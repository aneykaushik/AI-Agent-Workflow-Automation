# AI Agent Workflow Automation

An Excel-driven, reusable AI workflow agent built for the technical assignment. The system reads workflow definitions from Excel, routes natural-language requests to the correct workflow, executes reusable tools, applies workflow decision logic, records an execution trace, and returns a final result.
I Attached the screen recording link below-
https://www.loom.com/share/779f06b3a07044b5b4e6cd694cd36e74

## Architecture

```text
User Request
     |
     v
+-------------+
| Workflow    |  <- Excel workflow registry
| Router      |
+------+------+ 
       |
       v
+-------------+
| Workflow    |
| Executor    |  <- generic runtime + reusable domain handlers
+------+------+ 
       |
       v
+-------------+
| Tool Registry| <- CSV/XLSX reader, calculator, similarity, lookup
+------+------+ 
       |
       v
Execution Trace -> Final Result
```

### Why this architecture?

- **Excel is the source of workflow definitions.** Workflow names, triggers, inputs, steps, decision logic, tools, and expected outputs are not duplicated in ten chatbot prompts.
- **One router** chooses a workflow. With `OPENAI_API_KEY`, an LLM performs structured workflow selection; without it, a deterministic fallback keeps the demo runnable.
- **One executor** handles all workflows. Reusable tools are centralized in `ToolRegistry`.
- **LLM is used where language generation/classification adds value** (product content and campaign briefs, and optional routing).
- **Simulation mode** avoids requiring real business APIs. The sample datasets under `data/sample_data/` reproduce realistic tool behavior.

## Setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Add an OpenAI key to `.env` to enable LLM routing/content generation. The application still runs without a key using deterministic simulation.

## Run

CLI:

```bash
python main.py "Which products need restocking?" --context '{"inventory_file":"data/sample_data/inventory.csv"}'
```

Web UI:

```bash
streamlit run streamlit_app.py
```

## Assignment test examples

| Workflow | Example | Context |
|---|---|---|
| WF001 | Which products need restocking? | `inventory_file` |
| WF002 | Find products where vendor price differs by more than 10%. | `product_file`, `vendor_file` |
| WF003 | Process this vendor spreadsheet and show invalid rows. | `vendor_file` |
| WF004 | Generate SEO content for this product. | product attributes |
| WF005 | Where is order ORD-1001? | `order_id` |
| WF006 | Find likely duplicate products in the catalog. | `catalog_file` |
| WF007 | Create a campaign brief for the new collection. | campaign fields |
| WF008 | Classify these keywords and map them to pages. | `keyword_file` |
| WF009 | Assign this urgent task to the best available developer. | task + skills |
| WF010 | Which workflows are failing most often? | `logs_file` |

## Error and condition handling

Examples implemented from the Excel decision logic:

- WF001: restock when current stock is below minimum.
- WF002: exception when price difference exceeds 10%.
- WF003: invalid row when SKU or product name is missing.
- WF004: missing product attributes are explicitly identified; the LLM is instructed not to invent facts.
- WF005: missing order returns a request for another identifier.
- WF006: exact SKU matches are treated as definite duplicates; name similarity identifies likely duplicates.
- WF007: missing campaign goal or dates stops generation and requests those inputs.
- WF009: no suitable employee causes escalation.
- WF010: failure rate above 10% is flagged in recommendations.

## Adding workflow #11

The design intentionally separates workflow **definitions** from the agent runtime. A new workflow can be added as another row in `data/workflows.xlsx` with its trigger, inputs, steps, decision logic, tools, and expected output. If its steps can use existing generic tools, no new agent/router is required. If it needs a genuinely new external capability, add one tool to `ToolRegistry`; the core agent remains unchanged.

This is the main scalability property: **workflows are data, not separate chatbots.**

## Tests

```bash
pytest -q
```

Tests cover registry loading, routing, decision logic, invalid data, missing orders, missing campaign inputs, and the generic executor path.

## Project structure

```text
app/
  agent.py             # single orchestration entry point
  workflow_registry.py # Excel -> workflow definitions
  router.py            # LLM + deterministic workflow selection
  executor.py          # reusable execution runtime
  tools.py             # tool/API abstraction layer
data/
  workflows.xlsx       # original assignment source
  sample_data/         # simulated business systems
streamlit_app.py       # demo UI
main.py                # CLI demo
tests/                 # automated tests
```
