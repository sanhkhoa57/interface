def get_ai_recommendations(age, interests, mood, style, content_type):
    from ai_service import wait_for_rate_limit, SAFETY_SETTINGS
    import time
    
    # Prompt an toàn hơn
    prompt = f"""
    As an entertainment recommendation expert, suggest 5 appropriate {content_type}s for:
    
    User Profile:
    - Age: {age}
    - Current Mood: {mood}
    - Interests: {interests}
    - Preferred Style: {style}
    
    Provide recommendations in this JSON format (no markdown):
    [
      {{
        "title": "Title name",
        "reason": "Why it matches (2 sentences)",
        "genre": "Main genre",
        "search_keyword": "Search term"
      }}
    ]
    """
    
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            wait_for_rate_limit(min_interval=5)
            
            model = genai.GenerativeModel(
                'gemini-2.5-flash',
                safety_settings=SAFETY_SETTINGS
            )
            response = model.generate_content(prompt)
            
            # Check if blocked
            if not response.text:
                st.warning("⚠️ Unable to generate recommendations (content policy)")
                return None
            
            text = response.text.strip()
            
            if text.startswith("```json"): 
                text = text[7:-3]
            elif text.startswith("```"): 
                text = text[3:-3]
            
            return json.loads(text)
            
        except Exception as e:
            error_msg = str(e)
            
            if "PROHIBITED_CONTENT" in error_msg:
                st.error("⚠️ Request blocked by content policy. Please adjust your preferences.")
                return None
            
            if attempt < max_retries - 1 and ("429" in error_msg or "quota" in error_msg.lower()):
                st.warning(f"⏳ API busy. Retrying in 20s...")
                time.sleep(20)
                continue
            else:
                st.error(f"AI Error: {str(e)[:100]}")
                return None
    
    return None
