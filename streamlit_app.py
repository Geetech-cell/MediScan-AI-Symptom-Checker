# streamlit_app.py
import streamlit as st
import time
from datetime import datetime
from fpdf import FPDF
import base64
from io import BytesIO
import requests
import os
from typing import List


def _safe_pdf_text(text: str) -> str:
    """Return text safe for FPDF (latin-1). Replace common bullets and strip characters
    that can't be encoded in latin-1 to avoid UnicodeEncodeError.
    """
    if not text:
        return ""
    text = str(text)
    # Replace unicode bullet with ASCII dash and common smart quotes
    for old, new in [("•", "-"), ("“", '"'), ("”", '"'), ("’", "'"), ("–", "-")]:
        text = text.replace(old, new)
    # Ensure string is latin-1 encodable; replace unsupported chars with '?'
    return text.encode("latin-1", "replace").decode("latin-1")


# ========================= CONFIG / STATE =========================
st.set_page_config(page_title="MediScan – AI Symptom Checker", layout="wide")

# Ensure session state keys exist
if "symptoms_text" not in st.session_state:
    st.session_state["symptoms_text"] = ""
if "selected_symptoms" not in st.session_state:
    st.session_state["selected_symptoms"] = []
if "history" not in st.session_state:
    st.session_state["history"] = []
if "api_url" not in st.session_state:
    st.session_state["api_url"] = "http://localhost:8000/predict"


# App title
st.title("🩺 MediScan – AI Symptom Checker")
st.markdown("""
<style>
.ms-card {background: #f8f9fb; padding: 12px; border-radius: 8px; margin-bottom: 8px}
.ms-bar {height: 12px; background: #e6e6e6; border-radius: 6px; overflow: hidden}
.ms-bar > div {height: 100%; background: #4caf50}
</style>
""", unsafe_allow_html=True)

