from fastapi.testclient import TestClient
import mock_predict_server as mps


client = TestClient(mps.app)


def test_predict_basic_structure():
    payload = {"symptoms": ["fever", "cough"], "description": "High fever and cough"}
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "predictions" in body and isinstance(body["predictions"], list)
    assert "urgency" in body and isinstance(body["urgency"], dict)


def test_predict_probability_normalization():
    payload = {"symptoms": ["fever", "cough", "shortness_of_breath"], "description": ""}
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    preds = r.json().get("predictions", [])
    assert preds, "No predictions returned"
    total = sum([p.get("probability", 0) for p in preds])
    # probabilities should sum to ~1 (allow small numerical tolerance)
    assert total > 0.99 and total < 1.01


def test_predict_expected_top():
    payload = {"symptoms": ["flank_pain", "nausea", "vomiting"], "description": "Severe flank pain"}
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    preds = r.json().get("predictions", [])
    # expect kidney stone or appendicitis among top results for these symptoms
    top_diseases = [p["disease"] for p in preds[:3]]
    assert any(d in top_diseases for d in ("kidney stone", "appendicitis", "gastroenteritis"))


def test_predict_empty_symptoms_fallback():
    payload = {"symptoms": [], "description": ""}
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    preds = r.json().get("predictions", [])
    assert preds, "Fallback predictions should be returned for empty input"


def test_predict_ambiguous_case():
    payload = {"symptoms": ["fever", "runny_nose", "sneezing"], "description": ""}
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    preds = r.json().get("predictions", [])
    # common cold or influenza should typically be present
    top = [p["disease"] for p in preds[:4]]
    assert any(d in top for d in ("common cold", "influenza", "covid-19", "sinusitis"))
