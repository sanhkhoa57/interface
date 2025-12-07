import streamlit as st
import google.generativeai as genai
import requests
import json
import re
import os
import time
from datetime import datetime
from style_css import set_global_style
from jikan_services import get_genre_map, get_character_data, get_one_character_data, get_random_manga_data
from ai_service import ai_vision_detect, generate_ai_stream
st.set_page_config(page_title="ITOOK Library", layout="wide", page_icon="📚")

# --- CONFIGURATION ---
# main.py

# --- CONFIGURATION ---
if "GEMINI_API_KEY" in st.secrets: # Thay đổi tên biến tại đây
    API_KEY = st.secrets["GEMINI_API_KEY"] # Và tại đây
elif "GEMINI_API_KEY" in os.environ:
    API_KEY = os.environ["GEMINI_API_KEY"]
else:
    st.error("API Key is missing. Please check secrets.toml.")
    st.stop()

genai.configure(api_key=API_KEY)

# --- SESSION STATE INITIALIZATION ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'

if 'show_upgrade_modal' not in st.session_state:
    st.session_state.show_upgrade_modal = False

if 'favorites' not in st.session_state:
    st.session_state.favorites = {'media': [], 'characters': []}
elif isinstance(st.session_state.favorites, list):
    old_favs = st.session_state.favorites
    st.session_state.favorites = {'media': [], 'characters': []}
    for item in old_favs:
        if item.get('type') == 'Character':
            st.session_state.favorites['characters'].append(item)
        else:
            st.session_state.favorites['media'].append(item)

if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'random_manga_item' not in st.session_state:
    st.session_state.random_manga_item = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None

# --- HELPER FUNCTIONS ---

def navigate_to(page):
    st.session_state.show_upgrade_modal = False  # Reset modal khi chuyển trang
    if page == 'wiki':
        st.session_state.wiki_search_results = None
        st.session_state.wiki_ai_analysis = None
        st.session_state.wiki_selected_char = None
        st.session_state.search_source = None
    st.session_state.current_page = page
    st.rerun()

def add_to_history(action_type, query, details=None):
    entry = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'type': action_type,
        'query': query,
        'details': details
    }
    st.session_state.search_history.insert(0, entry)
    if len(st.session_state.search_history) > 50:
        st.session_state.search_history = st.session_state.search_history[:50]

def is_favorited(item_id, category):
    for item in st.session_state.favorites[category]:
        current_id = item.get('mal_id') or item.get('id')
        if str(current_id) == str(item_id):
            return True
    return False

def toggle_favorite(data, category='media'):
    item_id = data.get('mal_id') or data.get('id')
    title_name = data.get('title') or data.get('name') or data.get('title_english')
    
    if is_favorited(item_id, category):
        st.session_state.favorites[category] = [
            i for i in st.session_state.favorites[category] 
            if str(i.get('mal_id') or i.get('id')) != str(item_id)
        ]
        st.toast(f"💔 Removed '{title_name}' from Favorites", icon="🗑️")
    else:
        fav_item = {
            'mal_id': item_id,
            'title': title_name,
            'image_url': data.get('images', {}).get('jpg', {}).get('image_url') or data.get('image_url'),
            'score': data.get('score'),
            'url': data.get('url'),
            'type': data.get('type', 'Unknown'),
            'added_at': datetime.now().strftime("%Y-%m-%d")
        }
        st.session_state.favorites[category].append(fav_item)
        st.toast(f"❤️ Added '{title_name}' to Favorites", icon="✅")

