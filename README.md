# SilicoBioScreen — VS Code starter project

A local research prototype based on the uploaded technical specification. It includes candidate records, drug profiles, configurable protocol rules, target/safety/eligibility separation, screening explanations, audit events, verification feedback, and descriptive confusion-matrix metrics.

## Safety and scope
This is **not a validated clinical tool**. Use synthetic or properly de-identified data only. Do not use it to make patient-care or enrollment decisions. Example drug and protocol data are placeholders, not clinical recommendations. Feedback metrics are descriptive and never automatically change rules. Any real-world research use requires protocol-owner and qualified clinical review, privacy/security controls, validation, and appropriate ethics/regulatory assessment.

## Files
- `app/main.py`: FastAPI REST API and database operations
- `app/models.py`: SQLAlchemy models
- `app/engine.py`: deterministic, explainable screening rules
- `ui.py`: Streamlit interface
- `tests/test_engine.py`: starter tests
- `requirements.txt`: dependencies

## Windows PowerShell setup
Install Python 3.11+ (3.12 recommended), VS Code, and the Python extension. Open this folder in VS Code and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Terminal 1 — API:
```powershell
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs

Terminal 2 — UI:
```powershell
.\.venv\Scripts\Activate.ps1
streamlit run ui.py
```

For the quickest walkthrough, click **Create synthetic demo data** on the Overview tab, then open **Screen** and run the demo candidate.

## Rule JSON
```json
{
  "id": "INC-001",
  "field": "diagnosis",
  "operator": "EQUALS",
  "value": "metastatic_colorectal_cancer",
  "reason": "Diagnosis must match protocol"
}
```
Supported operators: `EXISTS`, `EQUALS`, `NOT_EQUALS`, `IN`, `NOT_IN`, `CONTAINS`, `GREATER_THAN`, `GREATER_THAN_OR_EQUAL`, `LESS_THAN`, `LESS_THAN_OR_EQUAL`, `TRUE`, `FALSE`.

Candidate paths include `diagnosis`, `prior_therapy_lines`, `ecog_score`, `biomarkers.KRAS_G12C`, `labs.egfr`, `comorbidities`, `medications`, `allergies`, and `history.record_age_days`. All inclusion rules must pass (AND logic); a confirmed exclusion triggers exclusion; missing/un-evaluable rules trigger review. A missing biomarker is `INDETERMINATE`, never `NEGATIVE`.

## Main API endpoints
`GET /health`, `POST/GET /candidates`, `POST/GET /drugs`, `POST/GET /protocols`, `POST/GET /screenings`, `POST /feedback`, `GET /metrics`, `GET /audit`, `POST /demo/seed`.

## Testing
```powershell
pytest -q
```

## Production hardening
Add authentication and role-based access, encrypted managed database/storage, secret management, validated terminology mappings (ICD-10-CM/SNOMED CT/RxNorm), immutable audit retention, automated security/integration tests, curated reference datasets, subgroup performance assessment, and human approval/versioning for protocol rules before considering real research use.
