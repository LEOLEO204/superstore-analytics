# Streamlit Watchdog Trigger Refresh: 2026-05-13 21:33
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_processor import load_and_clean_data, calculate_rfm
from utils.chat_widget import render_floating_chat
from utils.ui_components import inject_custom_css, render_top_bar
from utils.i18n import t

st.set_page_config(page_title="Dashboard Overview - Superstore", page_icon="📈", layout="wide")

import importlib
import utils.ui_components
importlib.reload(utils.ui_components)

from utils.ui_components import check_authentication
check_authentication("Trang Chủ")

inject_custom_css()
render_top_bar()

# 1. Tải Dữ Liệu Chuẩn SOP
with st.spinner("Đang tải dữ liệu hệ thống..."):
    df = load_and_clean_data()
    
# BỘ LỌC THỜI GIAN (Sidebar - SOP Step 8)
st.sidebar.header("📅 Bộ lọc thời gian")
years = sorted(list(df['Order Year'].unique()), reverse=True)
selected_years = st.sidebar.multiselect("Chọn Năm", options=years, default=years)

if not selected_years:
    selected_years = years

# Lọc Dữ liệu
df_filtered = df[df['Order Year'].isin(selected_years)]

# HEADER (SOP Step 8)
st.markdown("<h1 style='margin-bottom:0;'>📊 Dashboard Tổng Quan (Dashboard Overview)</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#666;'>Tóm tắt chỉ số hiệu suất kinh doanh hệ thống năm {', '.join(map(str, selected_years))}</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 2. THẺ KPI CHÍNH (SOP Bước 4 & 8) ---
st.markdown("### 🔑 Chỉ Số KPI Cốt Lõi")

total_sales = df_filtered['Sales'].sum()
total_profit = df_filtered['Profit'].sum()
profit_margin = (total_profit / total_sales * 100) if total_sales != 0 else 0
total_orders = df_filtered['Order ID'].nunique()
total_quantity = df_filtered['Quantity'].sum()
avg_discount = df_filtered['Discount'].mean() * 100

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #2E7D32;">
        <div class="metric-label">Tổng Doanh Thu</div>
        <div class="metric-value">${total_sales:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    profit_color = "#1565C0" if total_profit > 0 else "#C62828"
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid {profit_color};">
        <div class="metric-label">Tổng Lợi Nhuận</div>
        <div class="metric-value">${total_profit:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #FF8F00;">
        <div class="metric-label">Biên Lợi Nhuận (%)</div>
        <div class="metric-value">{profit_margin:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #6A1B9A;">
        <div class="metric-label">Tổng Đơn Hàng</div>
        <div class="metric-value">{total_orders:,}</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #00838F;">
        <div class="metric-label">Sản Phẩm Đã Bán</div>
        <div class="metric-value">{total_quantity:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 3. BIỂU ĐỒ XU HƯỚNG (SOP Step 8) ---
st.markdown("### 📈 Xu Hướng Doanh Thu & Lợi Nhuận (Sales & Profit Trend)")

# Nhóm theo tháng để vẽ trendline
monthly_data = df_filtered.groupby('Year-Month').agg({
    'Sales': 'sum',
    'Profit': 'sum'
}).reset_index().sort_values('Year-Month')

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(x=monthly_data['Year-Month'], y=monthly_data['Sales'], name='Doanh Thu',
                         line=dict(color='#1E88E5', width=3), mode='lines+markers'))
fig_trend.add_trace(go.Scatter(x=monthly_data['Year-Month'], y=monthly_data['Profit'], name='Lợi Nhuận',
                         line=dict(color='#E53935', width=2), fill='tozeroy', mode='lines'))

fig_trend.update_layout(
    title="Biến động Doanh số và Lợi nhuận qua các Tháng",
    xaxis_title="Tháng/Năm",
    yaxis_title="Giá trị ($)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    template="plotly_white",
    height=400,
    hovermode="x unified"
)
st.plotly_chart(fig_trend, use_container_width=True)

# --- 4. BIỂU ĐỒ PHÂN TÍCH NHÓM (SOP Step 8) ---
st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 📂 Doanh Thu theo Danh Mục (Sales by Category)")
    cat_sales = df_filtered.groupby('Category')['Sales'].sum().reset_index()
    fig_cat = px.pie(cat_sales, values='Sales', names='Category', hole=0.4,
                     color_discrete_sequence=px.colors.sequential.Tealgrn)
    fig_cat.update_layout(margin=dict(t=30, b=30))
    st.plotly_chart(fig_cat, use_container_width=True)

with col_right:
    st.markdown("#### 🗺️ Lợi Nhuận theo Khu Vực (Profit by Region)")
    reg_profit = df_filtered.groupby('Region')['Profit'].sum().sort_values(ascending=True).reset_index()
    fig_reg = px.bar(reg_profit, x='Profit', y='Region', orientation='h',
                     color='Profit', color_continuous_scale='RdYlGn')
    fig_reg.update_layout(yaxis_title=None, margin=dict(t=30, b=30))
    st.plotly_chart(fig_reg, use_container_width=True)

st.markdown("---")
col_b1, col_b2 = st.columns(2)

with col_b1:
    st.markdown("#### 🌍 Doanh Thu theo Thị Trường (Sales by Market)")
    market_sales = df_filtered.groupby('Market')['Sales'].sum().sort_values(ascending=False).reset_index()
    fig_mkt = px.bar(market_sales, x='Market', y='Sales', color='Market',
                     color_discrete_sequence=px.colors.qualitative.Safe)
    st.plotly_chart(fig_mkt, use_container_width=True)

with col_b2:
    st.markdown("#### 🏆 Top 10 Sản Phẩm Bán Chạy (Top 10 Products)")
    top_prod = df_filtered.groupby('Product Name')['Sales'].sum().nlargest(10).reset_index().sort_values('Sales')
    fig_prod = px.bar(top_prod, x='Sales', y='Product Name', orientation='h',
                      color_discrete_sequence=['#FFA000'])
    # Làm gọn nhãn tên sản phẩm
    fig_prod.update_layout(yaxis=dict(tickmode='array', tickvals=list(range(len(top_prod))),
                                     ticktext=[n[:30]+"..." if len(n)>30 else n for n in top_prod['Product Name']]))
    st.plotly_chart(fig_prod, use_container_width=True)

# --- 5. BẢNG DỮ LIỆU CHI TIẾT (SOP Step 8) ---
st.markdown("---")
st.markdown("### 📋 Bảng Dữ Liệu Chi Tiết (Data Table)")

search_term = st.text_input("🔍 Tìm kiếm nhanh (Tên khách hàng, Mã đơn hàng, Tên sản phẩm):")

# Logic tìm kiếm
display_df = df_filtered.copy()
if search_term:
    display_df = display_df[
        display_df['Customer Name'].str.contains(search_term, case=False, na=False) |
        display_df['Order ID'].str.contains(search_term, case=False, na=False) |
        display_df['Product Name'].str.contains(search_term, case=False, na=False)
    ]

cols_to_show = ['Order ID', 'Order Date', 'Customer Name', 'Region', 'Category', 'Product Name', 'Sales', 'Profit']
cols_to_show = [c for c in cols_to_show if c in display_df.columns]

st.dataframe(
    display_df[cols_to_show].sort_values('Order Date', ascending=False).head(500), 
    use_container_width=True,
    height=400
)
st.caption(f"Hiển thị tối đa 500 dòng dữ liệu mới nhất. Tổng số bản ghi tìm thấy: {len(display_df):,}")

# Floating Chat Assistant
rfm_df = calculate_rfm(df_filtered)
render_floating_chat(df_filtered, rfm_df)
