# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import os
import os
import sys
# Thêm thư mục gốc vào sys.path để có thể import module utils
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "..", "..")) if "pages" in current_dir else os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.data_processor import load_and_clean_data, calculate_rfm
from utils.chatbot_logic import get_ai_agent, ask_agent
from utils.chat_widget import render_floating_chat
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header
from utils.i18n import t

st.set_page_config(page_title="Trợ Lý AI", layout="wide")
import importlib
import utils.ui_components
importlib.reload(utils.ui_components)
from utils.ui_components import check_authentication
check_authentication("Trợ Lý AI")
inject_custom_css()
render_top_bar()

render_page_header("Trợ Lý Chiến Lược", "Trung tâm lập báo cáo chiến lược tự động theo quy tắc Python", "🤖", "dark")

def get_data():
    df = load_and_clean_data()
    rfm_df = calculate_rfm(df)
    return df, rfm_df

df, rfm_df = get_data()

# Báo cáo Chiến lược hoàn toàn chạy bằng Python cục bộ cực kỳ nhanh theo chuẩn SOP mới!
st.subheader(t('auto_strategy_proposal'))
st.markdown("Hệ thống sử dụng **Analytics Engine Rule-based bằng Python** để tổng hợp và soạn thảo báo cáo học thuật chuyên sâu chỉ trong chưa đầy 0.1 giây mà không cần phụ thuộc vào các mô hình AI đám mây chậm chạp.")

# Sử dụng Session State để lưu trữ báo cáo
if 'last_ai_report' not in st.session_state:
    st.session_state.last_ai_report = None
    
if st.button("⚡ Tạo Báo cáo Chiến lược (Tức thời theo Quy tắc)", use_container_width=True):
    with st.spinner("Hệ thống đang tổng hợp số liệu và lập văn bản báo cáo..."):
        # CHỈ KHỞI TẠO KHI THỰC SỰ BẤM NÚT
        agent = get_ai_agent(df, rfm_df)
        
        # Xây dựng câu lệnh đại diện cho hành vi tạo báo cáo đồ án tốt nghiệp
        prompt = "Tạo báo cáo phân tích chiến lược kinh doanh học thuật cho đồ án tốt nghiệp"
        
        try:
            # Gọi ask_agent với tham số đầy đủ để chạy Rule-based report generator
            report = ask_agent(agent, prompt, df=df, rfm_df=rfm_df)
            st.session_state.last_ai_report = report
            st.success("🎉 Đã lập báo cáo chiến lược thành công!")
        except Exception as e:
            st.error(f"Lỗi khi tạo báo cáo: {e}")

# Hiển thị báo cáo nếu đã có sẵn trong trạng thái
if st.session_state.last_ai_report:
    st.markdown('<div style="background-color:rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1);">', unsafe_allow_html=True)
    st.markdown(st.session_state.last_ai_report)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Cho phép người dùng tải xuống báo cáo dưới dạng file Markdown
    st.download_button(
        label="📥 Tải báo cáo chiến lược (.md)",
        data=st.session_state.last_ai_report,
        file_name="Bao_Cao_Chien_Luoc_Kinh_Doanh.md",
        mime="text/markdown"
    )

# Kích hoạt Floating Chat trên trang này
render_floating_chat(df, rfm_df)
