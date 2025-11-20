# In main.py
from fastapi import FastAPI, HTTPException, Request
import joblib
import pandas as pd

app = FastAPI()

# Model paths
MODEL_PATH = "disease_xgb.pkl"
ENCODER_PATH = "label_encoder.pkl"

# Load models
print("🔍 Loading models...")
try:
    model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(ENCODER_PATH)
    print("✅ Models loaded successfully!")
    print(f"Model features: {model.feature_names_in_}")
except Exception as e:
    print(f"❌ Error loading models: {e}")
    model = None
    label_encoder = None

@app.get("/health")
async def health_check():
    return {
        "status": "ok" if model is not None else "error",
        "model_loaded": model is not None
    }

@app.post("/predict")
async def predict(request: Request):
    try:
        # Ensure model is loaded
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")

        # Get the request data
        data = await request.json()

        # Extract symptoms and optional description
        if isinstance(data, list):
            symptoms = data
            description = ""
        elif isinstance(data, dict):
            symptoms = data.get("symptoms", [])
            description = data.get("description", "")
        else:
            symptoms = []
            description = ""

        # Basic input validation
        if not symptoms:
            return {
                "predictions": [],
                "urgency": {"level": "low", "recommendation": "Please provide at least one symptom."},
                "status": "no_input",
            }

        # Create input vector (ensure symptoms are strings)
        symptoms = [str(s).strip() for s in symptoms if s]
        input_data = {symptom: 1 for symptom in symptoms}
        input_df = pd.DataFrame([input_data])

        # If model exposes feature names, ensure all are present and ordered
        feature_names = None
        if hasattr(model, "feature_names_in_"):
            feature_names = list(model.feature_names_in_)

        if feature_names:
            for col in feature_names:
                if col not in input_df:
                    input_df[col] = 0
            input_df = input_df[feature_names]

        # Get predictions (handle model errors cleanly)
        try:
            probs = model.predict_proba(input_df)[0]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Model prediction failed: {e}")

        # Determine class labels safely
        class_labels = None
        if hasattr(model, "classes_") and len(getattr(model, "classes_", [])) == len(probs):
            class_labels = list(model.classes_)
        elif label_encoder is not None and hasattr(label_encoder, "classes_") and len(label_encoder.classes_) == len(probs):
            class_labels = list(label_encoder.classes_)
        else:
            class_labels = [str(i) for i in range(len(probs))]

        # Build sorted predictions (highest first)
        import numpy as _np

        idx_sorted = _np.argsort(probs)[::-1]
        predictions = []
        for i in idx_sorted[:10]:
            label = class_labels[i] if i < len(class_labels) else str(i)
            predictions.append({
                "disease": str(label),
                "probability": float(probs[i]),
            })

        # Map urgency based on simple heuristics (keeps compatibility with front-end)
        urgency = {"level": "low", "recommendation": "Monitor your symptoms and follow up if they worsen."}
        low_symptoms = {"fever", "cough", "fatigue"}
        high_flags = {"chest_pain", "shortness_of_breath", "severe_breathing"}
        given = {s.lower().replace(" ", "_") for s in symptoms}
        if given & high_flags or "chest" in description.lower():
            urgency = {"level": "high", "recommendation": "Seek immediate medical attention (call emergency services or go to ER)."}
        elif given & low_symptoms:
            urgency = {"level": "medium", "recommendation": "Contact your primary care or urgent care for evaluation if symptoms persist or worsen."}

        return {
            "predictions": predictions,
            "urgency": urgency,
            "status": "success",
        }

    except HTTPException:
        # Re-raise HTTP exceptions for FastAPI to handle
        raise
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    print("\n🌐 Starting FastAPI server...")
    print("📌 Available endpoints:")
    print("   - GET  /health  - Check server and model status")
    print("   - POST /predict - Make predictions (accepts multiple input formats)")
    print("\n🔗 Open http://localhost:8000/docs for interactive API documentation\n")
    # Import uvicorn here to avoid requiring it at module import time
    try:
        import uvicorn
    except Exception:
        print("uvicorn is not installed. Start the server with: python -m uvicorn main:app --reload")
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)