# pyrefly: ignore [missing-import]
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
from utils.data_processor import (
    load_and_clean_data, 
    calculate_rfm, 
    get_monthly_trends_sql, 
    get_category_revenue_sql, 
    get_geo_revenue_sql
)
from utils.chat_widget import render_floating_chat
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header
from utils.i18n import t

st.set_page_config(page_title="Phân tích Kinh doanh", layout="wide")
import importlib
import utils.ui_components
importlib.reload(utils.ui_components)
from utils.ui_components import check_authentication
check_authentication("Hiệu Suất Kinh Doanh")
inject_custom_css()
render_top_bar()

render_page_header("Hiệu Suất Kinh Doanh", "Phân tích xu hướng kinh doanh, doanh số, và địa lý toàn hệ thống", "📊", "blue")

def get_business_data():
    df = load_and_clean_data()
    rfm_df = calculate_rfm(df)
    return df, rfm_df

df, rfm_df = get_business_data()

# Đảm bảo an toàn tuyệt đối khi sử dụng bộ dữ liệu mới có cấu trúc khác biệt
if 'Order Year' not in df.columns:
    df['Order Year'] = 2026
if 'Region' not in df.columns:
    df['Region'] = 'All Regions'

st.sidebar.header(t('business_filter'))
years = sorted(list(df['Order Year'].unique()))
selected_years = st.sidebar.multiselect(t('select_year'), options=years, default=years)

regions = list(df['Region'].unique())
selected_regions = st.sidebar.multiselect(t('select_region'), options=regions, default=regions)

# --- Browser Session Validation Safeguard ---
# Đảm bảo nếu trình duyệt giữ cache của dữ liệu cũ (ví dụ: chọn năm 2026), 
# hệ thống tự động lọc và chuyển sang toàn bộ dữ liệu hợp lệ hiện tại
valid_years = [y for y in selected_years if y in years]
if not valid_years:
    valid_years = years

valid_regions = [r for r in selected_regions if r in regions]
if not valid_regions:
    valid_regions = regions

df_filtered = df[(df['Order Year'].isin(valid_years)) & (df['Region'].isin(valid_regions))]

st.markdown(f"### {t('time_analysis')}")
# Xu hướng Doanh thu và Lợi nhuận theo tháng (Sử dụng SQL tối ưu)
trend_df = get_monthly_trends_sql(valid_years, valid_regions)

fig_trend = px.line(trend_df, x='Year-Month', y=['Sales', 'Profit'], 
                    title=t('revenue_profit_by_month'),
                    markers=True,
                    labels={'value': 'USD', 'variable': 'Chỉ số'})
st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"### {t('category_analysis')}")
    # Biểu đồ Treemap cho Category và Sub-Category (Sử dụng SQL tối ưu)
    product_df = get_category_revenue_sql(valid_years, valid_regions)
    fig_tree = px.treemap(product_df, path=['Category', 'Sub-Category'], values='Sales',
                          title=t('revenue_by_category'),
                          color='Sales', color_continuous_scale='Blues')
    st.plotly_chart(fig_tree, use_container_width=True)

with col2:
    st.markdown(f"### {t('geo_analysis')}")
    # Doanh thu theo Market và Region (Sử dụng SQL tối ưu)
    geo_df = get_geo_revenue_sql(valid_years, valid_regions)
    fig_bar = px.bar(geo_df, x='Market', y='Sales', color='Region',
                     title=t('revenue_by_market'),
                     barmode='group')
    st.plotly_chart(fig_bar, use_container_width=True)

# --- Pareto & Profit Margin Analysis Section ---
st.divider()
st.subheader("💡 Phân Tích Pareto (80/20) & Biên Lợi Nhuận (Profit Margin)")

with st.expander("📖 Hướng dẫn Phân tích Pareto 80/20 & Biên Lợi Nhuận:"):
    st.markdown("""
    **1. Quy luật Pareto (80/20 Rule):**
    - Cho biết **20% khách hàng hàng đầu** đóng góp tới **80% doanh thu** của toàn doanh nghiệp. 
    - Giúp bộ phận Marketing và Chăm sóc Khách hàng tập trung nguồn lực tối ưu vào nhóm khách hàng mang lại giá trị cao nhất thay vì dàn trải chi phí.
    
    **2. Biên Lợi Nhuận (%) (Profit Margin):**
    - `Biên Lợi Nhuận (%) = (Tổng Lợi nhuận / Tổng Doanh số) * 100`.
    - Một vùng có Doanh số lớn chưa chắc đã hiệu quả nếu Biên Lợi Nhuận thấp do chi phí vận hành quá cao. Chúng tôi sử dụng sắc tím hoàng gia để đại diện cho dòng Lợi Nhuận bền vững của doanh nghiệp.
    """)

p_col1, p_col2 = st.columns(2)

