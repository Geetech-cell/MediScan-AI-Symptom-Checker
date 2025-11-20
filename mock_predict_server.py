from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="MediScan Mock Predict Server")


class PredictRequest(BaseModel):
    symptoms: List[str]
    description: str = ""


# simple disease->symptoms mapping for heuristics
_DISEASE_SYMPTOMS = {
    "common cold": {"cough", "sore_throat", "runny_nose", "sneezing", "congestion"},
    "influenza": {"fever", "chills", "muscle_ache", "fatigue", "headache"},
    "covid-19": {"fever", "cough", "loss_of_taste_or_smell", "shortness_of_breath", "fatigue"},
    "pneumonia": {"fever", "cough", "shortness_of_breath", "chest_pain", "productive_cough"},
    "gastroenteritis": {"diarrhea", "vomiting", "nausea", "abdominal_pain"},
    "migraine": {"headache", "nausea", "sensitivity", "photophobia"},
    "urinary tract infection": {"burning", "frequency", "urinary", "dysuria"},
    "asthma": {"wheeze", "shortness_of_breath", "cough", "chest_tightness"},
    "sinusitis": {"facial_pain", "nasal_congestion", "purulent_discharge", "sinus_pressure"},
    "otitis media": {"ear_pain", "fever", "reduced_hearing"},
    "appendicitis": {"abdominal_pain", "right_lower_quadrant", "nausea", "vomiting"},
    "gastroesophageal reflux (gerd)": {"heartburn", "regurgitation", "chest_discomfort"},
    "cellulitis": {"redness", "swelling", "pain", "warmth"},
    "anaphylaxis": {"hives", "swelling", "difficulty_breathing", "low_blood_pressure"},
    "panic attack": {"palpitations", "shortness_of_breath", "sweating", "fear"},
    "kidney stone": {"flank_pain", "hematuria", "nausea", "vomiting"},
}


@app.post("/predict")
async def predict(req: PredictRequest) -> Dict[str, Any]:
    # normalize symptoms
    given = {s.lower().replace(" ", "_") for s in req.symptoms}
    # score each disease by matched keywords and simple description boost
    raw_scores = {}
    for disease, attrs in _DISEASE_SYMPTOMS.items():
        match_count = len(attrs & given)
        base = match_count / max(1, len(attrs))
        desc_boost = 0.0
        for tok in disease.split():
            if tok in req.description.lower():
                desc_boost += 0.12
        raw_scores[disease] = max(0.0, base + desc_boost)

    # softmax normalize for realistic-looking probabilities
    import math

    def softmax(scores_dict):
        vals = list(scores_dict.values())
        if not vals:
            return {}
        maxv = max(vals)
        exps = {k: math.exp(v - maxv) for k, v in scores_dict.items()}
        s = sum(exps.values())
        if s <= 0:
            return {k: 0.0 for k in scores_dict}
        return {k: exps[k] / s for k in scores_dict}

    probs = softmax(raw_scores)
    preds = [
        {"disease": k, "probability": round(v, 3)}
        for k, v in sorted(probs.items(), key=lambda x: x[1], reverse=True)
        if v > 0
    ]
    # fallback
    if not preds:
        preds = [
            {"disease": "common cold", "probability": 0.5},
            {"disease": "influenza", "probability": 0.3},
            {"disease": "covid-19", "probability": 0.2},
        ]

    # determine urgency heuristics
    urgency = {"level": "low", "recommendation": "Monitor symptoms and follow up if they worsen."}
    # If chest pain or shortness_of_breath present, mark high
    if "chest_pain" in given or "shortness_of_breath" in given or "chest" in req.description.lower():
        urgency = {"level": "high", "recommendation": "Seek immediate medical attention (ER) for chest pain or severe breathing difficulty."}
    elif any(x in given for x in ("fever", "high_fever", "severe_fatigue")):
        urgency = {"level": "medium", "recommendation": "Contact your primary care or urgent care for evaluation."}

    return {"predictions": preds, "urgency": urgency}
