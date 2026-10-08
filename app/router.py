import os, json
from .models import Workflow

class WorkflowRouter:
    def __init__(self, workflows):
        self.workflows = workflows
        self.client = None
        key = os.getenv("OPENAI_API_KEY")
        if key:
            from openai import OpenAI
            self.client = OpenAI(api_key=key)

    def select(self, request: str) -> Workflow:
        if self.client:
            catalog = [{"id": w.workflow_id, "name": w.name, "trigger": w.trigger, "inputs": w.inputs} for w in self.workflows]
            prompt = f"Select exactly one workflow for this request. Return JSON {{\\\"workflow_id\\\":\\\"WFxxx\\\"}}. Request: {request}\\nCatalog: {json.dumps(catalog)}"
            try:
                r = self.client.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), messages=[{"role":"system","content":"You are a workflow router."},{"role":"user","content":prompt}], temperature=0)
                obj = json.loads(r.choices[0].message.content)
                return next(w for w in self.workflows if w.workflow_id == obj["workflow_id"])
            except Exception:
                pass
        return self._fallback(request)

    def _fallback(self, request: str) -> Workflow:
        q = request.lower()
        # Deterministic semantic hints keep the demo reliable when no LLM key is configured.
        hints = {
            "WF001": ["restock", "inventory", "stock"],
            "WF002": ["vendor price", "price differs", "price validation", "pricing"],
            "WF003": ["vendor file", "vendor spreadsheet", "invalid rows", "cleaned dataset", "process this vendor"],
            "WF004": ["product description", "seo content", "meta description", "product content"],
            "WF005": ["order status", "where is order", "tracking", "shipment", "order ord"],
            "WF006": ["duplicate product", "duplicates", "similar products"],
            "WF007": ["campaign brief", "marketing campaign", "campaign"],
            "WF008": ["keyword", "keywords", "search intent", "map keywords"],
            "WF009": ["assign a task", "assign this task", "employee", "best available developer", "workload"],
            "WF010": ["performance report", "failing most often", "failure rate", "execution logs", "slow steps"],
        }
        scores=[]
        for w in self.workflows:
            score=sum(3 if phrase in q else 0 for phrase in hints.get(w.workflow_id, []))
            text=f"{w.name} {w.trigger} {w.inputs}".lower()
            score += sum(1 for token in q.replace("?", " ").split() if len(token)>4 and token in text)
            scores.append((score,w))
        return max(scores,key=lambda x:x[0])[1]
