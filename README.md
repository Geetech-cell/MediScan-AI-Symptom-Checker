![CI](https://github.com/yourusername/yourrepo/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

**MediScan – AI Symptom Checker**

- **Project:** Streamlit front-end + FastAPI predict endpoint (mock + example server) for symptom analysis and PDF clinical summaries
- **Location:** `d:\AI future`
**Demo / Screenshots**

Add a GIF or screenshot to show the UI in the repo at `assets/demo.gif` or `assets/demo.png`. Example Markdown to include a demo image:

```markdown
![MediScan Demo](assets/demo.gif)
```
If you don't have a GIF yet, add a `screenshots/` folder with `ui.png` and link it in the README.
# Symptom Checker

A Streamlit-based web application that helps users check their symptoms, get risk assessments, and generate clinical summaries with PDF export. The app uses a FastAPI backend for predictions.

## Features

- 🔍 Symptom analysis and risk assessment
- 📊 Multiple possible conditions with confidence scores
- 📄 Generate and download PDF clinical summaries
- 🏥 Professional medical report formatting
- 🌐 Responsive web interface

## Prerequisites
**MediScan – AI Symptom Checker**

- **Project:** Streamlit front-end + FastAPI predict endpoint (mock + example server) for symptom analysis and PDF clinical summaries
- **Location:** `d:\AI future`

**Overview**
- **What:** A Streamlit UI (`streamlit_app.py`) that analyzes symptoms against a predict API and generates downloadable PDF clinical summaries and focused disease reports. Includes a local mock server (`mock_predict_server.py`) to simulate predictions and a sample `main.py` skeleton for production model wiring.
- **Why:** Rapid front-end development and testing without needing a production ML model; creates human-friendly summaries suitable for prototypes and demos.

**Features**
- 🎯 Symptom input (text + presets + multiselect)
- 📊 Ranked condition predictions with probabilities
- 🚦 Urgency assessment (low/medium/high) with recommendations
- 📄 Downloadable clinical summary PDFs and disease-focused PDFs
- 🧾 Session history and downloadable past reports

**Requirements**
- Python 3.10+ (3.11 recommended)
- `requirements.txt` contains project dependencies. Use a virtual environment for isolation.

**Quick Setup (PowerShell)**
```powershell
cd 'd:\AI future'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Run the Mock Predict Server (for front-end testing)**
```powershell
uvicorn mock_predict_server:app --reload --port 8000
```
- Visit `http://localhost:8000/docs` for interactive API docs.

**Run the Streamlit App**
```powershell
streamlit run "d:\AI future\streamlit_app.py"
```
- In the Streamlit sidebar set `API URL` to `http://localhost:8000/predict` (default for the mock server).

**API: `/predict` (expected format)**
- Request: JSON list of symptom strings or JSON object `{ "symptoms": [...], "description": "..." }`.
- Response: JSON with keys:
  - `predictions`: list of `{ "disease": str, "probability": float }` (sorted, highest first)
  - `urgency`: `{ "level": "low"|"medium"|"high", "recommendation": str }`
  - `status`: `"success"` (or `"no_input"` when input missing)

**Testing**
- Run the full test suite (uses `pytest`):
```powershell
cd 'd:\AI future'
python -m pytest -q
```
- If running tests directly (not via pytest), ensure `PYTHONPATH` includes the project root, for example:
```powershell
$env:PYTHONPATH = 'D:\AI future'
python d:\AI future\tests\test_mock_server.py
```

**Run sample requests & generate reports**
- Call the predict endpoint for a set of sample inputs and save outputs (JSON/CSV/MD):
```powershell
python run_samples.py --url http://localhost:8000/predict
```
- Results are saved into `outputs/` with timestamped filenames:
  - `.json` — raw requests + responses
  - `.csv` — summary rows with the top prediction per request
  - `.md` — human-readable markdown report

**PDF Reports**
- The Streamlit UI can produce:
  - Clinical summary PDF (session-level summary)
  - Disease-focused summary PDF (overview, advice, urgency, matched symptoms, top predictions)
- PDFs are generated in memory and downloadable via the app. Disease PDFs are also stored in `st.session_state` history for the session.

**Project Layout (key files)**
- `streamlit_app.py` — Streamlit UI, PDF generation, and `DISEASE_INFO` for human explanations
- `mock_predict_server.py` — FastAPI mock server with heuristic softmax scoring
- `main.py` — example production predict endpoint (model wiring skeleton)
- `run_samples.py` — calls predict endpoint, saves JSON/CSV/MD reports
- `tests/` — pytest unit tests for matching logic and mock server
- `.github/workflows/ci.yml` — GitHub Actions CI for running `pytest`

**CI**
- A GitHub Actions workflow is included to run tests on push and pull requests.

**Development Notes & Next Steps**
- To integrate a real model, place model files (e.g., `disease_xgb.pkl`, `label_encoder.pkl`) and update `main.py` to load them. The `main.py` endpoint is already shaped to return `predictions` and `urgency` compatible with the front-end.
- Consider adding ICD-10 codes, suggested tests, or richer patient handouts to each `DISEASE_INFO` entry.
 
**Deploying the API with Docker (recommended)**

1. Build the Docker image (from project root):

```powershell
cd 'd:\AI future'
docker build -t mediscan-api:latest .
```

2. Prepare model files

- Put your model files in `./models/` (e.g. `models/disease_xgb.pkl`, `models/label_encoder.pkl`). The `main.py` expects models at those paths.

3. Run the container (mount models folder):

```powershell
# run with port mapping and models mounted
docker run -it --rm -p 8000:8000 -v "${PWD}:/app" -v "${PWD}/models:/app/models" mediscan-api:latest
```

Or use docker-compose to run API (and optional Streamlit UI) locally:

```powershell
cd 'd:\AI future'
docker-compose up --build
```

4. Verify the API is running:

Open `http://localhost:8000/docs` for FastAPI interactive docs. Point the Streamlit app `API URL` to `http://host.docker.internal:8000/predict` (on Windows with Docker Desktop) or `http://localhost:8000/predict` if using local ports.

Notes for cloud deployment

- Google Cloud Run: build the container, push to Container Registry, then deploy to Cloud Run. Expose port 8000 and set concurrency to 80.
- Azure App Service: push the image to ACR and configure App Service to use the custom image.
- For production consider: environment variable-based configuration, secrets management for model storage, HTTPS, logging and monitoring.

**Disclaimer**
- This project is for prototyping and educational use only. Outputs are not medical advice. Always consult a qualified healthcare professional for diagnosis and treatment.

---
Generated: 2025-11-20
