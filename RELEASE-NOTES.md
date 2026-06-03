# Release Notes

All notable changes to the **AgenticPMO** project will be documented in this file.

---

## [v0.1.0] — 2026-06-04

This is the initial bootstrap release of the **AgenticPMO** orchestration and intelligence layer. It establishes the multi-agent graph logic and the API layer needed to automate PMBOK® 8th Edition project workflows.

### Added
- **Multi-Agent LangGraph Workflows (`graph/`, `agents/`)**:
  - **Orchestrator Agent**: Parses natural language inputs, extracts key project variables (name, budget, sponsor), and maps the request to a PMBOK 8 skill in the registry.
  - **Executor Agent**: Validates if all mandatory variables for a skill are present, generates compliant markdown artifacts (stored in `artifacts/`), and halts the graph with missing input prompts when context is incomplete.
  - **Governor Agent**: Calculates quantitative decision bands (T1 to T4) using project budgets and cost/schedule variance percentages. Triggers sponsor validation warnings for T3/T4 bands.
- **REST API Layer (`api/main.py` & `schemas/`)**:
  - Implemented the `/chat` POST endpoint to execute the state machine synchronously.
  - Enabled client-driven state serialization, allowing stateless clients to resume multi-turn conversations by passing back the serialized state from the previous response.
- **PMOSkills SDK Integration**:
  - Editable installation of the `pmoskills` SDK via PyPI.
  - Auto-injection of templates, process records, and quality check constraints.
- **Integration Test Suite (`tests/test_graph.py`)**:
  - Automated test coverage validating the happy-path execution, missing inputs pause-and-resume loops, and quantitative T1-T4 escalation rules.
- **Documentation**:
  - Created a detailed architecture and API usage instruction guide in the master `README.md`.