def get_ai_recommendations(age, interests, mood, style, content_type):
    from ai_service import wait_for_rate_limit
    import time
    
    prompt = f"""
    You are an expert Otaku and Librarian. 
    User Profile:
    - Age: {age}
    - Mood: {mood}
    - Interests/Hobbies: {interests}
    - Preferred Style: {style}
    
    Task: Recommend 5 best {content_type}s that perfectly match this profile.
    
    Return STRICTLY a JSON array with this format (no markdown, no extra text):
    [
      {{
        "title": "Title of work",
        "reason": "Why it fits the user (2 sentences max)",
        "genre": "Main Genre",
        "search_keyword": "Keyword to search this on database"
      }}
    ]
    """
    
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            wait_for_rate_limit(min_interval=5)
            
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith("```json"): 
                text = text[7:-3]
            elif text.startswith("```"): 
                text = text[3:-3]
            
            return json.loads(text)
            
        except Exception as e:
            error_msg = str(e)
            
            if attempt < max_retries - 1 and ("429" in error_msg or "quota" in error_msg.lower()):
                st.warning(f"⏳ API busy. Retrying in 20s...")
                time.sleep(20)
                continue
            else:
                st.error(f"AI Error: {e}")
                return None
    
    return None
# --- UI COMPONENTS ---
def show_navbar():
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1], gap="small", vertical_alignment="center")
        
        with col1: 
            st.markdown('<p class="logo-text">ITOOK Library</p>', unsafe_allow_html=True)
        
        with col2: 
            if st.button("HOME", use_container_width=True): navigate_to('home')
        
        with col3:
            with st.popover("SERVICES", use_container_width=True):
                if st.button("🕵️ Wiki Search", use_container_width=True): navigate_to('wiki')
                if st.button("📂 Genre Explorer", use_container_width=True): navigate_to('genre')
                if st.button("🤖 AI Recommend", use_container_width=True): navigate_to('recommend')
        
        with col4:
            if st.button("ADVANCES", use_container_width=True, key="advances_btn"):
                st.session_state.show_upgrade_modal = True
                st.rerun()
        
        with col5:
            if st.button("CONTACT", use_container_width=True): navigate_to('contact')
    
    # Usage monitor
    if 'api_call_count' in st.session_state and st.session_state.api_call_count > 0:
        st.caption(f"🔄 API Calls: {st.session_state.api_call_count}")
    
    st.write("")

