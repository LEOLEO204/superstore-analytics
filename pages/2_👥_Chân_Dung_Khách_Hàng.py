import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_processor import load_and_clean_data, calculate_rfm
from utils.chat_widget import render_floating_chat
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header
from utils.i18n import t

st.set_page_config(page_title="Phân tích Khách hàng", layout="wide")
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

# Inject Floating Chat
render_floating_chat(df, rfm_df)
