# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import sys
# Thêm thư mục gốc vào sys.path để có thể import module utils
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "..", "..")) if "pages" in current_dir else os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.data_processor import load_and_clean_data, calculate_rfm
from utils.chat_widget import render_floating_chat
import importlib
import utils.ui_components
importlib.reload(utils.ui_components)
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header
from utils.i18n import t

st.set_page_config(page_title="Phân khúc Khách hàng", layout="wide", page_icon="🎯")
inject_custom_css()
render_top_bar()

# CSS bổ sung cho trang RFM
st.markdown("""
<style>
    .strategy-box {
        background-color: #f1f8e9;
        border-left: 5px solid #689f38;
        padding: 20px;
        border-radius: 8px;
        margin-top: 15px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

render_page_header("Phân Khúc Khách Hàng", "Phân tích Đề xuất (Prescriptive Analytics) thiết kế ma trận chiến lược tiếp thị tự động", "🎯", "blue")

df = load_and_clean_data()
rfm_df = calculate_rfm(df)

# Phân nhóm RFM nâng cao chi tiết dựa trên điểm số phân vị
# Chia điểm R, F, M từ 1 đến 4
rfm_df['R_Score'] = pd.qcut(rfm_df['Recency'].rank(method='first'), q=4, labels=[4, 3, 2, 1]).astype(int) # Gần nhất nhận điểm cao nhất
rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method='first'), q=4, labels=[1, 2, 3, 4]).astype(int) # Tần suất lớn nhận điểm cao nhất
rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'].rank(method='first'), q=4, labels=[1, 2, 3, 4]).astype(int) # Tiêu tiền lớn nhận điểm cao nhất

# Định nghĩa Phân khúc chiến lược RFM
def assign_rfm_segment(row):
    r, f, m = row['R_Score'], row['F_Score'], row['M_Score']
    score = r + f + m
    
    if r >= 3 and f >= 3 and m >= 3:
        return 'Champions (Khách hàng Tinh hoa)'
    elif r >= 2 and f >= 3 and m >= 2:
        return 'Loyal Customers (Trung thành)'
    elif r >= 3 and f <= 2:
        return 'Promising (Tiềm năng mới)'
    elif r <= 2 and f >= 2:
        return 'At Risk (Cần chú ý giữ chân)'
    else:
        return 'Hibernating (Khách ngủ đông / Đã mất)'

rfm_df['RFM_Segment'] = rfm_df.apply(assign_rfm_segment, axis=1)

# 1. Thẻ chỉ số tổng quan các phân khúc
st.markdown("### 📊 Bản đồ phân bố số lượng khách hàng theo Phân khúc RFM")
segment_counts = rfm_df['RFM_Segment'].value_counts().reset_index()
segment_counts.columns = ['Phân khúc RFM', 'Số lượng khách hàng']

col_ch1, col_ch2 = st.columns([1, 1])
with col_ch1:
    fig_segment_pie = px.pie(
        segment_counts, 
        values='Số lượng khách hàng', 
        names='Phân khúc RFM',
        title="Tỷ trọng phân khúc khách hàng RFM thực nghiệm",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_segment_pie, use_container_width=True)
    
with col_ch2:
    fig_segment_bar = px.bar(
        segment_counts, 
        x='Phân khúc khách hàng' if 'Phân khúc khách hàng' in segment_counts.columns else segment_counts.columns[0], 
        y='Số lượng khách hàng',
        title="Số lượng khách hàng trên từng Phân khúc chiến lược",
        color='Phân khúc RFM',
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_segment_bar.update_layout(template="plotly_white", height=380, showlegend=False)
    st.plotly_chart(fig_segment_bar, use_container_width=True)

# 2. Không gian 3 chiều tương tác (3D RFM Scatter Plot)
st.divider()
st.markdown("### 🌌 Không gian Phân phối khách hàng 3 Chiều (3D RFM Scatter Plot)")
st.markdown("Mỗi điểm tròn đại diện cho một khách hàng được định vị chính xác trong không gian 3D tương tác. Giúp trực quan hóa mức độ phân tách rõ rệt giữa các phân khúc chiến lược.")

fig_3d = px.scatter_3d(
    rfm_df,
    x='Recency',
    y='Frequency',
    z='Monetary',
    color='RFM_Segment',
    opacity=0.8,
    title="Biểu đồ phân bố 3D khách hàng theo Recency (R) - Frequency (F) - Monetary (M)",
    labels={'Recency': 'R (Lần mua gần nhất - ngày)', 'Frequency': 'F (Tần suất - lần)', 'Monetary': 'M (Số tiền tiêu - USD)'},
    color_discrete_sequence=px.colors.qualitative.Vivid
)
fig_3d.update_layout(
    margin=dict(l=0, r=0, b=0, t=40),
    height=600,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
)
st.plotly_chart(fig_3d, use_container_width=True)

# 3. Trình tạo Chiến lược Tiếp thị tự động (Prescriptive Marketing Engine)
st.divider()
st.markdown("### 🎯 Công Cụ Đề Xuất Chiến Dịch Tiếp Thị (Prescriptive Marketing Engine)")
st.markdown("Chọn một phân khúc chiến lược để lọc danh sách khách hàng và tự động nhận đề xuất kịch bản tiếp thị từ hệ thống phân tích.")

selected_seg = st.selectbox(
    "Chọn phân khúc khách hàng mục tiêu để chạy kịch bản chiến dịch:",
    options=rfm_df['RFM_Segment'].unique()
)

seg_customers = rfm_df[rfm_df['RFM_Segment'] == selected_seg]

col_s1, col_s2 = st.columns([1, 1])
with col_s1:
    st.markdown(f"##### 📊 **Thống kê mô tả phân khúc: {selected_seg}**")
    sc_1, sc_2, sc_3 = st.columns(3)
    sc_1.metric("Số lượng khách", f"{len(seg_customers):,} người")
    sc_2.metric("Trung bình tiêu dùng", f"${seg_customers['Monetary'].mean():,.1f}")
    sc_3.metric("Tần suất trung bình", f"{seg_customers['Frequency'].mean():,.1f} lần")
    
    st.markdown(f"**Danh sách khách hàng đại diện thuộc nhóm:**")
    st.dataframe(seg_customers[['Customer ID', 'Customer Name', 'Recency', 'Frequency', 'Monetary']].head(100), use_container_width=True)

with col_s2:
    st.markdown("##### 💡 **Đề xuất chiến dịch Marketing cá nhân hóa tự động (Prescriptive Analytics)**")
    
    if "Tinh hoa" in selected_seg:
        st.markdown("""
        <div class="strategy-box">
            <strong>💎 Kịch bản chiến dịch: TRI ÂN ĐẲNG CẤP & ĐẶC QUYỀN VIP</strong><br><br>
            • <strong>Đối tượng:</strong> Nhóm khách hàng tinh hoa mang lại doanh thu và biên lợi nhuận lớn nhất cho doanh nghiệp.<br>
            • <strong>Hành động cụ thể:</strong>
              1. Gửi thư tri ân viết tay từ Giám đốc điều hành kèm quà tặng sinh nhật đặc biệt.<br>
              2. Kích hoạt tư cách thành viên Câu lạc bộ VIP với các đặc quyền truy cập sớm sản phẩm mới.<br>
              3. Cung cấp kênh chăm sóc khách hàng độc quyền 24/7.<br>
            • <strong>Thông điệp tiếp thị:</strong> <em>"Cảm ơn quý khách đã luôn đồng hành cùng sự thịnh vượng của chúng tôi. Dành riêng cho quý khách đặc quyền tiếp cận bộ sưu tập giới hạn mới nhất!"</em>
        </div>
        """, unsafe_allow_html=True)
    elif "Trung thành" in selected_seg:
        st.markdown("""
        <div class="strategy-box" style="border-left-color: #1976D2; background-color: #E3F2FD;">
            <strong>💙 Kịch bản chiến dịch: CHƯƠNG TRÌNH KHÁCH HÀNG THÂN THIẾT & UP-SELL</strong><br><br>
            • <strong>Đối tượng:</strong> Khách mua thường xuyên, tiêu dùng khá lớn và rất ổn định.<br>
            • <strong>Hành động cụ thể:</strong>
              1. Áp dụng chương trình tích điểm đổi quà tặng hoặc giảm giá trực tiếp cho đơn hàng tiếp theo.<br>
              2. Gợi ý các sản phẩm bổ trợ có giá trị cao hơn (Up-selling/Cross-selling) dựa trên lịch sử mua sắm.<br>
              3. Mời tham gia các khảo sát đóng góp ý kiến sản phẩm mới kèm quà tặng tri ân.<br>
            • <strong>Thông điệp tiếp thị:</strong> <em>"Nhân đôi điểm thưởng tích lũy dành riêng cho khách hàng thân thiết khi mua sắm danh mục sản phẩm cao cấp tuần này!"</em>
        </div>
        """, unsafe_allow_html=True)
    elif "Tiềm năng" in selected_seg:
        st.markdown("""
        <div class="strategy-box" style="border-left-color: #00ACC1; background-color: #E0F7FA;">
            <strong>🌱 Kịch bản chiến dịch: KÍCH THÍCH TẦN SUẤT & NUÔI DƯỠNG</strong><br><br>
            • <strong>Đối tượng:</strong> Khách mới mua gần đây nhưng số lượng đơn hàng và giá trị còn nhỏ.<br>
            • <strong>Hành động cụ thể:</strong>
              1. Gửi chuỗi email hướng dẫn sử dụng sản phẩm và gợi ý các sản phẩm liên quan bán chạy.<br>
              2. Tặng mã giảm giá thời hạn ngắn kích thích đơn hàng thứ hai (ví dụ: Giảm 10% trong vòng 14 ngày).<br>
              3. Tổ chức chương trình mua combo tiết kiệm để nâng cao chỉ số Monetary.<br>
            • <strong>Thông điệp tiếp thị:</strong> <em>"Chào mừng bạn đến với thế giới mua sắm thông minh! Quà tặng giảm giá 10% dành riêng cho đơn hàng tiếp theo của bạn đang chờ sẵn!"</em>
        </div>
        """, unsafe_allow_html=True)
    elif "giữ chân" in selected_seg:
        st.markdown("""
        <div class="strategy-box" style="border-left-color: #FF8F00; background-color: #FFF3E0;">
            <strong>⚠️ Kịch bản chiến dịch: KÍCH HOẠT LẠI KHẨN CẤP (RE-ACTIVATION)</strong><br><br>
            • <strong>Đối tượng:</strong> Khách hàng từng có sức mua tốt nhưng đã lâu chưa có giao dịch mới phát sinh.<br>
            • <strong>Hành động cụ thể:</strong>
              1. Gửi thông điệp mang tính nhắc nhớ cảm xúc ("Chúng tôi nhớ bạn").<br>
              2. Đưa ra các ưu đãi có giá trị đột phá cực lớn không thể chối từ dành riêng cho việc quay lại mua sắm.<br>
              3. Thực hiện cuộc gọi chăm sóc tìm hiểu lý do ngưng giao dịch (nếu là khách hàng doanh nghiệp).<br>
            • <strong>Thông điệp tiếp thị:</strong> <em>"Đã lâu không gặp! Chúng tôi đã chuẩn bị sẵn một phần quà giảm giá 20% đặc biệt trong tài khoản của bạn. Hãy quay lại khám phá những điều mới mẻ!"</em>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="strategy-box" style="border-left-color: #757575; background-color: #F5F5F5;">
            <strong>💤 Kịch bản chiến dịch: QUẢN LÝ CHI PHÍ & THĂM DÒ TỰ ĐỘNG</strong><br><br>
            • <strong>Đối tượng:</strong> Khách đã mua rất lâu trước đây, tần suất và giá trị giao dịch cực thấp, có khả năng cao đã mất hẳn.<br>
            • <strong>Hành động cụ thể:</strong>
              1. Hạn chế chi phí tiếp thị trả phí (như chạy quảng cáo trực tiếp, SMS brandname).<br>
              2. Chỉ áp dụng các kênh tiếp thị không tốn phí tự động (gửi email tự động hàng loạt dịp lễ lớn).<br>
              3. Tiến hành khảo sát thăm dò tự động lý do khách hàng rời đi để cải thiện sản phẩm.<br>
            • <strong>Thông điệp tiếp thị:</strong> <em>"Chúng tôi luôn nỗ lực cải thiện chất lượng dịch vụ mỗi ngày. Hãy dành 1 phút chia sẻ trải nghiệm sắm sửa cùng chúng tôi nhé!"</em>
        </div>
        """, unsafe_allow_html=True)

# Inject Floating Chat
render_floating_chat(df, rfm_df)
