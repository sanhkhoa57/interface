import google.generativeai as genai
import time
import json
from PIL import Image
import streamlit as st
import hashlib
from datetime import datetime, timedelta

# --- CẤU HÌNH MODEL ---
MODEL_NAME = "gemini-2.5-flash"

# --- RATE LIMITER ---
if 'last_api_call' not in st.session_state:
    st.session_state.last_api_call = None

@st.cache_resource
def get_model():
    return genai.GenerativeModel(MODEL_NAME)

def enforce_minimum_delay(min_seconds=4):
    """BẮT BUỘC delay 4s giữa mỗi API call"""
    if st.session_state.last_api_call:
        elapsed = (datetime.now() - st.session_state.last_api_call).total_seconds()
        if elapsed < min_seconds:
            wait_time = min_seconds - elapsed
            with st.spinner(f"⏳ Rate limiting... {wait_time:.1f}s"):
                time.sleep(wait_time)
    st.session_state.last_api_call = datetime.now()

def safe_api_call(func, *args, **kwargs):
    """Retry với exponential backoff"""
    backoff_times = [5, 10, 20, 40, 60]
    
    for attempt, wait_time in enumerate(backoff_times):
        try:
            enforce_minimum_delay(4)
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error_msg = str(e)
            if any(x in error_msg for x in ["429", "ResourceExhausted", "503", "quota"]):
                if attempt < len(backoff_times) - 1:
                    st.warning(f"⏳ Server busy. Waiting {wait_time}s... ({attempt+1}/{len(backoff_times)})")
                    time.sleep(wait_time)
                    continue
                else:
                    st.error("🚫 Server quá tải. Vui lòng đợi 2-3 phút rồi thử lại.")
                    return None
            else:
                st.error(f"❌ Lỗi: {error_msg[:150]}")
                return None
    return None

# --- CÁC HÀM API với @st.cache_data ---

@st.cache_data(ttl=7200, show_spinner=False)
def get_ai_recommendations(age, interests, mood, style, content_type):
    """AI Recommendations - Cache 2 giờ"""
    model = get_model()
    prompt = f"""
Act as an expert OTAKU. Recommend 5 {content_type} series.
User Info: {age} years old.
Interests: {interests}
Current Mood: {mood}
Preferred Style: {style}

IMPORTANT: Return ONLY valid JSON array. No markdown, no backticks.
Format: [{{"title": "Name", "genre": "Genre", "reason": "Why this fits"}}]
"""
    
    def _call():
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    
    result = safe_api_call(_call)
    return result if result else []

@st.cache_data(ttl=86400, show_spinner=False)
def ai_vision_detect_cached(image_bytes):
    """Vision Detection - Cache 24 giờ theo image bytes"""
    model = get_model()
    from io import BytesIO
    img = Image.open(BytesIO(image_bytes))
    
    prompt = """Look at this anime character image.
Return ONLY the character's full name (e.g. "Naruto Uzumaki").
If cannot identify, return exactly: "Unknown"
No explanation, just the name."""
    
    def _call():
        response = model.generate_content([prompt, img])
        return response.text.strip()
    
    result = safe_api_call(_call)
    return result if result else "Unknown"

def ai_vision_detect(image_file):
    """Wrapper cho vision detection"""
    image_file.seek(0)
    image_bytes = image_file.read()
    image_file.seek(0)
    return ai_vision_detect_cached(image_bytes)

@st.cache_data(ttl=86400, show_spinner=False)
def generate_ai_profile_text(char_id, char_name, char_about):
    """
    Generate AI Profile - Cache 24 giờ theo char_id
    ĐÂY LÀ HÀM CHÍNH ĐỂ CACHE
    """
    model = get_model()
    
    if char_about and len(char_about) > 2000:
        char_about = char_about[:2000] + "..."

    prompt = f"""You are an expert Anime Otaku. Write an engaging character profile in ENGLISH.

Character Name: {char_name}
Biography: {char_about}

Requirements:
- Catchy title with emojis (🌟🔥✨)
- Fun, enthusiastic tone
- Analyze personality and powers
- Keep under 200 words
- Make it engaging!"""
    
    def _call():
        response = model.generate_content(prompt)
        return response.text.strip()
    
    result = safe_api_call(_call)
    return result if result else "⚠️ Could not generate profile. Please try again later."

def generate_ai_stream(info):
    """
    Wrapper cho stream - GỌI HÀM CACHED
    Trả về list chunks để tương thích với code cũ
    """
    char_id = info.get('mal_id')
    char_name = info.get('name', 'N/A')
    char_about = info.get('about', 'N/A')
    
    # GỌI HÀM CACHED - Nếu có cache thì return ngay lập tức
    full_text = generate_ai_profile_text(char_id, char_name, char_about)
    
    # Fake stream để UX mượt
    class TextChunk:
        def __init__(self, text):
            self.text = text
    
    return [TextChunk(full_text)]
