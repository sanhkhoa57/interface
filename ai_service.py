import google.generativeai as genai
from PIL import Image
import time

# Global rate limiter
_last_api_call = 0
_api_call_count = 0

def wait_for_rate_limit(min_interval=5):
    """Đảm bảo ít nhất min_interval giây giữa các API calls"""
    global _last_api_call, _api_call_count
    
    elapsed = time.time() - _last_api_call
    if elapsed < min_interval:
        wait_time = min_interval - elapsed
        time.sleep(wait_time)
    
    _last_api_call = time.time()
    _api_call_count += 1

def ai_vision_detect(image_data):
    """Detect anime character from image using Gemini Vision"""
    image = Image.open(image_data)
    
    # Resize để tiết kiệm quota
    max_size = 800
    if image.width > max_size or image.height > max_size:
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    prompt = "Look at this anime character. Return ONLY the full name. If unsure, return 'Unknown'."
    
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            wait_for_rate_limit(min_interval=6)
            response = model.generate_content([prompt, image])
            return response.text.strip()
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1 and ("429" in error_msg or "quota" in error_msg.lower()):
                time.sleep(20)
                continue
            print(f"Vision Error: {e}")
            return "Unknown"
    
    return "Unknown"

def generate_ai_stream(info):
    """Generate character analysis using Gemini"""
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    name = info.get('name', 'N/A')
    about = info.get('about', 'N/A')
    
    if about and len(about) > 1500: 
        about = about[:1500] + "..."

    prompt = f"""
    Based on the following info: "{about}".
    Act as a professional Otaku. Write a character analysis profile for {name} in ENGLISH following these 4 sections strictly:

    1. **Short Bio**: Retell their past or background in an engaging way.
    2. **Appeared In**: Introduce the original Anime and their specific role in it.
    3. **Powers & Abilities**: Analyze their strengths, special moves, or intellectual capabilities.
    4. **Personal Rating**: Explain why this character is loved (or hated) by the community.

    Keep the tone enthusiastic and fun! Use emojis 🌟🔥.
    """

    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            wait_for_rate_limit(min_interval=5)
            response = model.generate_content(prompt, stream=True)
            return response
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1 and ("429" in error_msg or "quota" in error_msg.lower()):
                time.sleep(20)
                continue
            
            class ErrorChunk:
                def __init__(self, text): 
                    self.text = text
            return [ErrorChunk(f"AI Error: {str(e)}")]
    
    class ErrorChunk:
        def __init__(self, text): 
            self.text = text
    return [ErrorChunk("Service temporarily unavailable")]

def get_api_stats():
    """Get current API usage statistics"""
    global _api_call_count, _last_api_call
    return {
        'total_calls': _api_call_count,
        'last_call': time.strftime('%H:%M:%S', time.localtime(_last_api_call)) if _last_api_call > 0 else 'Never'
    }
