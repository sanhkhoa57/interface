import requests
import streamlit as st

# # Jikan API Services

@st.cache_data(ttl=3600)
def get_genre_map(content_type="anime"):
    url = f"https://api.jikan.moe/v4/genres/{content_type}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get('data', [])
            return {item['name']: item['mal_id'] for item in data}
        return {}
    except: return {}

@st.cache_data(ttl=3600)
def get_character_data(name):
    url = f"https://api.jikan.moe/v4/characters?q={name}&limit=10"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('data', [])
        return []
    except: return []

def get_one_character_data(name):
    results = get_character_data(name)
    return results[0] if results else None

def get_random_manga_data():
    url = "https://api.jikan.moe/v4/random/manga"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get('data', {})
            # Filter explicit content
            for genre in data.get('genres', []):
                if genre['name'] in ['Hentai', 'Erotica', 'Harem']:
                    return get_random_manga_data()
            return data
        return None
    except: return None