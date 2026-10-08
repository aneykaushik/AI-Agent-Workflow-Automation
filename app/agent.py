from .workflow_registry import WorkflowRegistry
from .router import WorkflowRouter
from .executor import WorkflowExecutor

class WorkflowAgent:
    def __init__(self, workflow_file='data/workflows.xlsx'):
        self.registry=WorkflowRegistry(workflow_file)
        self.router=WorkflowRouter(self.registry.all())
        self.executor=WorkflowExecutor()
    def handle(self, request, context=None):
        workflow=self.router.select(request)
        return self.executor.run(workflow, request, context or {})
