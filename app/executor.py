import json, os, re
from pathlib import Path
import pandas as pd
from .models import AgentResult, ExecutionEvent
from .tools import ToolRegistry

class WorkflowExecutor:
    def __init__(self, tool_registry=None):
        self.tools = tool_registry or ToolRegistry()
        self.client = None
        if os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            self.client = OpenAI()

    def run(self, workflow, request, context=None):
        context = context or {}
        result = AgentResult(workflow.workflow_id, workflow.name)
        try:
            handler = getattr(self, f"_run_{workflow.workflow_id}", self._generic_run)
            value = handler(workflow, request, context, result)
            result.result = value
        except Exception as e:
            result.error = str(e)
            result.events.append(ExecutionEvent("Workflow", None, "failed", str(e)))
        return result

    def _generic_run(self, w, request, context, result):
        # Generic executor for new workflows: records declarative steps and, when an LLM is configured,
        # asks it to transform the workflow definition + supplied context into a structured result.
        for step in w.steps:
            result.events.append(ExecutionEvent(step, None, "completed", "Declarative step executed"))
        if self.client:
            prompt = {"request":request,"workflow":{"name":w.name,"steps":w.steps,"decision":w.decision_logic,"output":w.expected_output},"context":context}
            r=self.client.chat.completions.create(model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),messages=[{"role":"system","content":"Execute a business workflow definition. Do not invent missing facts; clearly identify missing inputs."},{"role":"user","content":json.dumps(prompt)}],temperature=0)
            return r.choices[0].message.content
        return {"message":"Workflow steps completed in simulation mode", "workflow":w.name, "request":request, "decision_logic":w.decision_logic}

    def _run_WF001(self,w,request,context,result):
        df=self._table(context.get("inventory_file"), "inventory.csv")
        threshold_col='minimum_stock' if 'minimum_stock' in df else 'min_stock'
        low=df[df['current_stock'] < df[threshold_col]].copy()
        low['suggested_reorder_quantity']=low[threshold_col]-low['current_stock']
        result.events += [ExecutionEvent(s,None,'completed') for s in w.steps]
        return low[['product','current_stock',threshold_col,'suggested_reorder_quantity']].to_dict('records')

    def _run_WF002(self,w,request,context,result):
        products=self._table(context.get('product_file'),'products.csv'); vendor=self._table(context.get('vendor_file'),'vendor_prices.csv')
        m=products.merge(vendor,on='sku',suffixes=('_internal','_vendor')); m['difference_pct']=(m['price_vendor']-m['price_internal']).abs()/m['price_internal']*100
        m['exception']=m['difference_pct']>10
        result.events += [ExecutionEvent(s,None,'completed') for s in w.steps]
        return m[['sku','product','price_internal','price_vendor','difference_pct','exception']].round(2).to_dict('records')

    def _run_WF003(self,w,request,context,result):
        df=self._table(context.get('vendor_file'),'vendor_input.csv'); df.columns=[str(c).strip().lower().replace(' ','_') for c in df.columns]
        required={'sku','product_name'}; invalid=df[df[list(required)].isna().any(axis=1)].copy(); clean=df.drop(index=invalid.index)
        result.events += [ExecutionEvent(s,None,'completed') for s in w.steps]
        return {'cleaned_data':clean.to_dict('records'),'invalid_rows':invalid.to_dict('records'),'invalid_count':len(invalid)}

    def _run_WF004(self,w,request,context,result):
        fields=['product_name','category','attributes','material','color','target_audience']; missing=[x for x in fields if not context.get(x)]
        if self.client:
            prompt=f"Create product content from only these facts: {context}. Missing fields: {missing}. Never invent missing attributes. Return JSON with description, short_description, seo_title, meta_description."
            r=self.client.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),messages=[{'role':'system','content':'You are an ecommerce copywriter.'},{'role':'user','content':prompt}],temperature=.4)
            out=r.choices[0].message.content
        else:
            known=', '.join(f'{k}: {v}' for k,v in context.items() if v)
            out={'description':known or '[missing product information]','short_description':known or '[missing information]','seo_title':str(context.get('product_name','[Product]')),'meta_description':'Missing information: '+', '.join(missing) if missing else 'Generated from supplied attributes.'}
        for s in w.steps: result.events.append(ExecutionEvent(s,'LLM' if 'description' in s.lower() or 'seo' in s.lower() else None,'completed'))
        return out

    def _run_WF005(self,w,request,context,result):
        oid=context.get('order_id'); email=context.get('customer_email'); rows=self.tools.lookup_order(oid,email)
        for s in w.steps: result.events.append(ExecutionEvent(s,'Order database/API','completed'))
        if not rows: return {'status':'not_found','message':'No order found. Please provide another order ID or customer email.'}
        return rows[0]

    def _run_WF006(self,w,request,context,result):
        df=self._table(context.get('catalog_file'),'catalog.csv'); groups=[]; used=set()
        for i,a in df.iterrows():
            if i in used: continue
            g=[i]
            for j,b in df.iterrows():
                if j<=i or j in used: continue
                exact=(str(a.get('sku','')).strip() and str(a.get('sku','')).strip()==str(b.get('sku','')).strip())
                sim=(self.tools.text_similarity(a.get('product_name',''),b.get('product_name',''))>=.9)
                if exact or sim: g.append(j); used.add(j)
            if len(g)>1: groups.append(df.loc[g].to_dict('records'))
        for s in w.steps: result.events.append(ExecutionEvent(s,'text similarity','completed'))
        return groups

    def _run_WF007(self,w,request,context,result):
        missing=[x for x in ['campaign_goal','dates'] if not context.get(x)]
        if missing: return {'status':'needs_input','missing':missing,'message':'Please provide campaign goal and dates before generating the brief.'}
        if self.client:
            r=self.client.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),messages=[{'role':'system','content':'Create a structured marketing campaign brief.'},{'role':'user','content':str(context)}],temperature=.4); out=r.choices[0].message.content
        else: out={'objective':context.get('campaign_goal'),'audience':context.get('target_audience'),'products':context.get('product_list'),'promotion':context.get('promotion'),'dates':context.get('dates'),'channels':['Email','Social','Paid Search'],'checklist':['Approve messaging','Prepare creative','Schedule channels','Measure results']}
        for s in w.steps: result.events.append(ExecutionEvent(s,'LLM' if 'messaging' in s.lower() else 'product data reader','completed'))
        return out

    def _run_WF008(self,w,request,context,result):
        df=self._table(context.get('keyword_file'),'keywords.csv'); df=df.drop_duplicates(subset=['keyword']).copy()
        def intent(k):
            k=k.lower();
            if any(x in k for x in ['buy','price','order','discount']): return 'transactional'
            if any(x in k for x in ['best','compare','review']): return 'commercial'
            if any(x in k for x in ['what','how','guide','meaning']): return 'informational'
            return 'navigational'
        df['intent']=df.keyword.map(intent); df['priority']=df.get('volume',pd.Series([0]*len(df),index=df.index)).apply(lambda x:'high' if x>=1000 else 'medium' if x>=100 else 'low'); df['recommended_target_page']=df.get('category','general').astype(str).map(lambda x:'/category/'+x.lower().replace(' ','-'))
        for s in w.steps: result.events.append(ExecutionEvent(s,'CSV reader/classifier','completed'))
        return df.to_dict('records')

    def _run_WF009(self,w,request,context,result):
        df=self._table(context.get('employee_file'),'employees.csv'); required=set(str(context.get('required_skills','')).lower().split(',')); required={x.strip() for x in required if x.strip()}
        def score(row):
            skills={x.strip().lower() for x in str(row.get('skills','')).split(',')}; match=len(required & skills); capacity=max(0,100-float(row.get('workload_pct',100))); return match*100+capacity
        df['score']=df.apply(score,axis=1); suitable=df.sort_values('score',ascending=False)
        if suitable.empty or (required and suitable.iloc[0]['score']<100): return {'status':'escalate','message':'No suitable employee with required skills and capacity.'}
        best=suitable.iloc[0].to_dict()
        for s in w.steps: result.events.append(ExecutionEvent(s,'employee/task database','completed'))
        return {'recommended_employee':best,'task_summary':context.get('task_description'),'priority':context.get('priority'),'deadline':context.get('deadline')}

    def _run_WF010(self,w,request,context,result):
        df=self._table(context.get('logs_file'),'execution_logs.csv'); total=len(df); success=(df.status=='success').sum(); fail=total-success
        avg=float(df.execution_time_ms.mean()) if total else 0; errors=df[df.status!='success'].groupby('error').size().sort_values(ascending=False).to_dict(); slow=df.groupby('step').execution_time_ms.mean().sort_values(ascending=False).head(5).to_dict()
        for s in w.steps: result.events.append(ExecutionEvent(s,'calculator/reporting','completed'))
        return {'total_executions':total,'success_rate':success/total if total else 0,'failure_rate':fail/total if total else 0,'average_execution_time_ms':avg,'frequent_errors':errors,'slow_steps':slow,'recommendations':['Investigate workflows above 10% failure rate','Optimize consistently slow steps']}

    def _table(self,path,default):
        return self.tools.read_table(path or str(self.tools.data_dir/default))
