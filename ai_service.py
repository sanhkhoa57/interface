import google.generativeai as genai
from PIL import Image
import time
import streamlit as st

# Rate limiting state
if 'last_api_call' not in st.session_state:
    st.session_state.last_api_call = 0
if 'api_call_count' not in st.session_state:
    st.session_state.api_call_count = 0

def wait_for_rate_limit(min_interval=4):
    """Đảm bảo ít nhất min_interval giây giữa các API calls"""
    elapsed = time.time() - st.session_state.last_api_call
    if elapsed < min_interval:
        wait_time = min_interval - elapsed
        time.sleep(wait_time)
    st.session_state.last_api_call = time.time()
    st.session_state.api_call_count += 1

def ai_vision_detect(image_data):
    image = Image.open(image_data)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    prompt = "Look at this anime character. Return ONLY the full name. If unsure, return 'Unknown'."
    
    max_retries = 3
    base_wait = 5
    
    for attempt in range(max_retries):
        try:
            # Rate limiting
            wait_for_rate_limit(min_interval=4)
            
            response = model.generate_content([prompt, image])
            return response.text.strip()
            
        except Exception as e:
            error_msg = str(e)
            
            # Kiểm tra nếu là lỗi rate limit
            if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                if attempt < max_retries - 1:
                    # Exponential backoff: 5s, 10s, 20s
                    wait_time = base_wait * (2 ** attempt)
                    print(f"⏳ Rate limit hit. Waiting {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    return "⚠️ API busy. Please try again in 1 minute."
            else:
                print(f"Vision Error: {e}")
                return "Unknown"
    
    return "Unknown"

def generate_ai_stream(info):
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    name = info.get('name', 'N/A')
    about = info.get('about', 'N/A')
    
    if about and len(about) > 2000: 
        about = about[:2000] + "..."

    prompt = f"""
    Based on the following info: "{about}".
    Act as a professional Otaku. Write a character analysis profile for {name} in ENGLISH following these 4 sections strictly:

    1. **Short Bio**: Retell their past or background in an engaging way.
    2. **Appeared In**: Introduce the original Anime and their specific role in it.
    3. **Powers & Abilities**: Analyze their strengths, special moves, or intellectual capabilities.
    4. **Personal Rating**: Explain why this character is loved (or hated) by the community.

    Keep the tone enthusiastic and fun! Use emojis 🌟🔥.
    """

    max_retries = 3
    base_wait = 5
    
    for attempt in range(max_retries):
        try:
            # Rate limiting
            wait_for_rate_limit(min_interval=4)
            
            response = model.generate_content(prompt, stream=True)
            return response
            
        except Exception as e:
            error_msg = str(e)
            
            if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                if attempt < max_retries - 1:
                    wait_time = base_wait * (2 ** attempt)
                    print(f"⏳ Rate limit hit. Waiting {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    class ErrorChunk:
                        def __init__(self, text): self.text = text
                    return [ErrorChunk("⚠️ API is busy. Please try again in 1 minute.")]
            else:
                class ErrorChunk:
                    def __init__(self, text): self.text = text
                return [ErrorChunk(f"AI Error: {str(e)}")]
    
    class ErrorChunk:
        def __init__(self, text): self.text = text
    return [ErrorChunk("⚠️ Maximum retries reached. Please try again later.")]
