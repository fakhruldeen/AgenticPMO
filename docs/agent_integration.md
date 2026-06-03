# External AI Agent Integration Guide

This guide is designed for developers building autonomous AI agents or chat interfaces that consume the **AgenticPMO** orchestration API.

---

## 🤖 The Stateful API Loop Protocol

Since the AgenticPMO backend is stateless, the client application (or external AI orchestrator) must store and send back the updated Graph State on each HTTP turn.

```
 Client Agent                          AgenticPMO API
 ┌──────────┐                          ┌────────────┐
 │          │ ─── 1. Send Request ───► │            │
 │          │                          │            │
 │          │ ◄─── 2. Returns State ── │            │
 │          │    (missing_inputs:      │            │
 │          │     ['Sponsor'])         │            │
 │          │                          │            │
 │ Resolves │                          │            │
 │ Sponsor  │                          │            │
 │          │ ─── 3. Resume State ───► │            │
 │          │                          │            │
 │          │ ◄─── 4. Done (PASS) ──── │            │
 └──────────┘                          └────────────┘
```

---

## 🐍 Python Client Integration Example

Below is a complete, production-ready Python client implementation that programmatically communicates with the AgenticPMO `/chat` API, detects when the graph is paused waiting for inputs, and automatically supplies missing variables.

```python
import requests
import json
from typing import Dict, Any, List

API_URL = "http://127.0.0.1:8000/chat"

class AgenticPMOClient:
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.state: Dict[str, Any] = {}

    def send_message(self, message: str, context_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """Submits a message and context overrides to the AgenticPMO graph."""
        payload = {
            "message": message,
            "state": self.state if self.state else None,
            "current_project_context": context_overrides or {}
        }
        
        response = requests.post(self.api_url, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"API Error: {response.text}")
            
        data = response.json()
        
        # Save the returned state to preserve conversation context
        self.state = {
            "messages": data.get("messages", []),
            "current_project_context": data.get("current_project_context", {}),
            "active_skill": data.get("active_skill"),
            "missing_inputs": data.get("missing_inputs", []),
            "generated_artifact": data.get("generated_artifact"),
            "escalation_level": data.get("escalation_level")
        }
        return data

# --- Example Autonomous Execution Flow ---
client = AgenticPMOClient()

# 1. Initial Prompt: Requesting PM Governance without providing a sponsor
print("--- Initial Prompt ---")
res = client.send_message("Establish governance for Aero Project with budget $120000")
print(f"Active Skill: {res['active_skill']}")
print(f"Missing Inputs: {res['missing_inputs']}")

# 2. Check if the graph is paused waiting for inputs
if res["missing_inputs"]:
    print("\n--- Resolving Missing Inputs Autonomously ---")
    # Simulate a client-side lookup or user prompt resolving the missing fields
    resolved_context = {}
    for missing_field in res["missing_inputs"]:
        if missing_field.lower() == "sponsor":
            resolved_context["sponsor"] = "Alice Smith"
            print("Client resolved 'sponsor' -> 'Alice Smith'")

    # Send the follow-up message with resolved parameters, carrying back the state
    final_res = client.send_message(
        message="Providing the missing parameters.",
        context_overrides=resolved_context
    )
    
    print("\n--- Final API Execution Result ---")
    print(f"Escalation Level: {final_res['escalation_level']}")
    print(f"Artifact status: {'Generated' if final_res['generated_artifact'] else 'Failed'}")
```

---

## 📦 Request / Response State Mapping

When constructing integrations, map the payload properties as follows:

- **`messages`**: An array of objects with keys `role` (must be `"human"`, `"ai"`, or `"system"`) and `content`.
- **`current_project_context`**: A dictionary containing programmatic key-value indicators (e.g. `cost_variance_pct`, `schedule_variance_days`, `project_budget`).
- **`missing_inputs`**: A list of string labels of required fields. When this is non-empty, client interfaces should block normal chat and present a form requesting these parameters specifically.
- **`generated_artifact`**: The markdown string returned by the Executor agent upon successfully passing the quality gate.
- **`escalation_level`**: The governance tier (`T1`, `T2`, `T3`, or `T4`). If `T3` or `T4` is returned, client apps should trigger executive alerts requiring human validation.
