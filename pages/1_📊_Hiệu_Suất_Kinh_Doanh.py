import streamlit as st
import pandas as pd
import plotly.express as px
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