@st.dialog("🚀 Upgrade Your Experience", width="large")
def show_upgrade_dialog():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap');
        
        .upgrade-content {
            font-family: 'Poppins', sans-serif;
            text-align: center;
            padding: 10px;
        }
        
        .upgrade-message {
            font-size: 16px;
            color: #4a5568;
            line-height: 2;
            margin: 20px 0 30px 0;
            padding: 30px;
            background: linear-gradient(135deg, #f0f4ff 0%, #fff0f7 100%);
            border-radius: 20px;
            border-left: 5px solid #667eea;
        }
        
        .upgrade-message p {
            margin: 8px 0;
        }
        
        .highlight-text {
            font-weight: 600;
            color: #667eea;
            font-size: 17px;
        }
        </style>
        
        <div class="upgrade-content">
            <div class="upgrade-message">
                <p>Bạn chưa hài lòng với trải nghiệm hiện tại?</p>
                <p>Bạn muốn sử dụng dịch vụ tốt hơn?</p>
                <p class="highlight-text">Đừng lo! Chúng tôi sẽ đưa bạn đến 1 công cụ mạnh mẽ hơn!</p>
                <p style="font-size: 18px; margin-top: 15px;"><strong>Follow us ✨</strong></p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.link_button(
            "🚀 GO TO ADVANCED VERSION",
            "https://itookwusadvances.streamlit.app/",
            use_container_width=True,
            type="primary"
        )
    
    # Tự động reset flag khi đóng dialog bằng X
    st.session_state.show_upgrade_modal = False

# --- PAGES ---

def show_homepage():
    set_global_style("test.jpg") 
    show_navbar()
    
    # Show dialog if modal flag is True
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog() 
    
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Pacifico&display=swap');
        .hero-title {
            font-family: 'Pacifico', cursive !important;
            font-size: 80px !important;
            color: #ff7f50 !important; 
            text-align: center;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.8) !important; 
            margin-top: 20px;
        }
        .hero-subtitle {
            font-family: 'Montserrat', sans-serif; font-size: 24px !important; color: #e0e0e0 !important;
            text-align: center; margin-top: -20px; margin-bottom: 40px; font-style: italic;
            text-shadow: 2px 2px 4px #000000;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="hero-title">Welcome to ITOOK Library!</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Your gateway to infinite worlds.</p>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        if st.button("🕵️ CHARACTER WIKI", use_container_width=True): navigate_to('wiki')
    with c2:
        if st.button("📂 GENRE EXPLORER", use_container_width=True): navigate_to('genre')
    with c3:
        if st.button("🤖 AI RECOMMENDATION", use_container_width=True): navigate_to('recommend')

    if st.session_state.random_manga_item is None:
        st.session_state.random_manga_item = get_random_manga_data()

    def shuffle_manga():
        st.session_state.random_manga_item = get_random_manga_data()

    manga = st.session_state.random_manga_item
    if manga:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 style="text-align:center; color: #ffd700;">✨ Manga of the Day</h3>', unsafe_allow_html=True)
        
        with st.container(border=True):
            col_img, col_info = st.columns([1, 3], gap="large")
            with col_img:
                img_url = manga.get('images', {}).get('jpg', {}).get('large_image_url')
                if img_url: st.image(img_url, use_container_width=True)
                st.button("🔄 Shuffle New", on_click=shuffle_manga, use_container_width=True)
                
                manga_id = manga.get('mal_id')
                in_fav = is_favorited(manga_id, 'media')
                btn_label = "💔 Remove Favorite" if in_fav else "❤️ Add to Favorites"
                if st.button(btn_label, key="daily_fav_btn", use_container_width=True):
                    toggle_favorite(manga, 'media')
                    st.rerun()

            with col_info:
                title = manga.get('title_english') or manga.get('title')
                st.markdown(f"## {title}")
                st.markdown(f"**⭐ Score:** {manga.get('score', 'N/A')} | **📌 Status:** {manga.get('status', 'Unknown')}")
                
                synopsis = manga.get('synopsis')
                if synopsis and len(synopsis) > 600: synopsis = synopsis[:600] + "..."
                st.write(synopsis)
                
                if manga.get('url'): st.markdown(f"[📖 Read more on MyAnimeList]({manga.get('url')})")

def show_recommend_page():
    set_global_style("test1.jpg")
    show_navbar()
    
    # Show dialog if modal flag is True
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("🤖 AI Personal Recommendation")
    st.markdown("Let our AI analyze your preferences and suggest your next obsession!")
    
    with st.container(border=True):
        with st.form("ai_rec_form"):
            c1, c2 = st.columns(2)
            with c1:
                age = st.slider("🎂 Age:", 10, 80, 20)
                mood = st.selectbox("🎭 Mood:", ["Happy", "Sad", "Adventurous", "Chill", "Dark/Mysterious", "Romantic"])
            with c2:
                content_type = st.selectbox("📺 Looking for:", ["Anime", "Manga", "Light Novel"])
                style = st.selectbox("🎨 Style:", ["Action Packed", "Slow Life", "Mind Bending", "Emotional", "Horror/Thriller"])
            
            interests = st.text_area("💭 Describe your hobbies/interests:", placeholder="E.g. I like coding, cyberpunk themes, complex villains, and cats...")
            
            submit = st.form_submit_button("✨ Generate Recommendations", type="primary", use_container_width=True)
            
        if submit and interests:
            with st.spinner("AI is thinking..."):
                recs = get_ai_recommendations(age, interests, mood, style, content_type)
                if recs:
                    st.session_state.recommendations = recs
                    add_to_history("AI_Recommend", f"{content_type} for {mood} mood", f"Generated {len(recs)} items")
                    st.rerun()
                else:
                    st.error("AI could not generate a response. Please try again.")

    if st.session_state.recommendations:
        st.markdown("### 🎯 Your Results:")
        for idx, item in enumerate(st.session_state.recommendations):
            with st.container(border=True):
                c_a, c_b = st.columns([1, 4])
                with c_a:
                    st.markdown(f"## #{idx+1}")
                with c_b:
                    st.header(item['title'])
                    st.caption(f"Genre: {item.get('genre', 'N/A')}")
                    st.info(item['reason'])
                    search_url = f"https://myanimelist.net/search/all?q={item['title'].replace(' ', '%20')}"
                    st.markdown(f"[🔍 Search on Database]({search_url})")

def show_genre_page():
    set_global_style("test4.jpg")
    show_navbar()
    
    # Show dialog if modal flag is True
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("📂 Genre Explorer")
    
    col_type, col_sort = st.columns(2)
    with col_type: content_type = st.selectbox("📖 Content type:", ["anime", "manga"])
    with col_sort: order_by = st.selectbox("📅 Sort by:", ["Newest", "Oldest", "Most Popular"])

    with st.spinner(f"Loading genre list for {content_type}..."):
        genre_map = get_genre_map(content_type)
    
    if genre_map:
        excluded = ["Hentai", "Ecchi", "Erotica", "Harem"]
        genre_map = {k: v for k, v in genre_map.items() if k not in excluded}
        selected_names = st.multiselect("📚 Choose genres:", sorted(genre_map.keys()))
        
        if st.button("🔍 Start Searching", type="primary", use_container_width=True):
            if not selected_names: st.warning("⚠️ Please choose at least one genre.")
            else:
                selected_ids = [str(genre_map[name]) for name in selected_names]
                genre_params = ",".join(selected_ids)
                sort_param, order_param = "desc", "score"
                if order_by == "Newest": order_param, sort_param = "start_date", "desc"
                elif order_by == "Oldest": order_param, sort_param = "start_date", "asc"
                
                url = f"https://api.jikan.moe/v4/{content_type}?genres={genre_params}&order_by={order_param}&sort={sort_param}&limit=10"
                add_to_history("Genre_Search", f"{content_type}: {', '.join(selected_names)}", f"Sort: {order_by}")
                
                with st.spinner("Fetching data..."):
                    try:
                        r = requests.get(url)
                        if r.status_code == 200:
                            data = r.json().get('data', [])
                            if data:
                                st.success(f"✅ Found {len(data)} results!")
                                st.markdown("---")
                                for item in data:
                                    with st.container(border=True):
                                        c1, c2 = st.columns([1, 4])
                                        with c1: 
                                            st.image(item.get('images', {}).get('jpg', {}).get('image_url'), use_container_width=True)
                                            manga_id = item.get('mal_id')
                                            in_fav = is_favorited(manga_id, 'media')
                                            btn_label = "💔" if in_fav else "❤️ Add"
                                            if st.button(btn_label, key=f"fav_btn_{manga_id}", use_container_width=True):
                                                toggle_favorite(item, 'media')
                                                st.rerun()
                                        with c2:
                                            st.subheader(f"📺 {item.get('title_english') or item.get('title')}")
                                            st.write(f"**Summary:** {item.get('synopsis', 'No summary')[:250]}...")
                                            st.markdown(f"[🔗 View on MyAnimeList]({item.get('url', '#')})")
                            else: st.warning("No results found.")
                    except: st.error("Connection Error")

def show_favorites_page():
    set_global_style("https://wallpapers.com/images/hd/aesthetic-anime-bedroom-lq7b5j3x5x5y5x5.jpg")
    show_navbar()
    
    # Show dialog if modal flag is True
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.title("❤️ My Favorites Collection")
    
    tab1, tab2 = st.tabs(["📚 Anime & Manga", "🦸 Characters"])
    
    with tab1:
        media_list = st.session_state.favorites['media']
        if not media_list:
            st.info("No Anime/Manga in favorites yet.")
        else:
            st.write(f"Count: {len(media_list)}")
            cols = st.columns(3)
            for i, item in enumerate(media_list):
                with cols[i % 3]:
                    with st.container(border=True):
                        if item.get('image_url'): st.image(item['image_url'], use_container_width=True)
                        st.subheader(item.get('title'))
                        st.caption(f"Score: {item.get('score', 'N/A')}")
                        if st.button("💔 Remove", key=f"rm_media_{item['mal_id']}", use_container_width=True):
                            toggle_favorite(item, 'media')
                            st.rerun()
                            
    with tab2:
        char_list = st.session_state.favorites['characters']
        if not char_list:
            st.info("No Characters in favorites yet.")
        else:
            st.write(f"Count: {len(char_list)}")
            cols = st.columns(4)
            for i, item in enumerate(char_list):
                with cols[i % 4]:
                    with st.container(border=True):
                        if item.get('image_url'): st.image(item['image_url'], use_container_width=True)
                        st.subheader(item.get('title'))
                        if st.button("💔 Remove", key=f"rm_char_{item['mal_id']}", use_container_width=True):
                            toggle_favorite(item, 'characters')
                            st.rerun()

def show_history_page():
    set_global_style("test1.png") 
    show_navbar()
    
    # Show dialog if modal flag is True
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.title("📜 Activity History")
    
    if st.button("🗑️ Clear History"):
        st.session_state.search_history = []
        st.rerun()
        
    history = st.session_state.search_history
    if not history:
        st.info("No activity recorded yet.")
    else:
        for item in history:
            with st.expander(f"🕒 {item['timestamp']} - {item['type']}"):
                st.write(f"**Query:** {item['query']}")
                if item.get('details'):
                    st.caption(f"Details: {item['details']}")

def show_wiki_page():
    set_global_style("test3.jpg")
    show_navbar()
    
    # Show dialog if modal flag is True
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
    
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.title("🕵️ Character Wiki & Vision")
    
    if 'wiki_search_results' not in st.session_state: st.session_state.wiki_search_results = None
    if 'wiki_ai_analysis' not in st.session_state: st.session_state.wiki_ai_analysis = None
    if 'wiki_selected_char' not in st.session_state: st.session_state.wiki_selected_char = None
    if 'search_source' not in st.session_state: st.session_state.search_source = None

    def clear_previous_results():
        st.session_state.wiki_search_results = None
        st.session_state.wiki_ai_analysis = None
        st.session_state.wiki_selected_char = None
        st.session_state.search_source = None

    def display_final_result():
        if st.session_state.wiki_ai_analysis and st.session_state.wiki_selected_char:
            info = st.session_state.wiki_selected_char
            ai_text = st.session_state.wiki_ai_analysis
            st.markdown("---")
            c_img, c_info = st.columns([1, 2])
            with c_img: 
                st.image(info['images']['jpg']['image_url'], use_container_width=True)
                
                char_id = info['mal_id']
                in_fav = is_favorited(char_id, 'characters')
                btn_label = "💔 Unfavorite" if in_fav else "❤️ Favorite Character"
                if st.button(btn_label, key="wiki_char_fav"):
                    toggle_favorite(info, 'characters')
                    st.rerun()
                    
            with c_info:
                st.header(info['name'])
                st.subheader(f"Japanese: {info.get('name_kanji', '')}")
                st.success(ai_text, icon="📝")

    tab1, tab2 = st.tabs(["🔤 Search by Name", "📸 Search by Image"])
    
    with tab1:
        def execute_text_search():
            query = st.session_state.search_input
            if query:
                clear_previous_results()
                st.session_state.search_source = "text"
                st.session_state.wiki_search_results = get_character_data(query)
                add_to_history("Wiki_Search_Text", query, "Searched by name")

        st.text_input("Enter Character Name:", placeholder="E.g: Naruto...", key="search_input", on_change=execute_text_search)

        if st.session_state.wiki_search_results:
            results = st.session_state.wiki_search_results
            if len(results) > 0:
                char_opts = {f"{c['name']} (ID: {c['mal_id']})": c for c in results}
                selected_key = st.selectbox("Select character:", list(char_opts.keys()), key="char_select_box")
                
                if st.button("🚀 Analyze Profile", type="primary", use_container_width=True):
                    selected_info = char_opts[selected_key]
                    st.session_state.wiki_selected_char = selected_info
                    st.session_state.search_source = "text"
                    
                    st.markdown("---")
                    c1, c2 = st.columns([1, 2])
                    with c1: st.image(selected_info['images']['jpg']['image_url'], use_container_width=True)
                    with c2:
                        st.header(selected_info['name'])
                        placeholder = st.empty()
                        full_text = ""
                        try:
                            stream_response = generate_ai_stream(selected_info)
                            for chunk in stream_response:
                                if hasattr(chunk, 'text'):
                                    full_text += chunk.text
                                    placeholder.success(full_text + "▌", icon="📝") 
                            placeholder.success(full_text, icon="📝")
                            st.session_state.wiki_ai_analysis = full_text
                            add_to_history("Wiki_Analysis", selected_info['name'], "AI Profile Generated")
                        except Exception as e: st.error(f"AI Error: {e}")
            else: st.warning("No character found.")
        elif st.session_state.search_source == "text" and st.session_state.wiki_ai_analysis:
            display_final_result()

    with tab2:
        st.info("Upload an anime screenshot.")
        uploaded = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"], key="vision_uploader")
        
        if uploaded:
            st.image(uploaded, width=150, caption="Preview")
            if st.button("🚀 Scan Character", key="btn_scan_vision", type="primary"):
                clear_previous_results()
                st.session_state.search_source = "image"
                with st.spinner("Gemini is Identifying..."):
                    name = ai_vision_detect(uploaded)
                    add_to_history("Wiki_Vision", "Image Upload", f"Detected: {name}")
                if name != "Unknown":
                    st.success(f"Detected: **{name}**")
                    info = get_one_character_data(name)
                    if info:
                        st.session_state.wiki_selected_char = info
                        st.markdown("---")
                        c1, c2 = st.columns([1, 2])
                        with c1: st.image(info['images']['jpg']['image_url'], use_container_width=True)
                        with c2:
                            st.header(info['name'])
                            placeholder = st.empty()
                            full_text = ""
                            try:
                                stream_response = generate_ai_stream(info)
                                for chunk in stream_response:
                                    if hasattr(chunk, 'text'):
                                        full_text += chunk.text
                                        placeholder.success(full_text + "▌", icon="📝")
                                placeholder.success(full_text, icon="📝")
                                st.session_state.wiki_ai_analysis = full_text
                            except Exception as e: st.error(f"AI Error: {e}")
                    else: st.warning(f"Found '{name}' but no info on MyAnimeList.")
                else: st.error("Cannot identify character.")
        elif st.session_state.search_source == "image" and st.session_state.wiki_ai_analysis:
            display_final_result()

def show_contact_page():
    set_global_style("https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=1964&auto=format&fit=crop")
    show_navbar()
    
    # Show dialog if modal flag is True
    if st.session_state.show_upgrade_modal:
        show_upgrade_dialog()
        return
    
    st.markdown('<div class="content-box"><h2>📞 Contact Us</h2><p>Email: admin@itooklibrary.com</p></div>', unsafe_allow_html=True)

# --- MAIN ROUTER ---

if st.session_state.current_page == 'home': 
    show_homepage()
elif st.session_state.current_page == 'wiki': 
    show_wiki_page()
elif st.session_state.current_page == 'genre': 
    show_genre_page()
elif st.session_state.current_page == 'recommend': 
    show_recommend_page()
elif st.session_state.current_page == 'favorites': 
    show_favorites_page()
elif st.session_state.current_page == 'history':
    show_history_page()
elif st.session_state.current_page == 'contact': 
    show_contact_page()
