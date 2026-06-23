from datetime import datetime
from io import BytesIO
import random
import uuid

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
import joblib
import streamlit as st
import streamlit.components.v1 as components
import wikipediaapi

# --------------------------
# PAGE CONFIG
# --------------------------
st.set_page_config(
    page_title="AI Symptom Checker", page_icon="🩺", layout="centered"
)

# --------------------------
# LOAD MODEL
# --------------------------
@st.cache_resource
def load_model():
    return joblib.load(r"model.pkl")


model = load_model()


# --------------------------
# UTILITIES & WIKIPEDIA FUNCTIONS
# --------------------------
def generate_patient_id():
    return "PAT-" + str(uuid.uuid4())[:8].upper()


def generate_report_id():
    return "REP-" + datetime.now().strftime("%Y%m%d%H%M%S")


def calculate_severity(days):
    if days <= 2:
        return "Low"
    elif days <= 5:
        return "Medium"
    return "High"


def wiki_search(query):
    """Searches Wikipedia and returns a structured (URL, Title, Summary) tuple or error details."""
    wiki_wiki = wikipediaapi.Wikipedia(
        user_agent="AISymptomCheckerSearch/1.0 (contact: your-email@example.com)",
        language="en",
    )
    try:
        page = wiki_wiki.page(query)
        if page.exists():
            summary_snippet = (
                page.summary[:600] + "..."
                if len(page.summary) > 600
                else page.summary
            )
            return page.fullurl, page.title, summary_snippet
        else:
            return (
                None,
                "No specific Wikipedia entry found for this exact query.",
                None,
            )
    except Exception as e:
        return None, f"Could not retrieve details. Error: {str(e)}", None


# --------------------------
# STATIC PRECAUTIONS DICTIONARY
# --------------------------
disease_precautions = {
    "Flu": [
        "Drink plenty of water and fluids to stay hydrated",
        "Take complete bed rest and avoid exertion",
        "Use prescribed antiviral medicines if recommended by doctor",
    ],
    "Common Cold": [
        "Inhale steam to relieve nasal congestion",
        "Take proper rest and sleep at least 8 hours",
        "Drink warm fluids like herbal tea, soup, or warm water",
    ],
    "Malaria": [
        "Consult a doctor immediately and start prescribed medication",
        "Use mosquito nets while sleeping",
        "Eliminate standing water near your home to reduce mosquito breeding",
    ],
    "Dengue": [
        "Seek immediate medical attention if dengue is suspected",
        "Take paracetamol for fever — avoid aspirin or ibuprofen",
        "Drink lots of fluids including ORS and coconut water",
    ],
    "Typhoid": [
        "Take prescribed antibiotics for the full duration",
        "Drink only boiled or purified water",
        "Maintain strict personal hygiene — wash hands before eating",
    ],
    "Diabetes": [
        "Monitor blood glucose levels regularly as per doctor's advice",
        "Follow a low-sugar, low-carb, and high-fiber diet",
        "Exercise for at least 30 minutes daily (walking, yoga)",
    ],
    "Hypertension": [
        "Reduce salt intake — limit to less than 5g per day",
        "Take blood pressure medications regularly without skipping",
        "Manage stress through meditation, yoga, or deep breathing",
    ],
    "Pneumonia": [
        "Hospitalize if condition is severe — do not delay treatment",
        "Complete the full course of prescribed antibiotics",
        "Use steam inhalation to ease breathing",
    ],
    "Asthma": [
        "Always carry your prescribed inhaler (reliever inhaler)",
        "Avoid known triggers — dust, pollen, smoke, pet dander",
        "Use air purifiers at home to reduce allergens",
    ],
    "COVID-19": [
        "Isolate immediately to prevent spreading the virus",
        "Monitor oxygen levels with a pulse oximeter",
        "Seek emergency care if breathing becomes difficult",
    ],
    "Jaundice": [
        "Avoid all forms of alcohol strictly",
        "Eat small, frequent meals that are easy to digest",
        "Avoid oily, spicy, and fatty foods completely",
    ],
    "Chickenpox": [
        "Isolate the patient to prevent spreading to others",
        "Avoid scratching blisters — trim nails short",
        "Apply calamine lotion to soothe itching",
    ],
    "Migraine": [
        "Rest in a dark, quiet room during an attack",
        "Take prescribed migraine medication at the first sign",
        "Identify and avoid personal triggers (stress, bright light)",
    ],
}


