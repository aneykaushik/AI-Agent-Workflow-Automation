import pandas as pd
from pathlib import Path
from .models import Workflow

class WorkflowRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.workflows = self._load()

    def _load(self) -> dict[str, Workflow]:
        df = pd.read_excel(self.path, sheet_name="Workflows")
        out = {}
        for r in df.to_dict("records"):
            steps = [s.strip() for s in str(r["Steps"]).split("→") if s.strip()]
            tools = [s.strip() for s in str(r["Tools_Required"]).split(";") if s.strip()]
            out[r["Workflow_ID"]] = Workflow(
                workflow_id=r["Workflow_ID"],
                name=r["Workflow_Name"], trigger=r["Trigger"], inputs=r["Inputs"], steps=steps,
                decision_logic=r["Decision_Logic"], tools_required=tools, expected_output=r["Expected_Output"]
            )
        return out

    def all(self):
        return list(self.workflows.values())

    def get(self, workflow_id):
        return self.workflows[workflow_id]
