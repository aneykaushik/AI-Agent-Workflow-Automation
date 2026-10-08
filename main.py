import argparse, json, os
from dotenv import load_dotenv
load_dotenv()
from app.agent import WorkflowAgent

parser=argparse.ArgumentParser(description='Excel-driven AI Workflow Agent')
parser.add_argument('request', help='User request')
parser.add_argument('--context', default='{}', help='JSON input context')
args=parser.parse_args()
agent=WorkflowAgent(os.getenv('WORKFLOW_FILE','data/workflows.xlsx'))
r=agent.handle(args.request,json.loads(args.context))
print(f"\nSelected Workflow: {r.workflow_id} - {r.workflow_name}\n")
print('Steps Executed:')
for i,e in enumerate(r.events,1): print(f"{i}. {e.step} [{e.status}]" + (f" via {e.tool}" if e.tool else ''))
print('\nResult:')
print(json.dumps(r.result,indent=2,default=str))
if r.error: print('\nError:',r.error)
