# pyrefly: ignore [missing-import]
import streamlit as st
import os

def inject_custom_css():
    # Read config to determine theme
    is_dark = True
    config_path = ".streamlit/config.toml"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            if 'base="light"' in f.read():
                is_dark = False

    if is_dark:
        card_bg = "rgba(30, 34, 45, 0.7)"
        text_color = "#FFFFFF"
        label_color = "#8B949E"
        border_color = "rgba(255, 255, 255, 0.05)"
    else:
        card_bg = "rgba(240, 242, 246, 0.7)"
        text_color = "#000000"
        label_color = "#555555"
        border_color = "rgba(0, 0, 0, 0.05)"

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    .stApp {{
        font-family: 'Inter', sans-serif;
    }}
    
    h1 {{
        font-size: 3.2rem !important;
        font-weight: 800 !important;
        margin-bottom: 0.2rem !important;
        background: -webkit-linear-gradient(45deg, #4facfe, #00f2fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    
    .subtitle {{
        color: {label_color};
        font-size: 1.2rem;
        font-weight: 400;
        margin-bottom: 2rem;
        line-height: 1.6;
    }}
    
    .metric-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 24px 20px;
        margin-bottom: 20px;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease-in-out;
    }}
    
    .metric-card:hover {{
        transform: translateY(-5px);
        border-color: rgba(79, 172, 254, 0.5);
        box-shadow: 0 15px 30px rgba(79, 172, 254, 0.2);
    }}
    
    .metric-label {{
        font-size: 0.95rem;
        color: {label_color};
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
        margin-bottom: 8px;
    }}
    
    .metric-value {{
        font-size: 2.2rem;
        font-weight: 700;
        color: {text_color};
        margin: 0;
    }}
    
    /* Sửa chữ app thành Trang Chủ ở Sidebar (Thu nhỏ chữ gốc thành 0px và chèn chữ mới bằng ::after trên cùng thẻ p) */
    [data-testid="stSidebarNavItems"] > li:first-child p,
    [data-testid="stSidebarNavItems"] > div:first-child p,
    [data-testid="stSidebarNavItems"] > ul > li:first-child p,
    [data-testid="stSidebarNavItems"] a[href="/"] p {{
        font-size: 0px !important;
    }}
    
    [data-testid="stSidebarNavItems"] > li:first-child p::after,
    [data-testid="stSidebarNavItems"] > div:first-child p::after,
    [data-testid="stSidebarNavItems"] > ul > li:first-child p::after,
    [data-testid="stSidebarNavItems"] a[href="/"] p::after {{
        content: "🏠 Trang Chủ" !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        visibility: visible !important;
        display: inline-block !important;
    }}
    
    section[data-testid="stSidebar"] {{
        box-shadow: 2px 0 15px rgba(0, 0, 0, 0.15) !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a {{
        border-radius: 8px !important;
        margin: 6px 12px !important;
        padding: 10px 16px !important;
        transition: all 0.3s ease-in-out !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a:hover {{
        background-color: rgba(79, 172, 254, 0.12) !important;
        color: #4facfe !important;
        transform: translateX(3px);
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] .active {{
        background-color: rgba(79, 172, 254, 0.18) !important;
        font-weight: 700 !important;
        border-left: 3px solid #4facfe !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def switch_theme(is_dark):
    config_dir = ".streamlit"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        
    config_path = os.path.join(config_dir, "config.toml")
    
    if is_dark:
        content = """[theme]
base="dark"
primaryColor="#ffd400"
backgroundColor="#0E1117"
secondaryBackgroundColor="#161B22"
textColor="#E0E6ED"
font="sans serif"
"""
    else:
        content = """[theme]
base="light"
primaryColor="#ffd400"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F0F2F6"
textColor="#31333F"
font="sans serif"
"""
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)

def render_top_bar():
    # Detect current theme to set toggle state
    is_dark_current = True
    config_path = ".streamlit/config.toml"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            if 'base="light"' in f.read():
                is_dark_current = False

    # Top right container
    cols = st.columns([8, 1, 1])
    
    with cols[1]:
        # Theme toggle
        theme_label = "🌙 Dark" if is_dark_current else "☀️ Light"
        if st.button(theme_label, key="theme_toggle", use_container_width=True):
            switch_theme(not is_dark_current)
            st.rerun()
            
    with cols[2]:
        # Language selectbox
        lang = st.session_state.get("lang", "vi")
        new_lang = st.selectbox(
            "Lang", 
            ["vi", "en"], 
            index=0 if lang == "vi" else 1,
            label_visibility="collapsed",
            key="lang_selector"
        )
        if new_lang != lang:
            st.session_state.lang = new_lang
            st.rerun()

def render_page_header(title, subtitle, icon="", color_preset="blue"):
    presets = {
        "blue": "linear-gradient(135deg, #0D47A1 0%, #1976D2 100%)",
        "green": "linear-gradient(135deg, #00796B 0%, #009688 100%)",
        "orange": "linear-gradient(135deg, #FF6F00 0%, #FF9800 100%)",
        "purple": "linear-gradient(135deg, #4A148C 0%, #8E24AA 100%)",
        "dark": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
        "pink": "linear-gradient(135deg, #C2185B 0%, #EC407A 100%)"
    }
    gradient = presets.get(color_preset, presets["blue"])
    header_html = f"""
    <div style="
        background: {gradient};
        padding: 30px;
        border-radius: 15px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    ">
        <h2 style="
            font-family: 'Inter', sans-serif;
            font-size: 2.2rem;
            font-weight: 700;
            margin: 0;
            color: white !important;
        ">{icon} {title}</h2>
        <div style="
            font-size: 1.1rem;
            opacity: 0.9;
            margin-top: 5px;
            font-weight: 400;
        ">{subtitle}</div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

def log_activity(username, page_name):
    """
    Ghi nhận lịch sử hoạt động tác nghiệp của người dùng (Logging).
    """
    import datetime
    import csv
    import os
    try:
        os.makedirs("data", exist_ok=True)
        log_file = "data/access_logs.csv"
        file_exists = os.path.exists(log_file)
        with open(log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Username", "Page"])
            writer.writerow([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                username,
                page_name
            ])
    except Exception:
        pass

def check_authentication(page_name="Trang Chủ"):
    """
    Xác thực người dùng bảo mật cao (Authentication Form) và ghi nhận hoạt động (Logging).
    Áp dụng cho cả trang chủ và toàn bộ trang con.
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        
    if not st.session_state.authenticated:
        # Form Đăng Nhập Glassmorphism tuyệt vời
        st.markdown("""
        <div style="text-align: center; margin-top: 50px; margin-bottom: 20px;">
            <h1 style="font-size: 2.8rem !important; font-weight: 800; background: -webkit-linear-gradient(45deg, #ff4b4b, #8e24aa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🔒 SUPERSTORE ANALYTICS</h1>
            <p style="color: gray; font-size: 1.1rem;">Cổng thông tin phân tích kinh doanh nội bộ chuyên nghiệp. Vui lòng đăng nhập để tiếp tục.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            with st.form("login_form", clear_on_submit=False):
                st.markdown("<h3 style='text-align: center; margin-bottom: 15px;'>🔑 Hệ Thống Đăng Nhập</h3>", unsafe_allow_html=True)
                username = st.text_input("Tên đăng nhập (Username)", value="admin")
                password = st.text_input("Mật khẩu (Password)", type="password", value="admin123")
                submit = st.form_submit_button("🔑 XÁC THỰC DANH TÍNH", use_container_width=True)
                
                if submit:
                    if username == "admin" and password == "admin123":
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        log_activity(username, "Đăng nhập thành công")
                        st.success("Xác thực thành công! Đang chuyển hướng...")
                        st.rerun()
                    else:
                        st.error("Sai tên đăng nhập hoặc mật khẩu! Vui lòng thử lại.")
        
        # Thêm nút thoát chương trình để chặn truy cập
        st.stop()
    else:
        # Nếu đã đăng nhập, ghi log hoạt động xem trang hiện tại
        log_activity(st.session_state.get("username", "admin"), page_name)
