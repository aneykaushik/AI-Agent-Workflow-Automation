from dataclasses import dataclass, field
from typing import Any

@dataclass
class Workflow:
    workflow_id: str
    name: str
    trigger: str
    inputs: str
    steps: list[str]
    decision_logic: str
    tools_required: list[str]
    expected_output: str

@dataclass
class ExecutionEvent:
    step: str
    tool: str | None
    status: str
    detail: str = ""
    data: Any = None

@dataclass
class AgentResult:
    workflow_id: str
    workflow_name: str
    events: list[ExecutionEvent] = field(default_factory=list)
    result: Any = None
    error: str | None = None
