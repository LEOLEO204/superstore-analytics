import streamlit as st
import pandas as pd
import os
from utils.data_processor import validate_and_clean_sop, initialize_database, load_and_clean_data, calculate_rfm
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header

st.set_page_config(page_title="Tải Lên Dữ Liệu - SOP", page_icon="📤", layout="wide")

import importlib
import utils.ui_components
importlib.reload(utils.ui_components)
import utils.chat_widget
importlib.reload(utils.chat_widget)
from utils.chat_widget import render_floating_chat
from utils.ui_components import check_authentication
check_authentication("Tải Lên Dữ Liệu")
inject_custom_css()
render_top_bar()

render_page_header("Tải Lên Dữ Liệu (Data Upload)", "Quy trình chuẩn hóa dữ liệu SOP: Tải file, Kiểm tra, Làm sạch & Lưu trữ", "📤", "green")

# Tải trước dữ liệu hệ thống hiện hành phục vụ cho Chatbot
df_system = load_and_clean_data()
rfm_df_system = calculate_rfm(df_system)
render_floating_chat(df_system, rfm_df_system)
st.sidebar.markdown("---")
st.sidebar.success("🤖 Trợ Lý AI: Đã kết nối thành công!")

st.info("""
**📋 Tiêu chuẩn file hợp lệ theo SOP:**
1. Định dạng: `.csv`
2. Dấu phân cách chuẩn: `;` (Hệ thống tự động fallback sang `,` nếu cần)
3. Cột bắt buộc: Phải chứa đầy đủ các cột nghiệp vụ (`Order ID`, `Sales`, `Profit`, `Order Date`...)
""")

# Khu vực Upload
uploaded_file = st.file_uploader("Kéo và thả file dữ liệu Superstore tại đây:", type=["csv"])

if uploaded_file is not None:
    st.markdown("---")
    st.subheader("🔍 Bước 1 & 2: Kiểm Tra & Đọc Cấu Trúc Dữ Liệu")
    
    try:
        # Đọc thử dữ liệu (SOP Bước 1)
        try:
            df_raw = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
        except Exception:
            uploaded_file.seek(0) # Reset stream read head
            df_raw = pd.read_csv(uploaded_file, sep=',', encoding='latin1')
            
        st.success(f"✅ Đọc file thành công! Phát hiện {df_raw.shape[0]:,} dòng và {df_raw.shape[1]} cột.")
        
        # Tiến hành validate theo SOP (SOP Bước 2 & 3)
        st.subheader("🧹 Bước 3: Thực Thi Quy Trình Làm Sạch Chuẩn SOP")
        
        with st.spinner("Đang chuẩn hóa kiểu dữ liệu, xử lý ngày tháng và tính toán KPI..."):
            try:
                df_cleaned = validate_and_clean_sop(df_raw)
                st.success("✅ Cấu trúc cột hợp lệ. Dữ liệu đã được làm sạch thành công!")
                
                # Bảng thống kê tóm tắt sau làm sạch (SOP Bước 7 - Kiểm thử)
                st.markdown("#### 📊 Bảng Kiểm Định Dữ Liệu Tóm Tắt:")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Dòng hợp lệ", f"{len(df_cleaned):,}")
                k2.metric("Tổng Doanh số", f"${df_cleaned['Sales'].sum():,.0f}")
                k3.metric("Số lượng Đơn hàng", f"{df_cleaned['Order ID'].nunique():,}")
                k4.metric("Khu vực phát hiện", f"{df_cleaned['Region'].nunique():,}")
                
                st.dataframe(df_cleaned.head(5), use_container_width=True)
                
                st.markdown("---")
                st.warning("⚠️ **Cảnh báo:** Bấm nút dưới đây sẽ GHI ĐÈ toàn bộ dữ liệu hiện hành của hệ thống Dashboard bằng dữ liệu mới vừa tải lên.")
                
                if st.button("🚀 XÁC NHẬN: Cập nhật hệ thống bằng Dataset này", type="primary", use_container_width=True):
                    with st.spinner("Đang ghi đè Database SQLite..."):
                        initialize_database(force_reload=True, uploaded_df=df_raw)
                        # Xóa cache Streamlit để force toàn bộ trang load data mới
                        st.cache_data.clear()
                        st.success("🎉 KÍCH HOẠT THÀNH CÔNG! Toàn bộ Dashboard đã được cập nhật theo dữ liệu mới. Vui lòng chuyển sang các tab Phân tích.")
                        st.balloons()
                        
            except ValueError as ve:
                st.error(f"❌ Lỗi Cấu Trúc File (SOP Step 9): {str(ve)}")
            except Exception as e:
                st.error(f"❌ Đã xảy ra lỗi ngoài ý muốn trong quá trình xử lý: {str(e)}")
                
    except Exception as e:
        st.error(f"❌ Không thể đọc file. Lỗi: {str(e)}")
        st.error("Thông báo: File không đúng định dạng CSV hoặc có lỗi mã hóa font.")

else:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("Chưa có file mới được chọn. Hệ thống hiện đang chạy trên dataset mặc định `superstore.db`.")

# Hoàn tất trang
