import os, json, streamlit as st
from dotenv import load_dotenv
load_dotenv()
from app.agent import WorkflowAgent

st.set_page_config(page_title='AI Workflow Agent', layout='wide')
st.title('AI Agent Workflow Automation')
st.caption('Excel-driven reusable workflow engine')
agent=WorkflowAgent(os.getenv('WORKFLOW_FILE','data/workflows.xlsx'))
request=st.text_area('User request', 'Which products need restocking?')
context_text=st.text_area('Context JSON', '{"inventory_file":"data/sample_data/inventory.csv"}')
if st.button('Run Agent', type='primary'):
    try:
        r=agent.handle(request,json.loads(context_text or '{}'))
        st.subheader(f'Selected Workflow: {r.workflow_id} — {r.workflow_name}')
        st.subheader('Steps Executed')
        for i,e in enumerate(r.events,1): st.write(f'{i}. **{e.step}** — {e.status}' + (f' — `{e.tool}`' if e.tool else ''))
        st.subheader('Final Output')
        st.json(r.result)
        if r.error: st.error(r.error)
    except Exception as e: st.exception(e)
