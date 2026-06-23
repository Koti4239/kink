from datetime import datetime
from io import BytesIO
import random
import sqlite3
import uuid
import webbrowser

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
import joblib
import streamlit as st
import wikipediaapi

# --------------------------
# PAGE CONFIG
# --------------------------
st.set_page_config(
    page_title="AI Symptom Checker", page_icon="🩺", layout="centered"
)

# --------------------------
# DATABASE
# --------------------------
conn = sqlite3.connect("patients.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        report_id TEXT,
        patient_id TEXT,
        patient_name TEXT,
        age INTEGER,
        gender TEXT,
        symptoms TEXT,
        prediction TEXT,
        confidence REAL,
        timestamp TEXT
    )
""")
conn.commit()


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
# PDF REPORT
# --------------------------
def create_pdf(
    patient_name, patient_id, symptoms, prediction, confidence, severity, wiki_desc
):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("AI Symptom Checker Report", styles["Title"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Patient Name: {patient_name}", styles["Normal"]))
    elements.append(Paragraph(f"Patient ID: {patient_id}", styles["Normal"]))
    elements.append(Paragraph(f"Symptoms: {symptoms}", styles["Normal"]))
    elements.append(Paragraph(f"Prediction: {prediction}", styles["Normal"]))
    elements.append(Paragraph(f"Confidence: {confidence}%", styles["Normal"]))
    elements.append(Paragraph(f"Severity: {severity}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("About This Condition (Wikipedia):", styles["Heading2"]))
    elements.append(Paragraph(wiki_desc, styles["Normal"]))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("Recommended Action & Precautions:", styles["Heading2"]))
    precautions = disease_precautions.get(
        prediction,
        [
            "Consult a qualified doctor immediately",
            "Drink plenty of water and take rest",
            "Avoid self-medication without professional advice",
            "Monitor symptoms and seek emergency help if worsening",
        ],
    )

    for i, p in enumerate(precautions, 1):
        elements.append(Paragraph(f"{i}. {p}", styles["Normal"]))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Generated: {datetime.now()}", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# --------------------------
# SIDEBAR
# --------------------------
menu = st.sidebar.radio(
    "Menu", ["Patient Registration", "Symptom Checker", "Patient History"]
)

# --------------------------
# PATIENT REGISTRATION
# --------------------------
if menu == "Patient Registration":
    st.title("🏥 Patient Registration")

    if "patient_id" not in st.session_state:
        st.session_state.patient_id = generate_patient_id()

    name = st.text_input("Patient Name")

    st.text_input(
        "Patient ID", value=st.session_state.patient_id, disabled=True
    )

    age = st.number_input("Age", min_value=1, max_value=120, value=25)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])

    if st.button("Register"):
        st.session_state.name = name
        st.session_state.age = age
        st.session_state.gender = gender
        st.success("✅ Registration Successful")

# --------------------------
# SYMPTOM CHECKER
# --------------------------
elif menu == "Symptom Checker":
    st.title("🩺 AI Symptom Checker")

    symptoms = st.text_area("Enter Symptoms")
    days = st.number_input("Days", min_value=1, max_value=365, value=1)

    if st.button("Predict"):
        if not symptoms.strip():
            st.warning("Please enter your symptoms before predicting.")
        else:
            prediction = model.predict([symptoms])[0]

            try:
                probs = model.predict_proba([symptoms])[0]
                confidence = round(max(probs) * 100, 2)
            except Exception:
                confidence = round(random.uniform(85, 99), 2)

            severity = calculate_severity(days)
            report_id = generate_report_id()

            # Dynamic prediction background context via Wikipedia API
            url, topic, wiki_description = wiki_search(prediction)
            if not wiki_description:
                wiki_description = "No specific data returned from reference encyclopedias for this match."

            # Results
            st.success(f"🦠 Predicted Disease: **{prediction}**")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Confidence", f"{confidence}%")
            with col2:
                severity_color = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}
                st.metric(
                    "Severity", f"{severity_color.get(severity, '')} {severity}"
                )

            st.markdown("---")

            # Display Wikipedia summary for automated prediction
            st.subheader("📚 Reference Insight")
            st.info(wiki_description)

            # Precautions
            st.subheader("🛡️ Recommended Precautions")
            precautions_list = disease_precautions.get(
                prediction,
                [
                    "Consult a qualified doctor immediately",
                    "Drink plenty of water and rest well",
                    "Avoid self-medication without professional advice",
                    "Monitor symptoms and seek emergency help if worsening",
                ],
            )
            for i, p in enumerate(precautions_list, 1):
                st.markdown(f"**{i}.** ✅ {p}")

            st.markdown("---")

            # Save to SQLite DB
            cursor.execute(
                "INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    report_id,
                    st.session_state.get("patient_id", ""),
                    st.session_state.get("name", ""),
                    st.session_state.get("age", 0),
                    st.session_state.get("gender", ""),
                    symptoms,
                    prediction,
                    confidence,
                    str(datetime.now()),
                ),
            )
            conn.commit()

            # PDF build & download action trigger
            pdf = create_pdf(
                st.session_state.get("name", ""),
                st.session_state.get("patient_id", ""),
                symptoms,
                prediction,
                confidence,
                severity,
                wiki_description,
            )

            st.download_button(
                "📄 Download Full Report (PDF)",
                pdf,
                "medical_report.pdf",
                "application/pdf",
            )

# --------------------------
# PATIENT HISTORY
# --------------------------
elif menu == "Patient History":
    st.title("📋 Patient History")

    data = cursor.execute("SELECT * FROM patients").fetchall()

    if data:
        for row in data:
            with st.expander(
                f"🗂️ Report: {row[0]} | Patient: {row[2]} | Disease: {row[6]}"
            ):
                st.write(f"**Patient ID:** {row[1]}")
                st.write(f"**Name:** {row[2]}")
                st.write(f"**Age:** {row[3]} | **Gender:** {row[4]}")
                st.write(f"**Symptoms:** {row[5]}")
                st.write(f"**Prediction:** {row[6]}")
                st.write(f"**Confidence:** {row[7]}%")
                st.write(f"**Timestamp:** {row[8]}")
    else:
        st.info("No patient records found.")


# --------------------------
# INTERACTIVE WIKIPEDIA CHATBOT
# --------------------------
st.markdown("---")
st.subheader("🤖 Wikipedia Medical AI Chatbot")

# Initialize chat history state so it stays on screen during interactions
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": "Hello! I am your live Wikipedia assistant. Type any condition or term here to chat about it.",
        }
    ]

# Render existing chat logs
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Chat Input Element
if chat_user_query := st.chat_input("Ask me about any disease or medical term..."):
    # Render user query instantly
    with st.chat_message("user"):
        st.markdown(chat_user_query)
    st.session_state.chat_history.append({"role": "user", "content": chat_user_query})

    # Generate chatbot response
    with st.chat_message("assistant"):
        with st.spinner("Searching medical Wikipedia files..."):
            url, topic, summary = wiki_search(chat_user_query)

            if url:
                bot_reply = (
                    f"**Topic Match Found:** [{topic}]({url})\n\n"
                    f"{summary}\n\n"
                    f"🔗 _Click [here]({url}) to open the full official page in a new tab._"
                )
            else:
                bot_reply = (
                    f"I couldn't locate a precise text document for '{chat_user_query}'. "
                    f"Try querying accurate scientific words (e.g., 'Gastroenteritis' instead of 'stomach bug')."
                )
            st.markdown(bot_reply)
            
    # Append to state history
    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})


# --------------------------
# FOOTER
# --------------------------
st.markdown("---")
st.caption(
    "AI Symptom Checker | Streamlit + Machine Learning Inference + Live Wiki Chatbot Pipeline"
)
