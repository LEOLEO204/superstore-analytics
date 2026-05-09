# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_processor import load_and_clean_data, calculate_rfm
from utils.chat_widget import render_floating_chat
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header
from utils.i18n import t

st.set_page_config(page_title="Dự báo Tương lai", layout="wide", page_icon="🔮")
inject_custom_css()
render_top_bar()

render_page_header("Dự Báo Tương Lai", "Phân tích Dự báo (Predictive Analytics) sử dụng thuật toán hồi quy kinh tế lượng kết hợp điều chỉnh chu kỳ", "🔮", "purple")

df = load_and_clean_data()
rfm_df = calculate_rfm(df)

# Chuẩn bị chuỗi thời gian doanh số thực tế hàng tháng
df['Year_Month_DT'] = pd.to_datetime(df['Order Date']).dt.to_period('M')
monthly_data = df.groupby('Year_Month_DT')[['Sales', 'Profit']].sum().reset_index()
monthly_data['Year_Month_DT'] = monthly_data['Year_Month_DT'].astype(str)
monthly_data = monthly_data.sort_values('Year_Month_DT').reset_index(drop=True)

if len(monthly_data) < 12:
    st.warning("Dữ liệu chuỗi thời gian quá ngắn để thực hiện dự báo chính xác (yêu cầu tối thiểu 12 tháng).")