# Small disease information database (used to produce human-friendly outcomes)
DISEASE_INFO = {
    "common cold": {
        "emoji": "🤧",
        "desc": "A mild viral infection of the upper respiratory tract. Symptoms are usually mild and self-limited.",
        "advice": "Rest, fluids, saline nasal spray, and OTC symptom relief. See a clinician if symptoms worsen or last >10 days.",
        "keywords": ["cold", "rhinitis", "runny", "sore throat"],
    },
    "influenza": {
        "emoji": "🤒",
        "desc": "Influenza causes fever, body aches, cough and fatigue — can be more severe than a common cold.",
        "advice": "Rest, fluids, and consider antivirals if within 48 hours and at-risk. Seek care for breathing difficulty.",
        "keywords": ["flu", "influenza", "body ache", "myalgia"],
    },
    "covid-19": {
        "emoji": "🦠",
        "desc": "COVID-19 is caused by SARS‑CoV‑2 and can present with fever, cough, and loss of taste or smell.",
        "advice": "Isolate, test if available, monitor oxygenation. Seek urgent care for shortness of breath or chest pain.",
        "keywords": ["covid", "sars", "corona", "loss of taste", "loss of smell"],
    },
    "migraine": {
        "emoji": "🤯",
        "desc": "Migraines are recurrent headaches often with nausea and sensitivity to light/sound.",
        "advice": "Rest in a dark room, use prescribed agents. Seek immediate care for a new sudden severe headache.",
        "keywords": ["migraine", "headache", "throbbing"],
    },
    "gastroenteritis": {
        "emoji": "🤢",
        "desc": "Infection or inflammation of the stomach/intestine causing vomiting and diarrhea.",
        "advice": "Hydrate with oral rehydration solutions. Seek care for bloody stools or severe dehydration.",
        "keywords": ["diarrhea", "vomit", "gastro", "stomach"],
    },
    "pneumonia": {
        "emoji": "🫁",
        "desc": "Infection of the lungs causing cough, fever, and sometimes difficulty breathing.",
        "advice": "Medical evaluation is recommended; antibiotics or hospital care may be needed depending on severity.",
        "keywords": ["pneumonia", "lung infection", "consolidation"],
    },
    "bronchitis": {
        "emoji": "🌬️",
        "desc": "Inflammation of the bronchial tubes causing cough and phlegm production.",
        "advice": "Rest and fluids; see clinician if cough is severe, prolonged or pus-like sputum develops.",
        "keywords": ["bronchitis", "bronchial", "productive cough"],
    },
    "dehydration": {
        "emoji": "💧",
        "desc": "Loss of fluids/electrolytes causing dizziness, dry mouth, and decreased urine output.",
        "advice": "Oral rehydration; seek urgent care for severe symptoms or inability to keep fluids down.",
        "keywords": ["dehydrate", "dehydration", "dry mouth", "dizzy"],
    },
    "strep throat": {
        "emoji": "🗣️",
        "desc": "Bacterial infection of the throat causing sore throat, fever, and swollen lymph nodes.",
        "advice": "See a clinician for testing and antibiotics if confirmed.",
        "keywords": ["strep", "strep throat", "tonsillitis"],
    },
    "allergic rhinitis": {
        "emoji": "🤧",
        "desc": "Allergic reaction causing sneezing, itchy/watery eyes and runny nose.",
        "advice": "Avoid triggers, use antihistamines or nasal steroids. Seek care if breathing difficulty occurs.",
        "keywords": ["allergy", "hay fever", "sneezing", "itchy eyes"],
    },
    "urinary tract infection": {
        "emoji": "🚽",
        "desc": "Infection of the urinary tract causing burning with urination and frequent urges.",
        "advice": "See a clinician for diagnosis and antibiotics if needed.",
        "keywords": ["uti", "urinary", "burning urine", "frequency"],
    },
    "asthma": {
        "emoji": "🌬️",
        "desc": "Chronic airway inflammation leading to wheeze, cough, chest tightness and shortness of breath.",
        "advice": "Use prescribed inhalers and seek urgent care for severe breathlessness or noisy breathing.",
        "keywords": ["wheeze", "asthma", "wheezing", "bronchospasm"],
    },
    "sinusitis": {
        "emoji": "😷",
        "desc": "Inflammation of the sinuses causing facial pain/pressure, nasal congestion and purulent discharge.",
        "advice": "Saline rinses and decongestants; see clinician for persistent pain or high fever.",
        "keywords": ["sinus", "sinusitis", "facial pain", "sinus pain"],
    },
    "otitis media": {
        "emoji": "👂",
        "desc": "Middle ear infection common in children, often with ear pain, fever and reduced hearing.",
        "advice": "Pain control and clinician review; antibiotics may be indicated based on exam.",
        "keywords": ["ear pain", "otitis", "earache", "ear infection"],
    },
    "appendicitis": {
        "emoji": "🔪",
        "desc": "Inflammation of the appendix causing progressive abdominal pain (often starts periumbilical then localizes to the right lower abdomen).",
        "advice": "Seek immediate emergency care for severe or worsening abdominal pain, fever, or vomiting.",
        "keywords": ["appendix", "appendicitis", "right lower quadrant", "abdominal pain"],
    },
    "gastroesophageal reflux (gerd)": {
        "emoji": "🔥",
        "desc": "Backflow of stomach acid causing heartburn, regurgitation and chest discomfort.",
        "advice": "Lifestyle measures and antacids; see clinician for severe or recurrent symptoms to assess for complications.",
        "keywords": ["heartburn", "acid reflux", "gerd", "regurgitation"],
    },
    "cellulitis": {
        "emoji": "🩹",
        "desc": "Bacterial skin infection causing redness, warmth, swelling and pain of the affected area.",
        "advice": "See clinician for antibiotics; urgent care if rapidly spreading or systemic symptoms.",
        "keywords": ["cellulitis", "redness", "skin infection", "swelling"],
    },
    "anaphylaxis": {
        "emoji": "⚠️",
        "desc": "Severe allergic reaction with hives, swelling, difficulty breathing, or low blood pressure.",
        "advice": "Call emergency services immediately — this is life-threatening.",
        "keywords": ["anaphylaxis", "anaphylactic", "hives", "swelling", "difficulty breathing"],
    },
    "panic attack": {
        "emoji": "😰",
        "desc": "Acute episodes of intense fear with palpitations, shortness of breath and a sense of doom.",
        "advice": "Grounding techniques and breathing; seek medical attention if first-time or atypical symptoms.",
        "keywords": ["panic", "panic attack", "anxiety", "palpitations"],
    },
    "kidney stone": {
        "emoji": "🪨",
        "desc": "Hard deposits in the urinary tract causing severe flank pain, often with nausea and hematuria.",
        "advice": "Seek emergency care for severe pain, inability to pass urine, or fever.",
        "keywords": ["kidney stone", "renal colic", "flank pain", "hematuria"],
    },
}


