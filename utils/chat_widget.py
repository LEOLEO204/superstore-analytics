# pyrefly: ignore [missing-import]
import streamlit as st
from utils.chatbot_logic import get_ai_agent, ask_agent
from utils.i18n import t
import os
def render_floating_chat(df, rfm_df):
    # Read current theme to apply dynamic styling
    is_dark = True
    config_path = ".streamlit/config.toml"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            if 'base="light"' in f.read():
                is_dark = False

    if is_dark:
        window_bg = "#161b22"
        text_color = "#e0e6ed"
        border_color = "rgba(255, 255, 255, 0.08)"
        msg_bg = "#21262d"
        input_bg = "#21262d"
        header_border = "rgba(255, 255, 255, 0.1)"
        header_text = "#ffffff"
    else:
        window_bg = "#ffffff"
        text_color = "#31333f"
        border_color = "rgba(0, 0, 0, 0.08)"
        msg_bg = "#f0f2f6"
        input_bg = "#f0f2f6"
        header_border = "#eee"
        header_text = "#000000"

    floating_css = f"""
    <style>
    /* 1. Nút bấm Floating */
    div.element-container:has(.chat-btn-anchor),
    div[data-testid="element-container"]:has(.chat-btn-anchor) {{
        display: none !important;
    }}
    
    div.element-container:has(.chat-btn-anchor) + div.element-container,
    div[data-testid="element-container"]:has(.chat-btn-anchor) + div[data-testid="element-container"] {{
        position: fixed !important;
        bottom: 30px !important;
        right: 30px !important;
        z-index: 99999 !important;
        width: 70px !important;
        height: 70px !important;
    }}
    
    div.element-container:has(.chat-btn-anchor) + div.element-container button,
    div[data-testid="element-container"]:has(.chat-btn-anchor) + div[data-testid="element-container"] button {{
        border-radius: 50% !important;
        width: 70px !important;
        height: 70px !important;
        background-color: #ffd400 !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        color: #000 !important;
    }}
    
    div.element-container:has(.chat-btn-anchor) + div.element-container button p,
    div[data-testid="element-container"]:has(.chat-btn-anchor) + div[data-testid="element-container"] button p {{
        font-size: 35px !important;
        margin: 0 !important;
    }}

    /* 2. Cửa sổ Chat Floating */
    div.element-container:has(.chat-window-anchor),
    div[data-testid="element-container"]:has(.chat-window-anchor) {{
        display: none !important;
    }}
    
    div.element-container:has(.chat-window-anchor) + div,
    div[data-testid="element-container"]:has(.chat-window-anchor) + div,
    div[data-testid="element-container"]:has(.chat-window-anchor) + div[data-testid="element-container"],
    div[data-testid="element-container"]:has(.chat-window-anchor) + div[data-testid="stVerticalBlockBorderWrapper"] {{
        position: fixed !important;
        bottom: 110px !important;
        right: 30px !important;
        width: 380px !important;
        height: 580px !important;
        max-height: 85vh !important;
        z-index: 99999 !important;
        background-color: {window_bg} !important;
        border-radius: 15px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2) !important;
        padding: 20px !important;
        border: 1px solid {border_color} !important;
        display: flex !important;
        flex-direction: column !important;
    }}
    
    /* Ghi đè màu nền mặc định của thẻ container chứa form */
    div.element-container:has(.chat-window-anchor) + div [data-testid="stForm"],
    div[data-testid="element-container"]:has(.chat-window-anchor) + div [data-testid="stForm"],
    div[data-testid="element-container"]:has(.chat-window-anchor) + div[data-testid="element-container"] [data-testid="stForm"] {{
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
    }}
    
    /* Style chat messages */
    .chat-user {{
        background-color: {msg_bg} !important;
        padding: 12px 16px;
        border-radius: 20px 20px 0 20px;
        margin-bottom: 12px;
        color: {text_color} !important;
        text-align: right;
        display: inline-block;
        float: right;
        clear: both;
        max-width: 85%;
        font-size: 14px;
    }}
    
    .chat-ai {{
        background-color: {msg_bg} !important;
        padding: 12px 16px;
        border-radius: 20px 20px 20px 0;
        margin-bottom: 12px;
        color: {text_color} !important;
        text-align: left;
        display: inline-block;
        float: left;
        clear: both;
        max-width: 85%;
        font-size: 14px;
        border-left: 3px solid #ffd400;
    }}
    
    .chat-footer {{
        font-size: 11px;
        color: #999;
        text-align: center;
        clear: both;
        margin-top: 10px;
    }}
    
    /* Căn chỉnh nút gửi tin nhắn cao bằng với khung nhập liệu st.text_area */
    div.element-container:has(.chat-window-anchor) + div div[data-testid="column"]:nth-child(2) button {{
        height: 68px !important;
        margin-top: 0px !important;
    }}
    
    /* Ẩn dòng chữ 'Press Ctrl+Enter to apply' của st.text_area */
    div[data-testid="InputInstructions"] {{
        display: none !important;
    }}
    </style>
    """
    st.markdown(floating_css, unsafe_allow_html=True)
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "ai", "content": t("ai_greeting_1")},
            {"role": "ai", "content": t("ai_greeting_2")}
        ]
        
    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False
        
    def toggle_chat():
        st.session_state.chat_open = not st.session_state.chat_open

    def handle_chat_submit():
        user_input = st.session_state.user_msg_input
        if user_input:
            # Chỉ thêm nếu tin nhắn chưa tồn tại ở cuối lịch sử (tránh lỗi double submit của Streamlit)
            if not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.is_thinking = True
            st.session_state.user_msg_input = ""

    # 1. Nút bấm nổi
    st.markdown('<span class="chat-btn-anchor"></span>', unsafe_allow_html=True)
    st.button("🤖", on_click=toggle_chat, key="chat_toggle_btn")

    # 2. Cửa sổ chat
    if st.session_state.chat_open:
        st.markdown('<span class="chat-window-anchor"></span>', unsafe_allow_html=True)
        chat_window = st.container()
        with chat_window:
            # Header
            st.markdown(f'<div style="display:flex; align-items:center; border-bottom: 1px solid {header_border}; padding-bottom: 10px; margin-bottom: 15px;"><div style="background-color:#ffd400; border-radius:50%; width:35px; height:35px; display:flex; justify-content:center; align-items:center; margin-right:10px; font-size:20px;">🤖</div><div style="font-weight:bold; font-size: 16px; color:{header_text};">{t("ai_assistant")}</div></div>', unsafe_allow_html=True)
            
            # Chat history container
            chat_container = st.container(height=215, border=False)
            
            # Display history
            with chat_container:
                for msg in st.session_state.chat_history:
                    if msg["role"] == "user":
                        st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="chat-ai">{msg["content"]}</div>', unsafe_allow_html=True)
                        
                if st.session_state.get("is_thinking", False):
                    st.markdown(f'<div class="chat-ai">{t("analyzing_data")}</div>', unsafe_allow_html=True)
                
                # Tự động cuộn xuống cuối khung chat bằng JS khi có tin nhắn mới (sử dụng độ trễ để bảo đảm React đã render xong)
                st.markdown('<img src="does-not-exist" onerror="setTimeout(function(){var doc=window.parent.document||document;var blocks=doc.querySelectorAll(\'div[data-testid=stVerticalBlock]\');blocks.forEach(function(b){if(b.scrollHeight>b.clientHeight){b.scrollTop=b.scrollHeight;}});},100);" style="display:none;"/>', unsafe_allow_html=True)
            
            # FAQ Quick Suggestions Row (Nút bấm hỏi nhanh FAQ)
            faq_options = [
                ("📊 RFM là gì?", "Phân tích phân khúc khách hàng bằng RFM là gì và nó giúp ích gì cho doanh nghiệp?"),
                ("🔮 Dự báo thế nào?", "Giải thích giúp em thuật toán và mô hình dự báo doanh số ở Trang 5 được không?"),
                ("🔬 Welch t-test?", "Tại sao chúng ta phải dùng Welch t-test thay vì Student t-test trong kiểm định kinh doanh?"),
                ("🛠️ Feature Engineering?", "Lợi ích của việc biến đổi Logarithm và Scaling trong Kỹ nghệ đặc trưng là gì?")
            ]
            
            st.markdown("<div style='font-size: 11px; font-weight: bold; margin-bottom: 5px; color:#999; margin-top: 5px;'>💡 Hỏi nhanh Trợ lý (FAQ):</div>", unsafe_allow_html=True)
            faq_cols = st.columns(2)
            for idx, (btn_label, full_question) in enumerate(faq_options):
                col_idx = idx % 2
                with faq_cols[col_idx]:
                    if st.button(btn_label, key=f"faq_btn_{idx}", use_container_width=True):
                        st.session_state.chat_history.append({"role": "user", "content": full_question})
                        st.session_state.is_thinking = True
                        st.session_state.is_direct_faq = True # Flag khẩn cấp để bỏ qua router
                        st.rerun()

            # Input row (Sử dụng text_area thay vì text_input để hiển thị trọn vẹn câu hỏi dài của người dùng)
            cols = st.columns([5, 1])
            with cols[0]:
                st.text_area("Nhập tin nhắn...", label_visibility="collapsed", placeholder=t("type_message"), key="user_msg_input", on_change=handle_chat_submit, height=68)
            with cols[1]:
                if st.button("➤", key="send_btn"):
                    user_input = st.session_state.get("user_msg_input", "")
                    if user_input:
                        # Chỉ thêm nếu tin nhắn chưa tồn tại ở cuối lịch sử (tránh lỗi double submit của Streamlit)
                        if not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != user_input:
                            st.session_state.chat_history.append({"role": "user", "content": user_input})
                            st.session_state.is_thinking = True
                        st.session_state.user_msg_input = ""
                        st.rerun()
                
            # Nếu đang thinking thì gọi agent
            if st.session_state.get("is_thinking", False):
                try:
                    agent = get_ai_agent(df, rfm_df)
                    if agent:
                        # Định dạng lịch sử hội thoại để cung cấp trí nhớ (Memory) cho AI
                        history_str = ""
                        # Lấy tối đa 12 tin nhắn gần nhất để tạo "Vùng Huấn Luyện Ngắn Hạn" liên tục cho AI
                        recent_history = st.session_state.chat_history[:-1][-12:]
                        for msg in recent_history:
                            role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý AI (Em)"
                            history_str += f"{role_label}: {msg['content']}\n"
                            
                        full_prompt = f"""
                        --- BỘ NHỚ HỌC TẬP TRONG PHIÊN (CONVERSATIONAL TRAINING DATA) ---
                        Đọc kỹ nội dung trao đổi trước đó bên dưới để THẤU HIỂU thói quen, sở thích và lịch sử tư vấn cho người dùng:
                        {history_str}
                        -----------------------------------------------------------------
                        
                        YÊU CẦU MỚI NHẤT: {st.session_state.chat_history[-1]["content"]}
                        
                        YÊU CẦU VẬN HÀNH (LEARNING & ANALYSIS):
                        1. Luôn phân tích TOÀN BỘ DỮ LIỆU (df1, df2) nếu có câu hỏi về số liệu, không ước lượng.
                        2. Sử dụng BỘ NHỚ HỌC TẬP ở trên để cá nhân hóa câu trả lời, đảm bảo tính liên kết cực cao với các câu hỏi cũ.
                        3. Phong cách: Niềm nở, thân thiện, xưng "Em" gọi "Anh/Chị". Phân tích thông minh, ngắn gọn, đi thẳng vào trọng tâm.
                        """
                        # Trả lại quyền xử lý toàn diện cho Router thông minh của ask_agent
                        res = ask_agent(agent, full_prompt)
                        st.session_state.chat_history.append({"role": "ai", "content": res})
                    else:
                        # NẾU THIẾU KEY
                        st.session_state.chat_history.append({
                            "role": "ai", 
                            "content": "⚠️ Không tìm thấy API Key hợp lệ. Vui lòng cấu hình API Key trong file `.env` hoặc Streamlit Secrets."
                        })
                except Exception as e:
                    st.session_state.chat_history.append({"role": "ai", "content": f"❌ Lỗi hệ thống AI: {str(e)}"})
                finally:
                    st.session_state.is_thinking = False
                    st.rerun()
                
            st.markdown(f'<div class="chat-footer">{t("ai_disclaimer")}</div>', unsafe_allow_html=True)
