import streamlit as st
import google.generativeai as genai
import requests
import json
import re
import os
import time
from datetime import datetime

# --- IMPORT MODULES ---
from style_css import set_global_style
from jikan_services import get_genre_map, get_character_data, get_one_character_data, get_random_manga_data
from ai_service import ai_vision_detect, generate_ai_stream, get_ai_recommendations

# --- 1. PAGE CONFIG & SETUP ---
st.set_page_config(page_title="ITOOK Library", layout="wide", page_icon="📚")

# Load API Key
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
elif "GEMINI_API_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_API_KEY"]
else:
    st.error("API Key is missing. Please check secrets.toml.")
    st.stop()

genai.configure(api_key=API_KEY)

# --- 2. GLOBAL CSS & LOADING SCREEN ---
st.markdown("""
<style>
    .loading-overlay {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(0, 0, 0, 0.9);
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        z-index: 99999;
        animation: fadeOutOverlay 0.5s ease-out 2.0s forwards;
        pointer-events: none;
    }
    .loading-title {
        font-family: 'Pacifico', cursive; font-size: 2.5rem; color: #ff7f50;
        margin-bottom: 20px; text-shadow: 0 0 10px rgba(255, 127, 80, 0.5);
    }
    .progress-bar {
        width: 300px; height: 4px; background: linear-gradient(90deg, #ff7f50 0%, #ff6b6b 100%);
        animation: loadProgress 1.8s ease-out forwards;
    }
    @keyframes loadProgress { 0% { width: 0%; } 100% { width: 100%; } }
    @keyframes fadeOutOverlay { 100% { opacity: 0; visibility: hidden; } }
</style>
<div class="loading-overlay">
    <div class="loading-title">ITOOK Library</div>
    <div class="progress-bar"></div>
</div>
""", unsafe_allow_html=True)

# --- 3. SESSION STATE INITIALIZATION ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'

if 'show_upgrade_modal' not in st.session_state:
    st.session_state.show_upgrade_modal = False

if 'favorites' not in st.session_state:
    st.session_state.favorites = {'media': [], 'characters': []}

if 'search_history' not in st.session_state:
    st.session_state.search_history = []

if 'random_manga_item' not in st.session_state:
    st.session_state.random_manga_item = None

if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None

# *** KEY FIX: Dùng session_state để cache kết quả như code mới ***
if 'wiki_state' not in st.session_state:
    st.session_state.wiki_state = {
        'search_results': [],
        'selected_char': None,
        'ai_analysis': None,  # ← LƯU KẾT QUẢ AI Ở ĐÂY
        'mode': None
    }

# --- 4. HELPER FUNCTIONS ---
def navigate_to(page):
    st.session_state.show_upgrade_modal = False
    st.session_state.current_page = page
    st.rerun()

def add_to_history(action_type, query, details=None):
    entry = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'type': action_type, 'query': query, 'details': details
    }
    st.session_state.search_history.insert(0, entry)
    if len(st.session_state.search_history) > 50:
        st.session_state.search_history = st.session_state.search_history[:50]

def is_favorited(item_id, category):
    for item in st.session_state.favorites[category]:
        current_id = item.get('mal_id') or item.get('id')
        if str(current_id) == str(item_id): return True
    return False

def toggle_favorite(data, category='media'):
    item_id = data.get('mal_id') or data.get('id')
    title_name = data.get('title') or data.get('name') or data.get('title_english')
    
    if is_favorited(item_id, category):
        st.session_state.favorites[category] = [
            i for i in st.session_state.favorites[category] 
            if str(i.get('mal_id') or i.get('id')) != str(item_id)
        ]
        st.toast(f"💔 Removed '{title_name}'", icon="🗑️")
    else:
        fav_item = {
            'mal_id': item_id,
            'title': title_name,
            'image_url': data.get('images', {}).get('jpg', {}).get('image_url'),
            'score': data.get('score'),
            'url': data.get('url'),
            'type': category,
            'added_at': datetime.now().strftime("%Y-%m-%d")
        }
        st.session_state.favorites[category].append(fav_item)
        st.toast(f"❤️ Added '{title_name}'", icon="✅")

