import google.generativeai as genai
from PIL import Image
import time

# Global rate limiter
_last_api_call = 0
_api_call_count = 0
_daily_reset_time = time.time()

def reset_daily_counter():
    """Reset counter nếu đã qua ngày mới"""
    global _api_call_count, _daily_reset_time
    current_time = time.time()
    # Reset sau 24 giờ
    if current_time - _daily_reset_time > 86400:
        _api_call_count = 0
        _daily_reset_time = current_time
        print("🔄 Daily API counter reset")

def wait_for_rate_limit(min_interval=5):
    """
    Đảm bảo ít nhất min_interval giây giữa các API calls
    Gemini 2.0 Flash Free: 15 RPM = 4s/request minimum
    """
    global _last_api_call, _api_call_count
    
    reset_daily_counter()
    
    elapsed = time.time() - _last_api_call
    if elapsed < min_interval:
        wait_time = min_interval - elapsed
        print(f"⏳ Rate limiting: waiting {wait_time:.1f}s...")
        time.sleep(wait_time)
    
    _last_api_call = time.time()
    _api_call_count += 1
    print(f"✅ API Call #{_api_call_count} at {time.strftime('%H:%M:%S')}")

def ai_vision_detect(image_data):
    """Detect anime character from image using Gemini Vision"""
    
    # Resize image để giảm token usage
    image = Image.open(image_data)
    # Resize nếu quá lớn (max 1024x1024 để tiết kiệm tokens)
    max_size = 1024
    if image.width > max_size or image.height > max_size:
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        print(f"📐 Image resized to {image.size}")
    
    # Dùng flash-lite cho vision (rẻ hơn, quota cao hơn)
    model = genai.GenerativeModel('gemini-2.0-flash-lite')
    
    # Prompt ngắn gọn để tiết kiệm tokens
    prompt = "Anime character name only. Return 'Unknown' if unsure."
    
    max_retries = 3
    base_wait = 15  # Tăng lên 15s vì vision tốn nhiều quota hơn
    
    for attempt in range(max_retries):
        try:
            # Apply rate limiting - 6s cho vision
            wait_for_rate_limit(min_interval=6)
            
            print(f"🔍 Vision attempt {attempt + 1}/{max_retries}")
            response = model.generate_content(
                [prompt, image],
                generation_config={'max_output_tokens': 50}  # Giới hạn output
            )
            result = response.text.strip()
            print(f"✅ Vision result: {result}")
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Vision error (attempt {attempt + 1}): {error_msg}")
            
            # Check for rate limit or quota errors
            if any(keyword in error_msg.lower() for keyword in ["429", "quota", "rate limit", "resource exhausted"]):
                if attempt < max_retries - 1:
                    wait_time = base_wait * (2 ** attempt)  # 15s, 30s, 60s
                    print(f"⏳ Quota exceeded! Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    print("❌ Max retries reached for vision")
                    return "⚠️ API quota exceeded. Please wait 1 minute and try again."
            else:
                print(f"❌ Non-quota error: {error_msg}")
                return "Unknown"
    
    return "Unknown"

def generate_ai_stream(info):
    """Generate character analysis using Gemini"""
    
    # Dùng flash-lite thay vì flash-exp (quota cao hơn)
    model = genai.GenerativeModel('gemini-2.0-flash-lite')
    
    name = info.get('name', 'N/A')
    about = info.get('about', 'N/A')
    
    # Giảm context length để tiết kiệm tokens
    if about and len(about) > 1000: 
        about = about[:1000] + "..."

    # Prompt ngắn gọn hơn
    prompt = f"""Character: {name}
Info: {about}

Write 4 short sections:
1. Bio (2-3 sentences)
2. Anime appearance (1-2 sentences) 
3. Abilities (2-3 sentences)
4. Fan rating (1-2 sentences)

Keep it fun with emojis 🌟🔥"""

    max_retries = 3
    base_wait = 15
    
    for attempt in range(max_retries):
        try:
            # Apply rate limiting - 5s cho text generation
            wait_for_rate_limit(min_interval=5)
            
            print(f"📝 Stream attempt {attempt + 1}/{max_retries} for {name}")
            response = model.generate_content(
                prompt, 
                stream=True,
                generation_config={'max_output_tokens': 500}  # Giới hạn output
            )
            print(f"✅ Stream started successfully for {name}")
            return response
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Stream error (attempt {attempt + 1}): {error_msg}")
            
            if any(keyword in error_msg.lower() for keyword in ["429", "quota", "rate limit", "resource exhausted"]):
                if attempt < max_retries - 1:
                    wait_time = base_wait * (2 ** attempt)  # 15s, 30s, 60s
                    print(f"⏳ Quota exceeded! Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    print("❌ Max retries reached for stream")
                    class ErrorChunk:
                        def __init__(self, text): 
                            self.text = text
                    return [ErrorChunk("⚠️ Daily quota exceeded. Please try again tomorrow or upgrade to paid plan.")]
            else:
                print(f"❌ Non-quota error: {error_msg}")
                class ErrorChunk:
                    def __init__(self, text): 
                        self.text = text
                return [ErrorChunk(f"AI Error: {str(e)}")]
    
    # Fallback
    class ErrorChunk:
        def __init__(self, text): 
            self.text = text
    return [ErrorChunk("⚠️ Service temporarily unavailable. Please try again in a few minutes.")]

def get_api_stats():
    """Get current API usage statistics"""
    global _api_call_count, _last_api_call
    return {
        'total_calls': _api_call_count,
        'last_call': time.strftime('%H:%M:%S', time.localtime(_last_api_call)) if _last_api_call > 0 else 'Never'
    }
