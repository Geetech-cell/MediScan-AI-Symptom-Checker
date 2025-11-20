"""
run_samples.py

Simple script to POST sample symptom requests to the mock server
and save the combined responses into `outputs/samples_{timestamp}.json`.

Usage:
    python run_samples.py --url http://localhost:8000/predict

"""
import requests
import json
from datetime import datetime
import os
import argparse
import csv
from typing import Any, Dict

SAMPLES = [
    {"symptoms": ["sneezing", "runny_nose", "sore_throat"], "description": "Runny nose and sore throat"},
    {"symptoms": ["fever", "chills", "muscle_ache"], "description": "High fever and body aches"},
    {"symptoms": ["loss_of_taste_or_smell", "cough"], "description": "Sudden loss of smell and cough"},
    {"symptoms": ["flank_pain", "nausea", "vomiting"], "description": "Severe flank pain with vomiting"},
    {"symptoms": ["chest_pain", "shortness_of_breath"], "description": "Chest pain and difficulty breathing"},
]


def run(url: str):
    out = []
    for s in SAMPLES:
        try:
            r = requests.post(url, json=s, timeout=10)
            r.raise_for_status()
            body = r.json()
        except Exception as e:
            body = {"error": str(e)}
        out.append({"request": s, "response": body})

    os.makedirs("outputs", exist_ok=True)
    fname = f"outputs/samples_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved sample responses to {fname}")

    # Also write a CSV summary and a human-readable Markdown report
    csv_name = fname.replace('.json', '.csv')
    md_name = fname.replace('.json', '.md')

    # CSV: timestamp, request_description, top_disease, top_probability, all_predictions_json
    with open(csv_name, 'w', newline='', encoding='utf-8') as cf:
        writer = csv.writer(cf)
        writer.writerow(['timestamp', 'request_description', 'top_disease', 'top_probability', 'predictions'])
        for entry in out:
            req = entry['request']
            resp = entry['response']
            ts = datetime.now().isoformat()
            desc = req.get('description') or ' '.join(req.get('symptoms', []))
            preds = resp.get('predictions', []) if isinstance(resp, dict) else []
            if preds:
                top = preds[0]
                writer.writerow([ts, desc, top.get('disease'), top.get('probability'), json.dumps(preds, ensure_ascii=False)])
            else:
                writer.writerow([ts, desc, '', '', json.dumps(resp, ensure_ascii=False)])
    print(f"Saved CSV summary to {csv_name}")

    # Markdown report
    with open(md_name, 'w', encoding='utf-8') as mf:
        mf.write(f"# Sample Predict Responses — {datetime.now().isoformat()}\n\n")
        for i, entry in enumerate(out, 1):
            req = entry['request']
            resp = entry['response']
            mf.write(f"## Sample {i}\n\n")
            mf.write(f"**Request:** `{json.dumps(req, ensure_ascii=False)}`\n\n")
            if isinstance(resp, dict) and 'predictions' in resp:
                mf.write("**Predictions:**\n\n")
                for p in resp.get('predictions', [])[:10]:
                    mf.write(f"- {p.get('disease')} — {p.get('probability')*100:.1f}%\n")
                mf.write("\n")
                mf.write(f"**Urgency:** {resp.get('urgency', {})}\n\n")
            else:
                mf.write(f"**Response:** `{json.dumps(resp, ensure_ascii=False)}`\n\n")
    print(f"Saved Markdown report to {md_name}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/predict", help="Predict endpoint URL")
    args = parser.parse_args()
    run(args.url)
