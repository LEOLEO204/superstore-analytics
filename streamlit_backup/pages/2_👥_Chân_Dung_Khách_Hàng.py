import streamlit as st
import pandas as pd
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
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header
from utils.i18n import t

st.set_page_config(page_title="Phân tích Khách hàng", layout="wide")
import importlib
import utils.ui_components
importlib.reload(utils.ui_components)
from utils.ui_components import check_authentication
check_authentication("Chân Dung Khách Hàng")
inject_custom_css()
render_top_bar()

render_page_header("Chân Dung Khách Hàng", "Phân tích hành vi tiêu dùng và rủi ro rời bỏ của khách hàng", "👥", "pink")

def get_customer_data():
    df = load_and_clean_data()
    rfm_df = calculate_rfm(df)
    return df, rfm_df

df, rfm_df = get_customer_data()

# Đảm bảo an toàn tuyệt đối khi sử dụng bộ dữ liệu mới có cấu trúc khác biệt
if 'Segment' not in rfm_df.columns:
    rfm_df['Segment'] = 'All Customers'
if 'Customer Name' not in rfm_df.columns:
    rfm_df['Customer Name'] = 'Unknown Customer'

st.sidebar.header(t('customer_filter'))
segments = list(rfm_df['Segment'].unique())
selected_segments = st.sidebar.multiselect(
    t('select_segment'),
    options=segments,
    default=segments
)

valid_segments = [s for s in selected_segments if s in segments]
if not valid_segments:
    valid_segments = segments

filtered_rfm = rfm_df[rfm_df['Segment'].isin(valid_segments)]

# 1. Biểu đồ phân bổ Rủi ro Rời bỏ
st.subheader(t('churn_risk_distribution'))
col1, col2 = st.columns([1, 1])

with col1:
    risk_counts = filtered_rfm['Churn_Risk'].value_counts().reset_index()
    risk_counts.columns = ['Churn_Risk', 'Count']
    pie_chart = px.pie(risk_counts, values='Count', names='Churn_Risk', 
                       title=t('churn_rate_by_risk'),
                       color='Churn_Risk',
                       color_discrete_map={
                           'An toàn (Active)': 'green',
                           'Cần chú ý (Needs Attention)': 'orange',
                           'Nguy cơ cao (High Risk)': 'red',
                           'Đã rời bỏ (Churned)': 'gray'
                       })
    st.plotly_chart(pie_chart, use_container_width=True)

with col2:
    segment_risk = filtered_rfm.groupby(['Segment', 'Churn_Risk']).size().reset_index(name='Count')
    bar_chart = px.bar(segment_risk, x='Segment', y='Count', color='Churn_Risk',
                       title=t('churn_risk_by_segment'),
                       barmode='stack',
                       color_discrete_map={
                           'An toàn (Active)': 'green',
                           'Cần chú ý (Needs Attention)': 'orange',
                           'Nguy cơ cao (High Risk)': 'red',
                           'Đã rời bỏ (Churned)': 'gray'
                       })
    st.plotly_chart(bar_chart, use_container_width=True)

st.divider()

# 2. Danh sách Khách hàng nguy cơ cao
st.subheader(t('high_risk_list'))
st.markdown(t('high_risk_desc'))
high_risk_customers = filtered_rfm[filtered_rfm['Churn_Risk'] == 'Nguy cơ cao (High Risk)']
high_risk_display = high_risk_customers[['Customer ID', 'Customer Name', 'Segment', 'Recency', 'Frequency', 'Monetary']].sort_values(by='Monetary', ascending=False)
st.dataframe(high_risk_display, use_container_width=True)

# Nút tải xuống dữ liệu Khách hàng nguy cơ cao
csv_high_risk = high_risk_display.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Tải danh sách khách hàng nguy cơ cao (CSV)",
    data=csv_high_risk,
    file_name='high_risk_customers.csv',
    mime='text/csv',
    key='download_high_risk'
)

