import streamlit as st
import os
from sanskrit_asr import transcribe_audio
from yourvoic_tts import generate_speech

# -----------------------------------------------------------------------------
# 1. Page Configuration & Vyoma Blue Custom CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sanskrit Antyakshari Krida - Vyoma Edition",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Main App Background */
    .stApp {
        background-color: #F4F7FA;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Vyoma Blue Header Card */
    .header-card {
        background: linear-gradient(135deg, #0D3B66 0%, #104F8B 60%, #1A65A4 100%);
        color: #FFFFFF;
        padding: 24px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0px 4px 14px rgba(13, 59, 102, 0.2);
        margin-bottom: 24px;
        border-bottom: 4px solid #F4C430; /* Gold Accent */
    }
    .header-card h1 {
        color: #FFFFFF !important;
        margin: 0;
        font-size: 32px;
        font-weight: 700;
    }
    .header-card p {
        color: #E0EBF5;
        margin-top: 6px;
        font-size: 16px;
    }

    /* Target Akshara Card */
    .target-card {
        background-color: #FFFFFF;
        border: 2px solid #0D3B66;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 24px;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.05);
    }
    .target-letter {
        font-size: 48px;
        font-weight: bold;
        color: #0D3B66;
        margin: 8px 0;
    }

    /* Move History Cards */
    .player-move {
        background-color: #EBF3FA;
        border-left: 5px solid #104F8B;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 12px;
        color: #0F172A;
    }
    .computer-move {
        background-color: #FEF9E7;
        border-left: 5px solid #D97706;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 12px;
        color: #0F172A;
    }
    
    /* Custom Buttons */
    .stButton > button {
        background-color: #0D3B66;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 10px 24px;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #104F8B;
        color: white;
        box-shadow: 0px 3px 8px rgba(13, 59, 102, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Vyoma Header Banner
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="header-card">
        <h1>🕉️ संस्कृत-अन्त्याक्षरी क्रीडा</h1>
        <p>Interactive Sanskrit Verse Antyakshari powered by Sushrota ASR & Vagdhenu TTS</p>
    </div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. Session State Initialization
# -----------------------------------------------------------------------------
if 'history' not in st.session_state:
    st.session_state.history = []
if 'target_letter' not in st.session_state:
    st.session_state.target_letter = "ध"  # Default starting letter
if 'player_score' not in st.session_state:
    st.session_state.player_score = 0
if 'computer_score' not in st.session_state:
    st.session_state.computer_score = 0

# -----------------------------------------------------------------------------
# 4. Sidebar Configuration & Dashboard
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Game Controls")
    corpus_choice = st.selectbox("Select Text Corpus", ["Bhagavad Gita", "Narayaneeyam", "Vishnu Sahasranama"])
    st.divider()
    
    st.subheader("📊 Scoreboard")
    col_a, col_b = st.columns(2)
    col_a.metric("Player", st.session_state.player_score)
    col_b.metric("Computer", st.session_state.computer_score)
    st.divider()
    
    if st.button("🔄 Reset Game", use_container_width=True):
        st.session_state.history = []
        st.session_state.target_letter = "ध"
        st.session_state.player_score = 0
        st.session_state.computer_score = 0
        st.rerun()

# -----------------------------------------------------------------------------
# 5. Main Game Layout
# -----------------------------------------------------------------------------
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    st.markdown(f"""
        <div class="target-card">
            <span style="color: #475569; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Target Starting Letter</span>
            <div class="target-letter">{st.session_state.target_letter}</div>
            <span style="color: #0D3B66; font-size: 14px; font-weight: 500;">Recite a verse starting with this letter</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("🎤 Speak Your Verse")
    audio_val = st.audio_input("Record your verse in Sanskrit")
    
    if audio_val:
        st.info("Transcribing audio using **Sushrota ASR**...")
        # Save audio file temporarily and pass to sanskrit_asr.py
        with open("temp_input.wav", "wb") as f:
            f.write(audio_val.read())
        
        user_text = transcribe_audio("temp_input.wav")
        if user_text:
            st.success(f"Recognized Text: **{user_text}**")
            # Log player turn
            st.session_state.history.append({"speaker": "Player", "text": user_text})
            st.session_state.player_score += 1
            
            # Computer turn logic
            computer_response_text = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः"
            st.session_state.history.append({"speaker": "Computer", "text": computer_response_text})
            st.session_state.computer_score += 1
            
            # Generate speech using Vagdhenu TTS
            audio_out = generate_speech(computer_response_text, "computer_response.wav")
            if audio_out and os.path.exists(audio_out):
                st.audio(audio_out, format="audio/wav", start_time=0)
            
            # Update target letter for next turn
            st.session_state.target_letter = "ः"
        else:
            st.error("Could not transcribe audio. Please try speaking again.")

with right_col:
    st.subheader("📜 Game History")
    if not st.session_state.history:
        st.write("No moves played yet. Record your verse to start!")
    else:
        for idx, move in enumerate(reversed(st.session_state.history)):
            if move["speaker"] == "Player":
                st.markdown(f"""
                    <div class="player-move">
                        <strong style="color: #0D3B66;">👤 Player:</strong><br>
                        <span style="font-size: 18px;">{move['text']}</span>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="computer-move">
                        <strong style="color: #B45309;">🤖 Computer:</strong><br>
                        <span style="font-size: 18px;">{move['text']}</span>
                    </div>
                """, unsafe_allow_html=True)