else:
    # 1. Các thông số mô hình dự báo
    st.sidebar.markdown("### ⚙️ Thông số Mô hình")
    forecast_months = st.sidebar.slider("Số tháng dự báo tương lai:", min_value=3, max_value=24, value=12)
    confidence_level = st.sidebar.selectbox("Độ tin cậy (Confidence Interval):", options=[0.90, 0.95, 0.99], index=1)
    
    # 2. Xãy dựng thuật toán dự báo (Linear Regression + Seasonal Multiplier)
    # Lấy x là số thứ tự tháng (0, 1, 2...)
    x = np.arange(len(monthly_data))
    y_sales = monthly_data['Sales'].values
    y_profit = monthly_data['Profit'].values
    
    # Khớp đường xu hướng tuyến tính (y = ax + b)
    slope_sales, intercept_sales = np.polyfit(x, y_sales, 1)
    slope_profit, intercept_profit = np.polyfit(x, y_profit, 1)
    
    # Tính hệ số chu kỳ hàng tháng (Monthly Seasonal Index)
    # Giả định chu kỳ 12 tháng
    monthly_data['Month_Num'] = pd.to_datetime(monthly_data['Year_Month_DT']).dt.month
    avg_sales_by_month = monthly_data.groupby('Month_Num')['Sales'].mean()
    overall_mean_sales = monthly_data['Sales'].mean()
    seasonal_indices = (avg_sales_by_month / overall_mean_sales).to_dict()
    
    # Tạo chỉ số thời gian cho tương lai
    future_x = np.arange(len(monthly_data), len(monthly_data) + forecast_months)
    last_date = pd.to_datetime(monthly_data['Year_Month_DT'].iloc[-1] + "-01")
    future_dates = [ (last_date + pd.DateOffset(months=i)).strftime('%Y-%m') for i in range(1, forecast_months + 1) ]
    
    # Tính toán dự báo có chu kỳ
    forecast_sales = []
    forecast_profit = []
    lower_bound_sales = []
    upper_bound_sales = []
    
    # Sai số tiêu chuẩn của ước lượng (Standard Error of Estimate)
    std_err_sales = np.std(y_sales - (slope_sales * x + intercept_sales))
    z_score = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}[confidence_level]
    
    for i, fx in enumerate(future_x):
        # Xu hướng tuyến tính gốc
        trend_s = slope_sales * fx + intercept_sales
        trend_p = slope_profit * fx + intercept_profit
        
        # Áp dụng nhân tử chu kỳ tương ứng với tháng đó
        f_month = pd.to_datetime(future_dates[i] + "-01").month
        s_index = seasonal_indices.get(f_month, 1.0)
        
        pred_s = max(100.0, trend_s * s_index)
        pred_p = trend_p * s_index
        
        forecast_sales.append(pred_s)
        forecast_profit.append(pred_p)
        
        # Tính khoảng tin cậy
        lower_bound_sales.append(max(0.0, pred_s - z_score * std_err_sales))
        upper_bound_sales.append(pred_s + z_score * std_err_sales)
        
    # Tạo DataFrame dự báo
    forecast_df = pd.DataFrame({
        'Year-Month': future_dates,
        'Sales': forecast_sales,
        'Profit': forecast_profit,
        'Lower_Bound': lower_bound_sales,
        'Upper_Bound': upper_bound_sales,
        'Type': 'Dự báo (Forecast)'
    })
    
    actual_df = pd.DataFrame({
        'Year-Month': monthly_data['Year_Month_DT'],
        'Sales': monthly_data['Sales'],
        'Profit': monthly_data['Profit'],
        'Lower_Bound': monthly_data['Sales'],
        'Upper_Bound': monthly_data['Sales'],
        'Type': 'Thực tế (Actual)'
    })
    
    combined_df = pd.concat([actual_df, forecast_df]).reset_index(drop=True)
    
    # 3. Thẻ KPI Dự báo Kinh doanh
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #4A148C;">
            <div class="metric-label">Dự báo Doanh số Tháng tới</div>
            <div class="metric-value">${forecast_sales[0]:,.2f}</div>
            <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Tháng khởi đầu: {future_dates[0]}</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #00ACC1;">
            <div class="metric-label">Tổng Doanh số Dự báo ({forecast_months}T)</div>
            <div class="metric-value">${sum(forecast_sales):,.2f}</div>
            <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Giai đoạn dự báo tương lai</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #43A047;">
            <div class="metric-label">Lợi nhuận Dự báo ({forecast_months}T)</div>
            <div class="metric-value">${sum(forecast_profit):,.2f}</div>
            <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Biên lợi nhuận dự tính: {(sum(forecast_profit)/sum(forecast_sales))*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        growth_rate = (slope_sales / overall_mean_sales) * 100
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #ffd400;">
            <div class="metric-label">Tốc độ Tăng trưởng xu hướng</div>
            <div class="metric-value">{"+" if growth_rate >= 0 else ""}{growth_rate:.2f}% / tháng</div>
            <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Xu hướng tuyến tính lịch sử</div>
        </div>
        """, unsafe_allow_html=True)
        
    # 4. Vẽ biểu đồ chuỗi thời gian dự báo
    st.markdown("### 📈 Biểu đồ trực quan xu hướng và Dự báo Doanh số tương lai")
    
    fig = go.Figure()
    
    # Đường thực tế
    fig.add_trace(go.Scatter(
        x=actual_df['Year-Month'],
        y=actual_df['Sales'],
        mode='lines+markers',
        name='Doanh số Thực tế',
        line=dict(color='#1E88E5', width=3),
        marker=dict(size=6)
    ))
    
    # Đường dự báo
    fig.add_trace(go.Scatter(
        x=forecast_df['Year-Month'],
        y=forecast_df['Sales'],
        mode='lines+markers',
        name='Doanh số Dự báo',
        line=dict(color='#FF8F00', width=3, dash='dash'),
        marker=dict(size=6)
    ))
    
    # Vùng tin cậy
    fig.add_trace(go.Scatter(
        x=pd.concat([forecast_df['Year-Month'], forecast_df['Year-Month'].iloc[::-1]]),
        y=pd.concat([forecast_df['Upper_Bound'], forecast_df['Lower_Bound'].iloc[::-1]]),
        fill='toself',
        fillcolor='rgba(255, 143, 0, 0.15)',
        line=dict(color='rgba(255,143,0,0)'),
        hoverinfo="skip",
        showlegend=True,
        name=f'Khoảng tin cậy {int(confidence_level*100)}%'
    ))
    
    fig.update_layout(
        title=f"Mô hình Dự báo Doanh số có chu kỳ ({forecast_months} tháng tiếp theo)",
        xaxis_title="Thời gian (Năm-Tháng)",
        yaxis_title="Doanh số (USD)",
        template="plotly_white",
        height=500,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 5. Bảng dữ liệu chi tiết
    st.divider()
    col_t1, col_t2 = st.columns([1, 1])
    with col_t1:
        st.markdown("##### 📅 Bảng chi tiết kết quả dự báo 12 tháng tiếp theo")
        display_forecast = forecast_df[['Year-Month', 'Sales', 'Profit', 'Lower_Bound', 'Upper_Bound']].copy()
        display_forecast.columns = ['Năm-Tháng', 'Doanh số dự báo', 'Lợi nhuận dự báo', 'Cận dưới (95%)', 'Cận trên (95%)']
        st.dataframe(display_forecast.style.format({
            'Doanh số dự báo': '${:,.2f}',
            'Lợi nhuận dự báo': '${:,.2f}',
            'Cận dưới (95%)': '${:,.2f}',
            'Cận trên (95%)': '${:,.2f}'
        }), use_container_width=True)
        
    with col_t2:
        st.markdown("##### 🔬 Diễn giải Học thuật & Khuyến nghị Chiến lược (DATN)")
        st.markdown("""
        * **Độ tin cậy mô hình:** Sử dụng phương pháp phân tích chuỗi thời gian kết hợp hồi quy bình phương tối thiểu (OLS) điều chỉnh chu kỳ hàng năm. Mô hình tự động nhận dạng các tháng cao điểm mua sắm (thường là quý 4 hàng năm) để nhân hệ số chu kỳ thực nghiệm.
        * **Nhận định xu hướng:** Tốc độ tăng trưởng xu hướng đạt giá trị dương ổn định chỉ ra tệp khách hàng đang mở rộng đều đặn ngoài thực tế.
        * **Khuyến nghị hành động:** Doanh nghiệp nên chuẩn bị tăng lượng hàng tồn kho dự trữ tối thiểu 15% trước các tháng có hệ số chu kỳ lớn (như tháng 11 và tháng 12) để tránh tình trạng đứt gãy chuỗi cung ứng khi sức mua bùng nổ ngoài dự tính.
        """)

# Inject Floating Chat
render_floating_chat(df, rfm_df)
