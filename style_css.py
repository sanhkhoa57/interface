import streamlit as st
import base64
import os

def get_base64_of_bin_file(filename):
    file_path = os.path.join(os.getcwd(), "resources", filename)
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

def set_global_style(bg_source):
    background_css = ""

    if bg_source.startswith("#"):
        background_css = f"""
            background-color: {bg_source} !important;
            background-image: none !important;
        """
    elif bg_source.startswith("http"):
        background_css = f"""
            background-image: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), url("{bg_source}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        """
    else:
        b64_data = get_base64_of_bin_file(bg_source)
        if b64_data:
            ext = "jpeg" if bg_source.lower().endswith((".jpg", ".jpeg")) else "png"
            background_css = f"""
                background-image: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), url("data:image/{ext};base64,{b64_data}");
                background-size: cover;
                background-attachment: fixed;
                background-position: center;
            """
        else:
            background_css = "background-color: #0e1117;"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&display=swap');

    @keyframes fadeOutLoader {{
        0% {{ opacity: 1; }}
        70% {{ opacity: 1; }} 
        100% {{ opacity: 0; visibility: hidden; }}
    }}

    .stApp::before {{
        content: "Loading ITOOK Library...";
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: #0a0a15;
        z-index: 999999;
        display: flex;
        justify-content: center;
        align-items: center;
        color: #ff7f50; 
        font-family: 'Montserrat', sans-serif;
        font-size: 40px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 5px;
        animation: fadeOutLoader 1.2s ease-in-out forwards;
        pointer-events: none;
    }}

    .stApp {{ {background_css} }}
    
    .logo-text {{
        font-family: 'Montserrat', 'Arial Black', sans-serif !important;
        font-size: 30px !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
        text-shadow: 3px 3px 0px #ff7f50;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.2 !important;
        letter-spacing: -1px;
    }}

    h1, h2, h3, h4, p, span, div, label, li {{
        color: white !important;
        text-shadow: 1px 1px 2px #000000 !important; 
        font-weight: 500;
        font-family: 'Montserrat', sans-serif;
    }}

    /* Hide standard Streamlit elements */
    header {{display: none !important;}}
    [data-testid="stHeader"] {{display: none !important;}}
    .stStatusWidget, [data-testid="stStatusWidget"] {{visibility: hidden !important; display: none !important;}}
    div[data-testid="stDecoration"] {{ display: none !important; }}
    .block-container {{ padding-top: 1rem !important; }}

    /* Navigation Bar Styling */
    div[data-testid="stHorizontalBlock"] button {{
        background-color: transparent !important;
        border: 0px solid transparent !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0px !important;
        color: #FFFFFF !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        text-shadow: 2px 2px 4px #000000 !important;
        transition: all 0.3s ease;
        padding: 0 5px !important;
    }}

    div[data-testid="stHorizontalBlock"] button:hover {{
        color: #ff7f50 !important;
        transform: translateY(-2px);
        text-shadow: 0 0 10px #ff7f50, 2px 2px 4px #000000 !important;
        border-bottom: 2px solid #ff7f50 !important;
    }}

    /* Card Containers */
    div[data-testid="stVerticalBlockBorderWrapper"], div.stContainer {{
        background-color: rgba(10, 10, 21, 0.85) !important; 
        border: 1px solid #ff7f50 !important;
        border-radius: 12px !important;
        padding: 15px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(4px);
    }}
    
    /* Inputs */
    .stTextArea textarea {{
        background-color: rgba(0,0,0,0.7) !important;
        color: white !important;
        border: 1px solid #444 !important;
    }}

    /* Buttons */
    button[kind="primary"] {{
        background: linear-gradient(90deg, #ff7f50, #ff4500) !important;
        color: white !important; border: none !important;
        box-shadow: 0 4px 15px rgba(255, 69, 0, 0.3);
        font-weight: bold !important;
        transition: transform 0.2s;
    }}
    button[kind="primary"]:hover {{
        transform: scale(1.02);
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 20px;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        white-space: pre-wrap;
        background-color: rgba(0,0,0,0.5);
        border-radius: 5px;
        color: white;
        border: 1px solid transparent;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: #ff7f50 !important;
        color: white !important;
        font-weight: bold;
    }}
    </style>
    """, unsafe_allow_html=True)

