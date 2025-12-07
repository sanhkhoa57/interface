import google.generativeai as genai
from PIL import Image
# AI Services & Prompts

def ai_vision_detect(image_data):
    image = Image.open(image_data)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    # Vision Prompt
    prompt = "Look at this anime character. Return ONLY the full name. If unsure, return 'Unknown'."
    
    try:
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e: 
        print(f"Vision Error: {e}")
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

    try:
        response = model.generate_content(prompt, stream=True)
        return response
    except Exception as e:
        class ErrorChunk:
            def __init__(self, text): self.text = text
        return [ErrorChunk(f"AI Error: {str(e)}")]

    return model.generate_content(prompt, stream=True)