# --- 5. UI COMPONENTS ---
def show_navbar():
    with st.container():
        c1, c2, c3, c4, c5, c6 = st.columns([2.5, 0.8, 0.8, 0.8, 0.8, 0.8], gap="small", vertical_alignment="center")
        with c1: st.markdown('<p class="logo-text">ITOOK Library</p>', unsafe_allow_html=True)
        with c2: 
            if st.button("HOME", use_container_width=True): navigate_to('home')
        with c3:
            with st.popover("SERVICES", use_container_width=True):
                if st.button("🕵️ Wiki Search", use_container_width=True): navigate_to('wiki')
                if st.button("📂 Genre Explorer", use_container_width=True): navigate_to('genre')
                if st.button("🤖 AI Recommend", use_container_width=True): navigate_to('recommend')
        with c4:
            if st.button("FAVORITES", use_container_width=True): navigate_to('favorites')
        with c5:
            if st.button("ADVANCES", use_container_width=True): 
                st.session_state.show_upgrade_modal = True
                st.rerun()
        with c6:
            if st.button("CONTACT", use_container_width=True): navigate_to('contact')
    st.write("")

@st.dialog("🚀 Upgrade Your Experience", width="large")
def show_upgrade_dialog():
    st.markdown("<h3 style='text-align:center'>Discover More with Advanced Version</h3>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.link_button("🚀 GO TO ADVANCED VERSION", "https://itookwusadvances.streamlit.app/", use_container_width=True, type="primary")
    st.session_state.show_upgrade_modal = False

# --- 6. PAGE FUNCTIONS ---

def show_homepage():
    set_global_style("test.jpg") 
    show_navbar()
    if st.session_state.show_upgrade_modal: show_upgrade_dialog()
    
    st.markdown("""
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 style="font-family: 'Pacifico', cursive; font-size: 80px; color: #FF6600; text-shadow: 3px 3px 6px black;">Welcome to ITOOK</h1>
            <p style="font-size: 24px; font-style: italic;">What adventure awaits you?</p>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1: 
        if st.button("🕵️ CHARACTER WIKI", use_container_width=True): navigate_to('wiki')
    with c2: 
        if st.button("📂 GENRE EXPLORER", use_container_width=True): navigate_to('genre')
    with c3: 
        if st.button("🤖 AI RECOMMENDATION", use_container_width=True): navigate_to('recommend')

    if not st.session_state.random_manga_item:
        st.session_state.random_manga_item = get_random_manga_data()
    
    manga = st.session_state.random_manga_item
    if manga:
        st.markdown("---")
        st.markdown('<h3 style="text-align:center; color: #ffd700;">✨ Manga of the Day</h3>', unsafe_allow_html=True)
        with st.container(border=True):
            col_img, col_info = st.columns([1, 3], gap="large")
            with col_img:
                st.image(manga.get('images', {}).get('jpg', {}).get('large_image_url'), use_container_width=True)
                if st.button("🔄 Shuffle New", use_container_width=True):
                    st.session_state.random_manga_item = get_random_manga_data()
                    st.rerun()
            with col_info:
                st.markdown(f"## {manga.get('title_english') or manga.get('title')}")
                st.markdown(f"**⭐ Score:** {manga.get('score')} | **Status:** {manga.get('status')}")
                synopsis = manga.get('synopsis', '')
                if synopsis and len(synopsis) > 600: synopsis = synopsis[:600] + "..."
                st.write(synopsis)

def show_recommend_page():
    set_global_style("test1.jpg")
    show_navbar()
    if st.session_state.show_upgrade_modal: show_upgrade_dialog()
    
    st.title("🤖 AI Personal Recommendation")
    
    with st.container(border=True):
        with st.form("ai_rec_form"):
            c1, c2 = st.columns(2)
            with c1:
                age = st.slider("Age:", 10, 80, 20)
                mood = st.selectbox("Mood:", ["Happy", "Sad", "Adventurous", "Chill", "Dark", "Romantic"])
            with c2:
                ctype = st.selectbox("Type:", ["Anime", "Manga"])
                style = st.selectbox("Style:", ["Action", "Slice of Life", "Psychological", "Fantasy", "Horror"])
            
            interests = st.text_area("Hobbies/Interests:", placeholder="E.g. I like cyberpunk, cats, and complex villains...")
            submit = st.form_submit_button("✨ Generate", type="primary", use_container_width=True)
            
        if submit and interests:
            with st.spinner("🤖 AI is thinking..."):
                recs = get_ai_recommendations(age, interests, mood, style, ctype)
                if recs:
                    st.session_state.recommendations = recs
                    st.rerun()
                else:
                    st.error("AI is busy. Please try again in 2 minutes.")

    if st.session_state.recommendations:
        st.markdown("### 🎯 Recommendations:")
        for i, item in enumerate(st.session_state.recommendations):
            with st.container(border=True):
                st.markdown(f"**#{i+1} {item['title']}** ({item.get('genre','')})")
                st.info(item['reason'])

def show_genre_page():
    set_global_style("test4.jpg")
    show_navbar()
    if st.session_state.show_upgrade_modal: show_upgrade_dialog()
    
    st.title("📂 Genre Explorer")
    col1, col2 = st.columns(2)
    with col1: ctype = st.selectbox("Type:", ["anime", "manga"])
    with col2: sort_by = st.selectbox("Sort:", ["Popularity", "Newest", "Oldest"])
    
    genre_map = get_genre_map(ctype)
    if genre_map:
        selected = st.multiselect("Genres:", sorted(genre_map.keys()))
        if st.button("🔍 Search", type="primary"):
            if not selected: st.warning("Pick a genre!")
            else:
                ids = ",".join([str(genre_map[n]) for n in selected])
                order = "score" if sort_by == "Popularity" else "start_date"
                sort = "desc" if sort_by != "Oldest" else "asc"
                
                url = f"https://api.jikan.moe/v4/{ctype}?genres={ids}&order_by={order}&sort={sort}&limit=10"
                with st.spinner("Fetching..."):
                    try:
                        r = requests.get(url).json()
                        data = r.get('data', [])
                        if data:
                            for item in data:
                                with st.container(border=True):
                                    c1, c2 = st.columns([1, 4])
                                    with c1: st.image(item['images']['jpg']['image_url'], use_container_width=True)
                                    with c2:
                                        st.subheader(item.get('title_english') or item.get('title'))
                                        st.write(item.get('synopsis', '')[:200] + "...")
                                        
                                        mid = item.get('mal_id')
                                        fav = is_favorited(mid, 'media')
                                        if st.button("💔" if fav else "❤️", key=f"g_{mid}"):
                                            toggle_favorite(item, 'media')
                                            st.rerun()
                        else: st.warning("No results.")
                    except: st.error("Error fetching data.")

def show_favorites_page():
    set_global_style("test2.jpg")
    show_navbar()
    if st.session_state.show_upgrade_modal: show_upgrade_dialog()
    
    st.title("❤️ My Favorites")
    t1, t2 = st.tabs(["Media", "Characters"])
    
    with t1:
        items = st.session_state.favorites['media']
        if not items: st.info("Empty.")
        else:
            cols = st.columns(3)
            for i, item in enumerate(items):
                with cols[i%3]:
                    with st.container(border=True):
                        if item.get('image_url'): st.image(item['image_url'])
                        st.write(f"**{item.get('title')}**")
                        if st.button("Remove", key=f"rm_m_{item['mal_id']}"):
                            toggle_favorite(item, 'media')
                            st.rerun()
    with t2:
        items = st.session_state.favorites['characters']
        if not items: st.info("Empty.")
        else:
            cols = st.columns(4)
            for i, item in enumerate(items):
                with cols[i%4]:
                    with st.container(border=True):
                        if item.get('image_url'): st.image(item['image_url'])
                        st.write(f"**{item.get('title')}**")
                        if st.button("Remove", key=f"rm_c_{item['mal_id']}"):
                            toggle_favorite(item, 'characters')
                            st.rerun()

# --- 7. WIKI PAGE - FIX THEO LOGIC CODE MỚI ---
def show_wiki_page():
    set_global_style("test3.jpg")
    show_navbar()
    if st.session_state.show_upgrade_modal: show_upgrade_dialog()
    
    st.title("🕵️ Character Wiki & Vision")
    
    def reset_wiki():
        """Reset wiki state khi search mới"""
        st.session_state.wiki_state = {
            'search_results': [],
            'selected_char': None,
            'ai_analysis': None,
            'mode': None
        }

    def render_profile():
        """Render character profile - GIỐNG CODE MỚI"""
        char = st.session_state.wiki_state['selected_char']
        ai_txt = st.session_state.wiki_state['ai_analysis']  # ← LẤY TỪ STATE
        
        if not char:
            return
        
        st.markdown("---")
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.image(char['images']['jpg']['image_url'], use_container_width=True)
            cid = char['mal_id']
            fav = is_favorited(cid, 'characters')
            if st.button("💔 Unfavorite" if fav else "❤️ Favorite", key=f"w_fav_{cid}", use_container_width=True):
                toggle_favorite(char, 'characters')
                st.rerun()
        
        with c2:
            st.header(char.get('name'))
            st.caption(f"Japanese: {char.get('name_kanji','')}")
            st.write(f"**Favorites:** {char.get('favorites', 0)}")
            
            # *** LOGIC GIỐNG CODE MỚI: Kiểm tra STATE trước ***
            if ai_txt:
                # Đã có trong state → hiển thị
                st.success(ai_txt, icon="📝")
            else:
                # Chưa có → hiện nút generate
                st.info("✨ Want an AI-powered character analysis?")
                
                if st.button("🤖 Generate AI Profile", type="primary", key=f"gen_ai_{cid}"):
                    with st.spinner("🤖 AI is writing..."):
                        # Gọi hàm (đã có @st.cache_data trong ai_service.py)
                        stream = generate_ai_stream(char)
                        
                        full_text = ""
                        if stream:
                            for chunk in stream:
                                if hasattr(chunk, 'text'):
                                    full_text += chunk.text
                        
                        # *** KEY FIX: LƯU VÀO STATE như code mới ***
                        st.session_state.wiki_state['ai_analysis'] = full_text
                        st.rerun()  # Rerun để hiển thị, nhưng lần sau sẽ lấy từ state

    # TABS
    t1, t2 = st.tabs(["🔤 Search Name", "📸 Vision Search"])
    
    with t1:
        def on_search():
            q = st.session_state.wiki_input
            if q:
                reset_wiki()
                st.session_state.wiki_state['mode'] = 'text'
                with st.spinner("🔍 Searching..."):
                    st.session_state.wiki_state['search_results'] = get_character_data(q)
        
        st.text_input("Character Name:", key="wiki_input", on_change=on_search, placeholder="E.g. Naruto, Luffy...")
        
        res = st.session_state.wiki_state['search_results']
        if res:
            opts = {f"{c['name']} (ID: {c['mal_id']})": c for c in res}
            sel = st.selectbox("Select Character:", list(opts.keys()))
            
            chosen = opts[sel]
            current = st.session_state.wiki_state['selected_char']
            
            # Nếu chọn nhân vật MỚI → reset AI analysis
            if not current or current['mal_id'] != chosen['mal_id']:
                st.session_state.wiki_state['selected_char'] = chosen
                st.session_state.wiki_state['ai_analysis'] = None
            
            render_profile()

    with t2:
        uploaded = st.file_uploader("Upload Anime Character Image", type=['jpg','png','jpeg'])
        
        if uploaded:
            st.image(uploaded, width=200)
            
            if st.button("🔍 Identify Character", type="primary"):
                reset_wiki()
                st.session_state.wiki_state['mode'] = 'image'
                
                with st.status("🔍 Scanning image...", expanded=True) as status:
                    name = ai_vision_detect(uploaded)
                    status.write(f"🎯 Detected: **{name}**")
                    
                    if name != "Unknown":
                        time.sleep(1)
                        info = get_one_character_data(name)
                        if info:
                            st.session_state.wiki_state['selected_char'] = info
                            status.update(label="✅ Character Found!", state="complete", expanded=False)
                        else:
                            status.update(label="❌ No database match", state="error")
                    else:
                        status.update(label="❌ Cannot identify character", state="error")
                
                # Rerun để hiển thị profile
                if st.session_state.wiki_state['selected_char']:
                    st.rerun()
            
            # Hiển thị nếu đã có kết quả
            if st.session_state.wiki_state['selected_char']:
                render_profile()
def show_contact_page():
    set_global_style("https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=1964&auto=format&fit=crop")
    show_navbar()
    
    # Show dialog if modal flag is True
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
        return
    
    st.markdown('<div class="content-box"><h2>📞 Contact Us</h2><p>Email: admin@itooklibrary.com</p></div>', unsafe_allow_html=True)


# --- 8. PAGE ROUTER ---
if st.session_state.current_page == 'home': show_homepage()
elif st.session_state.current_page == 'wiki': show_wiki_page()
elif st.session_state.current_page == 'genre': show_genre_page()
elif st.session_state.current_page == 'recommend': show_recommend_page()
elif st.session_state.current_page == 'favorites': show_favorites_page()
elif st.session_state.current_page == 'contact': 
    set_global_style("test.jpg")
    show_navbar()
    if st.session_state.show_upgrade_modal: show_upgrade_dialog()
    st.markdown('<div class="content-box"><h2>Contact</h2><p>admin@itook.com</p></div>', unsafe_allow_html=True)