with p_col1:
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # Tính toán Pareto theo Khách hàng
        pareto_df = df_filtered.groupby('Customer Name')['Sales'].sum().sort_values(ascending=False).reset_index()
        pareto_df['Cum_Sales'] = pareto_df['Sales'].cumsum()
        tot_sales = pareto_df['Sales'].sum()
        pareto_df['Cum_Percentage'] = (pareto_df['Cum_Sales'] / tot_sales) * 100
        
        top_30_pareto = pareto_df.head(30)
        
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pareto.add_trace(
            go.Bar(
                x=top_30_pareto['Customer Name'], 
                y=top_30_pareto['Sales'], 
                name="Doanh số cá nhân", 
                marker_color="#1f77b4" # Blue for Revenue
            ),
            secondary_y=False
        )
        fig_pareto.add_trace(
            go.Scatter(
                x=top_30_pareto['Customer Name'], 
                y=top_30_pareto['Cum_Percentage'], 
                name="Tỷ lệ lũy kế (%)", 
                line=dict(color="#9467bd", width=3), # Purple for Cumulative Pareto Line
                mode="lines+markers"
            ),
            secondary_y=True
        )
        
        fig_pareto.update_layout(
            title="Biểu đồ Pareto 80/20 theo Khách Hàng (Top 30)",
            xaxis_tickangle=-45,
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_pareto.update_yaxes(title_text="Doanh số ($)", secondary_y=False)
        fig_pareto.update_yaxes(title_text="Tỷ lệ tích lũy (%)", secondary_y=True)
        
        st.plotly_chart(fig_pareto, use_container_width=True)
    except Exception as e:
        st.error(f"Lỗi tính toán Pareto: {e}")

with p_col2:
    try:
        # Tính biên lợi nhuận theo Region
        margin_df = df_filtered.groupby('Region').agg(
            Total_Sales=('Sales', 'sum'),
            Total_Profit=('Profit', 'sum')
        ).reset_index()
        margin_df['Profit_Margin'] = (margin_df['Total_Profit'] / margin_df['Total_Sales']) * 100
        margin_df = margin_df.sort_values(by='Profit_Margin', ascending=True) # Ascending for nice horizontal bar
        
        fig_margin = px.bar(
            margin_df,
            y='Region',
            x='Profit_Margin',
            orientation='h',
            title='Biên Lợi Nhuận (%) Theo Khu Vực',
            labels={'Profit_Margin': 'Biên Lợi Nhuận (%)', 'Region': 'Khu vực'},
            color='Profit_Margin',
            color_continuous_scale='Purples' # Purple for Profit Consistency
        )
        
        fig_margin.update_layout(height=450)
        st.plotly_chart(fig_margin, use_container_width=True)
    except Exception as e:
        st.error(f"Lỗi tính toán Biên lợi nhuận: {e}")

# --- Interactive Data Drill-down Section ---
st.divider()
st.subheader("🔍 Kích hoạt Drill-down Chi tiết Đơn hàng theo Khu vực (Region Drill-down)")
st.markdown("Chọn một khu vực cụ thể để lọc nhanh danh sách đơn hàng chi tiết và xuất dữ liệu tác nghiệp.")

selected_drill_region = st.selectbox(
    "Chọn Khu vực (Region) cần drill-down phân tích:",
    options=["-- Hãy chọn một khu vực --"] + list(df_filtered['Region'].unique())
)

if selected_drill_region != "-- Hãy chọn một khu vực --":
    drill_df = df_filtered[df_filtered['Region'] == selected_drill_region]
    
    # Hiển thị các chỉ số nhanh của khu vực được drill-down
    d_col1, d_col2, d_col3 = st.columns(3)
    d_col1.metric("Tổng Doanh số Vùng", f"${drill_df['Sales'].sum():,.2f}")
    d_col2.metric("Tổng Lợi nhuận Vùng", f"${drill_df['Profit'].sum():,.2f}")
    d_col3.metric("Số lượng đơn hàng", f"{len(drill_df):,} giao dịch")
    
    # Hiển thị bảng chi tiết các cột tác nghiệp chính
    drill_display_cols = ['Order ID', 'Order Date', 'Customer Name', 'Segment', 'Category', 'Sub-Category', 'Product Name', 'Sales', 'Profit']
    drill_display_cols = [c for c in drill_display_cols if c in drill_df.columns]
    
    st.dataframe(drill_df[drill_display_cols].sort_values(by='Sales', ascending=False).head(200), use_container_width=True)
    
    # Nút download CSV
    csv_data = drill_df[drill_display_cols].to_csv(index=False, sep=';', encoding='utf-8')
    st.download_button(
        label=f"📥 Tải dữ liệu giao dịch chi tiết Vùng {selected_drill_region} (.csv)",
        data=csv_data,
        file_name=f"drill_down_orders_{selected_drill_region}.csv",
        mime="text/csv"
    )

# Inject Floating Chat
render_floating_chat(df, rfm_df)
