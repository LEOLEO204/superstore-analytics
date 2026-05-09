# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import os
from utils.data_processor import load_and_clean_data, calculate_rfm
from utils.chatbot_logic import get_ai_agent, ask_agent
from utils.chat_widget import render_floating_chat
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header
from utils.i18n import t

st.set_page_config(page_title="Trợ Lý AI", layout="wide")
from utils.ui_components import check_authentication
check_authentication("Trợ Lý AI")
inject_custom_css()
render_top_bar()

render_page_header("Trợ Lý AI", "Trung tâm lập báo cáo chiến lược tự động bằng AI", "🤖", "dark")

def get_data():
    df = load_and_clean_data()
    rfm_df = calculate_rfm(df)
    return df, rfm_df

df, rfm_df = get_data()

agent = get_ai_agent(df, rfm_df)

if agent:
    st.subheader(t('auto_strategy_proposal'))
    st.markdown(t('ai_report_desc'))
    if st.button(t('generate_report_btn')):
        with st.spinner(t('ai_generating')):
            # Tạo chuỗi tóm tắt dữ liệu thực tế cực kỳ chi tiết
            sales_col = 'Sales' if 'Sales' in df.columns else df.columns[0]
            profit_col = 'Profit' if 'Profit' in df.columns else df.columns[0]
            
            total_sales = df[sales_col].sum()
            total_profit = df[profit_col].sum()
            margin = (total_profit / total_sales) * 100 if total_sales > 0 else 0
            
            worst_region = "N/A"
            if 'Region' in df.columns:
                worst_region = df.groupby('Region')[profit_col].sum().idxmin()
                
            worst_category = "N/A"
            if 'Category' in df.columns:
                worst_category = df.groupby('Category')[profit_col].sum().idxmin()
                
            rfm_summary = ""
            if 'RFM_Segment' in rfm_df.columns:
                counts = rfm_df['RFM_Segment'].value_counts()
                rfm_summary = ", ".join([f"{k}: {v} khách" for k, v in counts.items()])
            elif 'Segment' in rfm_df.columns:
                counts = rfm_df['Segment'].value_counts()
                rfm_summary = ", ".join([f"{k}: {v} khách" for k, v in counts.items()])

            prompt = f"""
            Em hãy viết một báo cáo phân tích chiến lược kinh doanh chuyên sâu học thuật (dùng trong Đồ án tốt nghiệp ngành CNTT/Khoa học dữ liệu) dựa trên các số liệu thực tế được tính toán tự động từ hệ thống như sau:
            - Tổng Doanh số: ${total_sales:,.2f}
            - Tổng Lợi nhuận: ${total_profit:,.2f}
            - Biên lợi nhuận trung bình: {margin:.2f}%
            - Khu vực lỗ/kém hiệu quả nhất: {worst_region}
            - Danh mục sản phẩm lỗ/kém hiệu quả nhất: {worst_category}
            - Phân phối phân khúc khách hàng RFM hiện tại: {rfm_summary}
            
            YÊU CẦU BẮT BUỘC CHO ĐỒ ÁN TỐT NGHIỆP:
            Báo cáo phải được viết cực kỳ chi tiết, mang tính học thuật cao, có chiều sâu và phải lồng ghép khéo léo các phương pháp chuyên môn đã triển khai trong đồ án:
            1. Đánh giá kinh doanh: Phân tích sâu sắc ý nghĩa của con số Doanh số và Lợi nhuận trên, hiệu suất biên lợi nhuận thực tế đạt {margin:.2f}%.
            2. Vấn đề cốt lõi: Đưa ra nhận định sâu sắc về việc tại sao khu vực '{worst_region}' và danh mục '{worst_category}' lại kém hiệu quả. Hãy giải thích rằng việc hệ thống tích hợp bộ kiểm định giả thuyết thống kê Welch's t-Test và One-Way ANOVA đã giúp chứng minh sự khác biệt về doanh thu giữa các nhóm này có ý nghĩa thống kê thực sự (p-value < 0.05) chứ không phải do yếu tố ngẫu nhiên ngoài thực tế.
            3. Kỹ nghệ đặc trưng (Feature Engineering Lab): Phân tích tầm quan trọng của việc biến đổi dữ liệu (Log Transformation để chuẩn hóa phân phối lệch phải Skewness, Chuẩn hóa Scaling MinMax/Standard để đồng bộ thang đo, Phân nhóm Binning và Mã hóa One-Hot/Label Encoding) đã đóng vai trò cốt lõi thế nào trong việc làm sạch dữ liệu để huấn luyện thuật toán RFM và Hồi quy chuỗi thời gian.
            4. Đề xuất kịch bản chiến dịch Marketing cụ thể theo phân khúc RFM đã tính toán (tri ân nhóm VIP/Champions và tái kích hoạt nhóm At Risk).
            
            Hãy viết bằng tiếng Việt, trình bày Markdown lộng lẫy, sử dụng các ký hiệu biểu tượng chuyên nghiệp, phân chia các tiêu mục rõ ràng và có lập luận sắc bén của một chuyên gia Khoa học dữ liệu thực thụ.
            """
            try:
                report = ask_agent(agent, prompt)
                st.markdown(report)
            except Exception as e:
                st.error(f"{t('ai_error')} {e}")
else:
    st.warning(t('missing_api_key'))

# Kích hoạt Floating Chat trên trang này
render_floating_chat(df, rfm_df)