def _find_disease_info(disease_name: str):
    """Find a DISEASE_INFO entry for a predicted disease.

    Matching strategy:
    - Exact key match (case-insensitive)
    - Substring match
    - Keyword match using the `keywords` lists in DISEASE_INFO
    """
    if not disease_name:
        return None
    dn = disease_name.lower().strip()
    # direct key match
    for key in DISEASE_INFO:
        if key.lower() == dn:
            return DISEASE_INFO[key]
    # substring match
    for key in DISEASE_INFO:
        if key.lower() in dn or dn in key.lower():
            return DISEASE_INFO[key]
    # keyword match
    for key, info in DISEASE_INFO.items():
        for kw in info.get('keywords', []):
            if kw in dn:
                return info
    # fallback: check common tokens
    if any(tok in dn for tok in ("covid", "corona", "sars")):
        return DISEASE_INFO.get("covid-19")
    if "flu" in dn or "influenza" in dn:
        return DISEASE_INFO.get("influenza")
    return None


# ========================= SYMPTOM INPUT =========================
SYMPTOMS = [
    "fever", "cough", "headache", "fatigue", "nausea", "chest_pain",
    "shortness_of_breath", "dizziness", "sore_throat", "muscle_ache",
    "loss_of_taste_or_smell", "chills", "vomiting", "diarrhea"
]


# Sidebar: API config, presets and history
st.sidebar.header("Configuration & History")
st.sidebar.text_input("API URL", key="api_url")

PRESETS = {
    "Common Cold": "cough sore_throat runny_nose",
    "Flu-like": "fever chills muscle_ache fatigue",
    "COVID-like": "fever cough loss_of_taste_or_smell shortness_of_breath",
}

st.sidebar.markdown("**Example presets**")
for name, txt in PRESETS.items():
    if st.sidebar.button(name):
        st.session_state["symptoms_text"] = txt
        st.session_state["selected_symptoms"] = [s for s in txt.split() if s in SYMPTOMS]

st.sidebar.markdown("---")
if st.session_state["history"]:
    st.sidebar.subheader("History")
    for i, h in enumerate(reversed(st.session_state["history"][-6:])):
        idx = len(st.session_state["history"]) - 1 - i
        with st.sidebar.expander(f"{h['date']} — {h['summary']}"):
            st.sidebar.write(h.get("symptoms_display", ""))
            st.sidebar.write(h.get("urgency_display", ""))
            if st.sidebar.download_button(
                label="Download PDF",
                data=h.get("pdf_bytes", b""),
                file_name=h.get("file_name", "report.pdf"),
                mime="application/pdf",
            ):
                pass
    if st.sidebar.button("Clear History"):
        st.session_state["history"] = []

