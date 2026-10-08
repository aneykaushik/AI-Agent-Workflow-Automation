from pathlib import Path
import pandas as pd
from rapidfuzz.fuzz import ratio

class ToolRegistry:
    """Reusable tool layer. Real integrations can replace these implementations without changing the agent/runtime."""
    def __init__(self, data_dir="data/sample_data"):
        self.data_dir = Path(data_dir)

    def read_table(self, path):
        p = Path(path)
        return pd.read_excel(p) if p.suffix.lower() in {'.xlsx','.xls'} else pd.read_csv(p)

    def calculate(self, expression):
        return eval(expression, {"__builtins__": {}}, {})

    def text_similarity(self, a, b):
        return ratio(str(a).lower(), str(b).lower()) / 100

    def lookup_order(self, order_id=None, email=None):
        df = self.read_table(self.data_dir / "orders.csv")
        if order_id:
            hit = df[df.order_id.astype(str).str.lower() == str(order_id).lower()]
        else:
            hit = df[df.customer_email.astype(str).str.lower() == str(email).lower()]
        return hit.to_dict("records")

    def read_employees(self):
        return self.read_table(self.data_dir / "employees.csv")

    def read_tasks(self):
        return self.read_table(self.data_dir / "tasks.csv")
