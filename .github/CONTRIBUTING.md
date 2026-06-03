# Contributing to AgenticPMO

First off, thank you for checking out AgenticPMO! Contributions from the community help build a more robust orchestration and intelligence layer for PMBOK® 8th Edition workflows.

---

## 🛠️ Local Environment Setup

We recommend using Python 3.11+ and setting up a virtual environment.

### 1. Clone the repository:
```bash
git clone https://github.com/fakhruldeen/AgenticPMO.git
cd AgenticPMO
```

### 2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install development dependencies:
```bash
pip install -r requirements.txt
```

---

## 🧪 Testing & Validation

Before submitting any Pull Request, verify that all integration tests are passing.

### Run tests:
Specify `PYTHONPATH` from the root directory when executing `pytest`:
```bash
PYTHONPATH=. pytest tests/test_graph.py -v
```

> [!TIP]
> **Offline Validation**: The test suite falls back to a deterministic regex engine if no API keys are present. Set `GEMINI_API_KEY` or `OPENAI_API_KEY` to run the integration tests with live LLM calls.

---

## 🔀 Git Workflow & Pull Requests

1. **Branch Naming**:
   - Create a feature or bugfix branch off `main`:
     - `feature/new-agent-capability`
     - `bugfix/issue-loop-fix`
2. **Commit Messages**:
   - Write clear, imperative commits. E.g., `feat: integrate PMBOK 8 skill SKL-03-01` or `fix: handle null values in cost variance calculations`.
3. **Pull Request Checklist**:
   - Ensure the code complies with Python linting standard practices.
   - Run the tests to guarantee zero regressions.
   - Check that all line endings conform to `LF` formatting (normalization rules are handled by the repository's `.gitattributes` configuration).
   - Reference the related issue in the PR description.
