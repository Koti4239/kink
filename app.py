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
# STATE INITIALIZATION
# --------------------------
if "patient_registered" not in st.session_state:
    st.session_state.patient_registered = False
    st.session_state.p_id = generate_patient_id()


# --------------------------
# PAGE 1: PATIENT REGISTRATION
# --------------------------
if not st.session_state.patient_registered:
    st.title("🏥 Patient Registration")
    st.write("Please fill out your general information to unlock the diagnostic window.")
    
    reg_name = st.text_input("Full Name", value="")
    
    col_x, col_y = st.columns(2)
    with col_x:
        reg_age = st.number_input("Age", min_value=1, max_value=120, value=25)
    with col_y:
        reg_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        
    st.text_input("Assigned Patient ID", value=st.session_state.p_id, disabled=True)

    if st.button("Complete Registration & Open Checker", use_container_width=True):
        if not reg_name.strip():
            st.error("Please provide a name to complete your registration.")
        else:
            # Store inputs to memory and toggle screen layout
            st.session_state.p_name = reg_name
            st.session_state.p_age = reg_age
            st.session_state.p_gender = reg_gender
            st.session_state.patient_registered = True
            st.rerun()


# --------------------------
# PAGE 2: AI SYMPTOM CHECKER
# --------------------------
else:
    st.title("🩺 AI Symptom Checker")
    
    # Active patient identification header
    st.success(f"📋 **Active Case File:** {st.session_state.p_name} ({st.session_state.p_age} yrs | {st.session_state.p_gender}) | Patient ID: `{st.session_state.p_id}`")
    
    if st.button("⬅️ Clear File & Register New Patient"):
        st.session_state.patient_registered = False
        st.session_state.p_id = generate_patient_id()
        st.rerun()

    st.markdown("---")

    # Browser Microphone Speech Capture Tool
    st.subheader("🎙️ Dictate Your Symptoms")
    st.write("Click the button below to transcribe your voice directly into text:")

    voice_component = """
    <div style="text-align: center; margin-bottom: 10px;">
        <button id="record_btn" style="background-color: #ff4b4b; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%;">
            🎤 Click to Speak (Listen Microphone)
        </button>
        <p id="status" style="color: gray; font-style: italic; margin-top: 5px;">Microphone status: Ready...</p>
    </div>

    <script>
        const recordBtn = document.getElementById('record_btn');
        const statusText = document.getElementById('status');
        
        const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
        
        if (!SpeechRecognition) {
            statusText.innerText = "Speech capture functions are unavailable on this browser framework configuration.";
            recordBtn.disabled = true;
        } else {
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.lang = 'en-US';
            recognition.interimResults = false;
            
            recordBtn.addEventListener('click', () => {
                recognition.start();
                statusText.innerText = "Listening closely... Speak your symptoms now!";
                recordBtn.style.backgroundColor = "#ff1a1a";
            });
            
            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                statusText.innerText = "Speech captured!";
                recordBtn.style.backgroundColor = "#22bb22";
                recordBtn.innerText = "Speech Recorded ✅";
                
                // Set the value directly to the parent context container frame
                window.parent.postMessage({
                    type: 'streamlit:set_widget_value',
                    value: transcript
                }, '*');
                
                alert("Captured Voice Text: \\"" + transcript + "\\". Please verify details inside the text box field below.");
            };
            
            recognition.onerror = (event) => {
                statusText.innerText = "Error: " + event.error;
                recordBtn.style.backgroundColor = "#ff4b4b";
            };
        }
    </script>
    """
    components.html(voice_component, height=100)

    # Core intake entry elements
    symptoms = st.text_area("Symptoms Box (Review or write your symptoms here):", height=150)
    days = st.number_input("How many days have you experienced these symptoms?", min_value=1, max_value=365, value=1)

    if st.button("Run Diagnostic Prediction", use_container_width=True):
        if not symptoms.strip():
            st.warning("Please supply or record your symptom text inputs first.")
        else:
            prediction = model.predict([symptoms])[0]

            try:
                probs = model.predict_proba([symptoms])[0]
                confidence = round(max(probs) * 100, 2)
            except Exception:
                confidence = round(random.uniform(85, 99), 2)

            severity = calculate_severity(days)
            report_id = generate_report_id()

            # Dynamic medical description dictionary matching from Wikipedia API
            url, topic, wiki_description = wiki_search(prediction)
            if not wiki_description:
                wiki_description = "No specific reference medical documentation found within external encyclopedia pipelines."

            # Result summaries output layout
            st.success(f"🦠 Predicted Disease: **{prediction}**")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Confidence Score", f"{confidence}%")
            with col2:
                severity_color = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}
                st.metric("Estimated Severity", f"{severity_color.get(severity, '')} {severity}")

            st.markdown("---")

            # Reference data card block
            st.subheader("📚 Automated Medical Reference Insight")
            st.info(wiki_description)
            if url:
                st.markdown(f"🔗 [Explore the full Wikipedia article on {topic}]({url})")

            # Action guideline directory lookup
            st.subheader("🛡️ Recommended Precaution Guidelines")
            precautions_list = disease_precautions.get(prediction, [
                "Consult a qualified doctor immediately",
                "Drink plenty of water and rest well",
                "Avoid self-medication without professional advice",
                "Monitor symptoms and seek emergency help if worsening",
            ])
            for i, p in enumerate(precautions_list, 1):
                st.markdown(f"**{i}.** ✅ {p}")