# Saved reports directory (persistent files)
REPORTS_DIR = os.path.join(os.getcwd(), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# List saved report files (most recent first)
st.sidebar.markdown("---")
st.sidebar.subheader("Saved Reports")
try:
    reports = sorted(
        [f for f in os.listdir(REPORTS_DIR) if f.lower().endswith('.pdf')],
        key=lambda x: os.path.getmtime(os.path.join(REPORTS_DIR, x)),
        reverse=True,
    )
except Exception:
    reports = []

if reports:
    for r in reports[:12]:
        path = os.path.join(REPORTS_DIR, r)
        with open(path, 'rb') as _f:
            bytes_data = _f.read()
        st.sidebar.write(r)
        st.sidebar.download_button(label="Download", data=bytes_data, file_name=r, mime="application/pdf")
else:
    st.sidebar.write("No saved reports")

st.sidebar.markdown("---")
st.sidebar.info("This tool is for educational purposes only. Always consult a doctor.")


# Main input area
col1, col2 = st.columns([3, 1])

with col1:
    symptoms_text = st.text_area(
        "Describe your symptoms (voice input appears here):",
        value=st.session_state.get("symptoms_text", ""),
        key="symptoms_text",
        height=120,
        placeholder="Or type manually..."
    )

with col2:
    selected_symptoms = st.multiselect(
        "Or select common symptoms:",
        options=SYMPTOMS,
        default=st.session_state.get("selected_symptoms", []),
        key="selected_symptoms",
    )

all_symptoms = list(dict.fromkeys(selected_symptoms + [
    s.strip() for s in str(symptoms_text).lower().replace(",", " ").split() if s.strip()
]))


# ========================= PREDICTION =========================
@st.cache_data(ttl=30)
def predict_cached(api_url: str, symptoms_list: List[str], description: str):
    try:
        resp = requests.post(
            api_url,
            json={"symptoms": symptoms_list, "description": description},
            timeout=15,
        )
        resp.raise_for_status()
        try:
            return resp.json(), None
        except Exception as e:
            return None, f"Invalid JSON response: {e}"
    except Exception as e:
        return None, str(e)


def generate_pdf_bytes(symptoms: List[str], preds: list, urgency: dict) -> tuple[bytes, str]:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "MediScan Clinical Summary", ln=1, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", size=12)
    dt = datetime.now().strftime('%Y-%m-%d %H:%M')
    pdf.cell(0, 10, f"Date: {dt}", ln=1)
    pdf.cell(0, 10, "Symptoms:", ln=1)
    pdf.set_font("Arial", size=10)
    for s in symptoms[:50]:
        safe = _safe_pdf_text(s.title())
        pdf.cell(0, 8, f"- {safe}", ln=1)
    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Predictions:", ln=1)
    pdf.set_font("Arial", size=10)
    for p in (preds or [])[:20]:
        name = _safe_pdf_text(p.get('disease', 'Unknown'))
        prob = p.get('probability', 0) * 100
        pdf.cell(0, 8, f"- {name}: {prob:.1f}%", ln=1)
    pdf.ln(3)
    if urgency:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Urgency:", ln=1)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, _safe_pdf_text(str(urgency)))

    # Try to return in-memory bytes
    try:
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
    except Exception:
        # Fallback to temp file
        import tempfile
        tmpf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmpf.close()
        pdf.output(tmpf.name)
        with open(tmpf.name, 'rb') as _f:
            pdf_bytes = _f.read()
        try:
            os.unlink(tmpf.name)
        except Exception:
            pass

    file_name = f"mediscan_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return pdf_bytes, file_name


def generate_disease_pdf(disease_name: str, probability: float, symptoms: List[str], preds: list, urgency: dict, info: dict | None) -> tuple[bytes, str]:
    """Generate a focused PDF report about the most likely disease.

    The report contains: disease name, emoji, probability, description, advice,
    suggested actions, matched symptoms, and top predictions for context.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    title = f"{info.get('emoji', '') + ' ' if info else ''}{disease_name}"
    pdf.cell(0, 12, title, ln=1, align='C')
    pdf.ln(4)

    pdf.set_font("Arial", size=12)
    dt = datetime.now().strftime('%Y-%m-%d %H:%M')
    pdf.cell(0, 8, f"Generated: {dt}", ln=1)
    pdf.ln(4)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Estimated Probability:", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"{probability*100:.1f}%", ln=1)
    pdf.ln(4)

    if info:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "Overview:", ln=1)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, _safe_pdf_text(info.get('desc', '')))
        pdf.ln(3)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "Advice / Next Steps:", ln=1)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, _safe_pdf_text(info.get('advice', '')))
        pdf.ln(3)

    if urgency:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "Urgency Assessment:", ln=1)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, _safe_pdf_text(str(urgency)))
        pdf.ln(3)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Reported Symptoms:", ln=1)
    pdf.set_font("Arial", size=11)
    for s in symptoms[:50]:
        pdf.cell(0, 6, f"- {_safe_pdf_text(s)}", ln=1)
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Top Predictions (context):", ln=1)
    pdf.set_font("Arial", size=11)
    for p in (preds or [])[:20]:
        name = _safe_pdf_text(p.get('disease', 'Unknown'))
        prob = p.get('probability', 0) * 100
        pdf.cell(0, 6, f"- {name}: {prob:.1f}%", ln=1)

    # produce bytes
    try:
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
    except Exception:
        import tempfile
        tmpf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmpf.close()
        pdf.output(tmpf.name)
        with open(tmpf.name, 'rb') as _f:
            pdf_bytes = _f.read()
        try:
            os.unlink(tmpf.name)
        except Exception:
            pass

    file_name = f"disease_summary_{disease_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return pdf_bytes, file_name


check_label = "🔎 Check My Symptoms"
download_label = "📄 Download Clinical Summary (PDF)"

def _render_probability_bar(name: str, prob: float) -> str:
    # returns HTML for a simple inline bar
    pct = max(0, min(100, int(prob * 100)))
    color = "#4caf50" if pct >= 50 else ("#ff9800" if pct >= 20 else "#9e9e9e")
    return (
        f"<div class='ms-card'><strong>{name}</strong> — {pct:.1f}%"
        f"<div class='ms-bar' style='margin-top:6px'><div style='width:{pct}%; background:{color}'></div></div></div>"
    )


if st.button(check_label):
    if not all_symptoms:
        st.warning("Please add at least one symptom.")
    else:
        with st.spinner("Analyzing…"):
            result, err = predict_cached(st.session_state.get("api_url"), all_symptoms, symptoms_text)
        if err:
            st.error(f"Server error: {err}")
        else:
            st.success("Analysis Complete!")
            preds = result.get("predictions", []) if result else []
            urgency = result.get("urgency", {}) if result else {}

            # Show top results as simple styled bars and list
            top = preds[:10]
            if top:
                for p in top:
                    name = p.get('disease', 'Unknown')
                    prob = p.get('probability', 0)
                    st.markdown(_render_probability_bar(name, prob), unsafe_allow_html=True)

                best = top[0]
                best_name = best.get('disease', 'Unknown')
                best_prob = best.get('probability', 0) * 100
                st.markdown(f"### { '✅' } Most likely: {best_name} — {best_prob:.1f}%")

                # Provide human-friendly outcome/explanation
                info = _find_disease_info(best_name)
                if info:
                    st.markdown(f"<div class='ms-card'><h4>{info['emoji']} {best_name}</h4>"
                                f"<p>{info['desc']}</p>"
                                f"<b>Next steps:</b> {info['advice']}</div>", unsafe_allow_html=True)
                    # Offer a disease-focused PDF summary
                    if st.button(f"📄 Download {best_name} Summary (PDF)"):
                        disease_pdf_bytes, disease_file = generate_disease_pdf(best_name, best.get('probability', 0), all_symptoms, preds, urgency, info)
                        # Save to persistent reports folder
                        try:
                            os.makedirs(REPORTS_DIR, exist_ok=True)
                            report_path = os.path.join(REPORTS_DIR, disease_file)
                            with open(report_path, 'wb') as rp:
                                rp.write(disease_pdf_bytes)
                        except Exception:
                            report_path = None

                        # Provide immediate download in UI
                        st.download_button(
                            label=f"Save {best_name} Summary",
                            data=disease_pdf_bytes,
                            file_name=disease_file,
                            mime="application/pdf",
                        )
                        # store disease summary in history entry as well
                        if st.session_state['history']:
                            st.session_state['history'][-1].setdefault('disease_summaries', []).append({
                                'disease': best_name,
                                'file_name': disease_file,
                                'pdf_bytes': disease_pdf_bytes,
                                'report_path': report_path,
                            })
                else:
                    st.info(f"{best_name}: This result suggests {best_name}. Consider seeing a clinician for diagnosis and treatment.")

            urgency = result.get("urgency", {}) if result else {}
            level = urgency.get("level", "medium").upper()
            color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}.get(level, "gray")
            st.markdown(f"**Urgency: <span style='color:{color}'>{level}</span>**", unsafe_allow_html=True)
            if rec := urgency.get("recommendation"):
                st.info(rec)

            # Generate PDF and keep in history
            pdf_bytes, file_name = generate_pdf_bytes(all_symptoms, preds, urgency)

            # Save to history (include human-friendly outcome if available)
            summary = top[0]['disease'] if preds else 'No diagnosis'
            outcome_info = _find_disease_info(summary)
            history_item = {
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'summary': summary,
                'symptoms_display': ", ".join(all_symptoms[:30]),
                'urgency_display': level,
                'predictions': preds,
                'pdf_bytes': pdf_bytes,
                'file_name': file_name,
                'outcome_emoji': outcome_info['emoji'] if outcome_info else '',
                'outcome_desc': outcome_info['desc'] if outcome_info else '',
            }
            st.session_state['history'].append(history_item)

            st.download_button(
                label=download_label,
                data=pdf_bytes,
                file_name=file_name,
                mime="application/pdf",
            )