st.divider()

# 3. Phân tích Cohort & Tỷ lệ giữ chân khách hàng (Cohort Analysis)
st.subheader("📊 Phân Tích Cohort & Tỷ Lệ Giữ Chân (Cohort Retention Analysis)")

with st.expander("📖 Hướng dẫn phân tích Cohort là gì?"):
    st.markdown("""
    **Cohort Analysis (Phân tích Cohort)** là một kỹ thuật phân tích sâu trong Khoa học Dữ liệu, giúp chia khách hàng thành từng nhóm (Cohort) dựa trên thời điểm họ thực hiện giao dịch đầu tiên. 
    - **Trục Tung (Y - Cohort Month):** Biểu thị tháng khách hàng bắt đầu mua hàng lần đầu tiên.
    - **Trục Hoành (X - Cohort Index):** Biểu thị số tháng sau lần mua đầu tiên (Tháng 0 là tháng mua đầu, Tháng 1 là tháng tiếp theo...).
    - **Tỷ lệ giữ chân (Retention Rate %):** Tỷ lệ phần trăm khách hàng quay lại mua sắm. Màu sắc càng đậm nghĩa là tỷ lệ giữ chân khách hàng càng cao, chứng tỏ hoạt động chăm sóc khách hàng và chất lượng sản phẩm rất tốt.
    """)

try:
    from utils.data_processor import detect_standard_columns
    col_map = detect_standard_columns(df)
    cust_col = col_map['Customer ID']
    date_col = col_map['Order Date']
    
    if cust_col and date_col and cust_col in df.columns and date_col in df.columns:
        # Chuẩn bị dữ liệu Cohort
        cohort_df = df[[cust_col, date_col]].copy()
        cohort_df['Order Month'] = cohort_df[date_col].dt.to_period('M')
        
        # Tìm tháng đầu tiên mua hàng của mỗi khách hàng
        cohort_df['Cohort Month'] = cohort_df.groupby(cust_col)[date_col].transform('min').dt.to_period('M')
        
        # Group dữ liệu tính số lượng khách hàng độc nhất
        cohort_group = cohort_df.groupby(['Cohort Month', 'Order Month']).agg(n_customers=(cust_col, 'nunique')).reset_index()
        
        # Tính Cohort Index (Tháng hoạt động thứ n)
        cohort_group['Cohort Index'] = (cohort_group['Order Month'] - cohort_group['Cohort Month']).apply(lambda x: x.n)
        
        # Pivot dữ liệu thành dạng bảng rộng
        cohort_pivot = cohort_group.pivot(index='Cohort Month', columns='Cohort Index', values='n_customers')
        
        # Tính tỷ lệ giữ chân (%)
        cohort_size = cohort_pivot.iloc[:, 0]
        retention = cohort_pivot.divide(cohort_size, axis=0) * 100
        
        # Định dạng index và cột hiển thị
        retention.index = retention.index.astype(str)
        
        # Vẽ Heatmap sử dụng Plotly
        fig_cohort = px.imshow(
            retention,
            text_auto=".1f",
            color_continuous_scale='Blues',
            labels=dict(x="Tháng hoạt động (Cohort Index)", y="Nhóm Khách Hàng (Cohort Month)", color="Tỷ lệ giữ chân (%)"),
            title="Bản đồ nhiệt giữ chân khách hàng lũy kế (%)"
        )
        
        fig_cohort.update_layout(
            xaxis=dict(tickmode='linear', tick0=0, dtick=1),
            yaxis=dict(type='category'),
            height=500
        )
        
        st.plotly_chart(fig_cohort, use_container_width=True)
    else:
        st.info("Dataset hiện tại không có đủ thông tin Customer ID và Order Date để thực hiện phân tích Cohort.")
except Exception as e:
    st.error(f"Lỗi khi tính toán Cohort: {e}")

# Inject Floating Chat
render_floating_chat(df, rfm_df)