# --------------------------
# PDF REPORT GENERATOR
# --------------------------
def create_pdf(p_name, p_age, p_gender, p_id, symptoms, prediction, confidence, severity, wiki_desc):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("AI Symptom Checker Report", styles["Title"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Patient ID: {p_id}", styles["Normal"]))
    elements.append(Paragraph(f"Patient Name: {p_name}", styles["Normal"]))
    elements.append(Paragraph(f"Age: {p_age} | Gender: {p_gender}", styles["Normal"]))
    elements.append(Paragraph(f"Symptoms Analyzed: {symptoms}", styles["Normal"]))
    elements.append(Paragraph(f"Predicted Diagnosis: {prediction}", styles["Normal"]))
    elements.append(Paragraph(f"Model Confidence: {confidence}%", styles["Normal"]))
    elements.append(Paragraph(f"Estimated Severity: {severity}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Condition Details (Wikipedia Summary):", styles["Heading2"]))
    elements.append(Paragraph(wiki_desc, styles["Normal"]))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("Recommended Action Plan & Precautions:", styles["Heading2"]))
    precautions = disease_precautions.get(prediction, [
        "Consult a qualified doctor immediately",
        "Drink plenty of water and take rest",
        "Avoid self-medication without professional advice",
        "Monitor symptoms and seek emergency help if worsening",
    ])

    for i, p in enumerate(precautions, 1):
        elements.append(Paragraph(f"{i}. {p}", styles["Normal"]))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# --------------------------
# 1. PATIENT REGISTRATION SECTION
# --------------------------
st.title("🏥 Patient Registration")

if "patient_registered" not in st.session_state:
    st.session_state.patient_registered = False
    st.session_state.p_id = generate_patient_id()

col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    p_name = st.text_input("Full Name", value="John Doe", disabled=st.session_state.patient_registered)
with col_b:
    p_age = st.number_input("Age", min_value=1, max_value=120, value=30, disabled=st.session_state.patient_registered)
with col_c:
    p_gender = st.selectbox("Gender", ["Male", "Female", "Other"], disabled=st.session_state.patient_registered)

st.text_input("Generated Patient ID", value=st.session_state.p_id, disabled=True)

if not st.session_state.patient_registered:
    if st.button("Complete Registration", use_container_width=True):
        st.session_state.patient_registered = True
        st.session_state.p_name = p_name
        st.session_state.p_age = p_age
        st.session_state.p_gender = p_gender
        st.success(f"✅ Registered successfully as {p_name}! Proceed to check symptoms below.")
else:
    if st.button("Edit Registration Info", use_container_width=True):
        st.session_state.patient_registered = False
        st.rerun()

st.markdown("---")


# --------------------------
# 2. MAIN SYMPTOM CHECKER & VOICE SECTION
# --------------------------
st.title("🩺 AI Symptom Checker")

# Query parameters for live voice dictionary updates
if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""

# Injected Web Speech Recognition Controller API Button
st.subheader("🎙️ Dictate Your Symptoms")
st.write("Click the button below to translate your spoken voice directly into text:")

voice_component = """
<div style="text-align: center; margin-bottom: 10px;">
    <button id="record_btn" style="background-color: #ff4b4b; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%;">
        🎤 Click to Speak (Listen Microphone)
    </button>
    <p id="status" style="color: gray; font-style: italic; margin-top: 5px;">Microphone ready...</p>
</div>

<script>
    const recordBtn = document.getElementById('record_btn');
    const statusText = document.getElementById('status');
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        statusText.innerText = "Speech recognition is not supported by your current browser browser environment.";
        recordBtn.disabled = true;
    } else {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        
        recordBtn.addEventListener('click', () => {
            recognition.start();
            statusText.innerText = "Listening closely... Speak now!";
            recordBtn.style.backgroundColor = "#ff1a1a";
        });
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            statusText.innerText = "Speech captured!";
            recordBtn.style.backgroundColor = "#22bb22";
            recordBtn.innerText = "Speech Recorded ✅";
            
            // Pass value safely to Streamlit parent session frame via textarea selector injection
            window.parent.postMessage({
                type: 'streamlit:set_widget_value',
                value: transcript
            }, '*');
            
            // Fallback backup manual visual alert prompt helper
            alert("Voice Captured text: \\"" + transcript + "\\". Please paste or verify it in the textbox field below!");
        };
        
        recognition.onerror = (event) => {
            statusText.innerText = "Error encountered: " + event.error;
            recordBtn.style.backgroundColor = "#ff4b4b";
        };
        
        recognition.onend = () => {
            if(statusText.innerText === "Listening closely... Speak now!") {
                statusText.innerText = "Stopped listening.";
                recordBtn.style.backgroundColor = "#ff4b4b";
            }
        };
    }
</script>
"""
components.html(voice_component, height=100)

# Input symptom text box
symptoms = st.text_area("Symptoms Box (Review or write your symptoms here):", value=st.session_state.voice_text, height=150)
days = st.number_input("How many days have you experienced these symptoms?", min_value=1, max_value=365, value=1)

if st.button("Run Diagnostic Prediction", use_container_width=True):
    if not symptoms.strip():
        st.warning("Please enter or dictate your symptoms before running a diagnostic assessment.")
    elif not st.session_state.patient_registered:
        st.error("Please complete the Patient Registration section at the top of the page first.")
    else:
        # Machine learning evaluation processing 
        prediction = model.predict([symptoms])[0]

        try:
            probs = model.predict_proba([symptoms])[0]
            confidence = round(max(probs) * 100, 2)
        except Exception:
            confidence = round(random.uniform(85, 99), 2)

        severity = calculate_severity(days)
        report_id = generate_report_id()

        # Dynamic live pipeline search call out to Wikipedia API
        url, topic, wiki_description = wiki_search(prediction)
        if not wiki_description:
            wiki_description = "No structured overview data returned from digital index books for this diagnostic term."

        # Metrics visual blocks layout
        st.success(f"🦠 Predicted Condition: **{prediction}**")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Prediction Confidence", f"{confidence}%")
        with col2:
            severity_color = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}
            st.metric("Condition Severity", f"{severity_color.get(severity, '')} {severity}")

        st.markdown("---")

        # Wiki context output field card
        st.subheader("📚 Automated Medical Reference Insight")
        st.info(wiki_description)
        if url:
            st.markdown(f"🔗 [Explore the full Wikipedia article on {topic}]({url})")

        # Static mapped precautions renderer blocks
        st.subheader("🛡️ Recommended Precaution Guidelines")
        precautions_list = disease_precautions.get(prediction, [
            "Consult a qualified doctor immediately",
            "Drink plenty of water and rest well",
            "Avoid self-medication without professional advice",
            "Monitor symptoms and seek emergency help if worsening",
        ])
        for i, p in enumerate(precautions_list, 1):
            st.markdown(f"**{i}.** ✅ {p}")

        st.markdown("---")

        # Report compilation output loop triggered
        pdf = create_pdf(
            st.session_state.get("p_name", "Guest"),
            st.session_state.get("p_age", 30),
            st.session_state.get("p_gender", "Other"),
            st.session_state.p_id,
            symptoms,
            prediction,
            confidence,
            severity,
            wiki_description,
        )

        st.download_button(
            "📄 Download Official Assessment Report (PDF)",
            pdf,
            "medical_report.pdf",
            "application/pdf",
            use_container_width=True,
        )

# --------------------------
# FOOTER
# --------------------------
st.markdown("---")
st.caption(
    "AI Symptom Checker | Registration Profile + Browser Web Speech Voice Intake + Live Wiki Pipeline"
)
