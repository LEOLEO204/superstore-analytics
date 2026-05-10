# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import os
from utils.data_processor import load_and_clean_data, flag_outliers, calculate_rfm
from utils.chat_widget import render_floating_chat
from utils.ui_components import inject_custom_css, render_top_bar
from utils.i18n import t

st.set_page_config(page_title="Superstore Analytics", page_icon="📈", layout="wide")

import importlib
import utils.ui_components
importlib.reload(utils.ui_components)

from utils.ui_components import check_authentication, inject_custom_css, render_top_bar
check_authentication("Trang Chủ")

inject_custom_css()
render_top_bar()

# 1. Tải và làm sạch dữ liệu
with st.spinner(t('loading_data')):
    df = load_and_clean_data()
    
# Layout Header (Modern Design)
st.markdown(f"<h1>{t('app_title')}</h1>", unsafe_allow_html=True)
st.markdown(f'<p class="subtitle">{t("app_subtitle")}</p>', unsafe_allow_html=True)

st.markdown("---")
st.markdown(f"### {t('kpi_overview')}")
exclude_outliers = st.checkbox(t('exclude_outliers'), value=False)
if exclude_outliers:
    df_calc = df[df['Is_Outlier'] == False]
else:
    df_calc = df
from utils.data_processor import detect_standard_columns

col_map = detect_standard_columns(df_calc)

sales_col = col_map['Sales']
profit_col = col_map['Profit']
cust_col = col_map['Customer ID']

total_revenue = df_calc[sales_col].sum() if sales_col else 0.0
total_profit = df_calc[profit_col].sum() if profit_col else 0.0
profit_margin = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0.0
total_customers = df_calc[cust_col].nunique() if cust_col else len(df_calc)

# Hiển thị Metrics bằng HTML/CSS tùy chỉnh để có viền màu (Colored borders)
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #ff4b4b;">
        <div class="metric-label">{t('total_revenue')}</div>
        <div class="metric-value">${total_revenue:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #00f2fe;">
        <div class="metric-label">{t('total_profit')}</div>
        <div class="metric-value">${total_profit:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #ffd400;">
        <div class="metric-label">{t('profit_margin')}</div>
        <div class="metric-value">{profit_margin:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #00E676;">
        <div class="metric-label">{t('total_customers')}</div>
        <div class="metric-value">{total_customers:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

st.info(t('data_preprocessed_info'))

# 2. Phân Tích Thống Kê Học & Phân Phối Xác Suất (Bias & Skewness)
st.markdown("---")
st.markdown("### 📊 Trung Tâm Phân Tích Thống Kê Học & Phân Phối Xác Suất (Bias & Skewness)")
st.markdown("""
Khảo sát tính chất phân phối xác suất của các chỉ số tài chính, xác định **Độ lệch (Skewness/Bias)**, **Độ nhọn (Kurtosis)**, và **Hệ số biến thiên (Dispersion)** để đánh giá bản chất phân bổ dữ liệu và các hành vi thị trường bất đối xứng.
""")

from utils.data_processor import calculate_distribution_stats
dist_stats = calculate_distribution_stats(df_calc)

if dist_stats:
    # Chọn cột phân tích
    selected_stat_label = st.radio(
        "Chọn chỉ số tài chính để khảo sát phân phối xác suất:",
        options=list(dist_stats.keys()),
        horizontal=True
    )
    
    selected_stat = dist_stats[selected_stat_label]
    col_name = selected_stat['col_name']
    
    # Hiển thị các chỉ số đo lường phân phối bằng metric cards
    sc1, sc2, sc3, sc4 = st.columns(4)
    
    with sc1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #1E88E5;">
            <div class="metric-label">Trung bình vs Trung vị</div>
            <div class="metric-value" style="font-size: 1.4rem;">${selected_stat['mean']:,.1f} / ${selected_stat['median']:,.1f}</div>
            <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Mất cân bằng: {abs(selected_stat['mean'] - selected_stat['median']) / selected_stat['mean'] * 100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    with sc2:
        skew_color = "#E53935" if abs(selected_stat['skew']) > 1.0 else ("#FB8C00" if abs(selected_stat['skew']) > 0.5 else "#43A047")
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {skew_color};">
            <div class="metric-label">Độ lệch (Skewness / Bias)</div>
            <div class="metric-value">{selected_stat['skew']:.3f}</div>
            <div style="font-size: 0.8rem; color: {skew_color}; margin-top: 5px; font-weight: bold;">
                { "Lệch Phải (Bias Dương)" if selected_stat['skew'] > 0 else "Lệch Trái (Bias Âm)" }
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with sc3:
        kurt_color = "#8E24AA" if selected_stat['kurt'] > 3.0 else "#5E35B1"
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {kurt_color};">
            <div class="metric-label">Độ nhọn (Kurtosis / Tails)</div>
            <div class="metric-value">{selected_stat['kurt']:.3f}</div>
            <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Đuôi phân phối dày (Outliers)</div>
        </div>
        """, unsafe_allow_html=True)
        
    with sc4:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #00ACC1;">
            <div class="metric-label">Hệ số Biến thiên (CV)</div>
            <div class="metric-value">{selected_stat['cv']:.3f}</div>
            <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Độ phân tán tương đối</div>
        </div>
        """, unsafe_allow_html=True)
        
    # Trực quan hóa Phân phối Xác suất bằng biểu đồ Histogram mật độ tích lũy cao cấp
    st.markdown(f"#### 📈 Biểu đồ Mật độ Phân phối Thực nghiệm của {selected_stat_label}")
    
    import plotly.express as px
    fig_dist = px.histogram(
        df_calc, 
        x=col_name,
        marginal="box", # Thêm biểu đồ hộp ở trên để mô tả trực quan các điểm outliers và phân vị
        histnorm="probability density", # Chuẩn hóa thành mật độ xác suất (Probability Density Function)
        title=f"Hàm Mật độ Phân phối Xác suất (Probability Density Function) & Phân vị của {selected_stat_label}",
        color_discrete_sequence=['#1E88E5'],
        opacity=0.75
    )
    
    fig_dist.update_layout(
        xaxis_title=selected_stat_label,
        yaxis_title="Mật độ Xác suất (Density)",
        template="plotly_white",
        height=450,
        margin=dict(l=40, r=40, t=50, b=40)
    )
    
    st.plotly_chart(fig_dist, use_container_width=True)
    
    # Thẻ Diễn giải Thống kê Chuyên sâu cho đồ án tốt nghiệp
    st.markdown('<div class="metric-card" style="border-left: 4px solid #00ACC1; padding: 20px; text-align: left; line-height: 1.6;">', unsafe_allow_html=True)
    st.markdown(f"##### 🔬 **Nhận định Bản chất Phân phối & Bias (Từ góc nhìn Toán thống kê):**")
    st.markdown(f"* 📐 **Độ lệch (Skewness):** `{selected_stat['skew']:.4f}` — **{selected_stat['bias_interpretation']}**")
    st.markdown(f"* 🔔 **Độ nhọn (Kurtosis):** `{selected_stat['kurt']:.4f}` — **{selected_stat['kurt_interpretation']}**")
    st.markdown(f"* ⚖️ **Khoảng cách Trung bình - Trung vị:** Giá trị trung bình (`${selected_stat['mean']:,.1f}`) lệch so với trung vị (`${selected_stat['median']:,.1f}`) chứng tỏ dữ liệu chịu sự chi phối mạnh mẽ từ các giá trị cực đoan, tạo ra độ bất đối xứng lớn trong phân phối thực tế.")
    st.markdown(f"* 📊 **Ý nghĩa Kinh tế học:** Phân phối lệch phải mạnh (Right-skewed) với Kurtosis cao là một đặc tính kinh điển của dữ liệu giao dịch thương mại (luật Pareto 80/20). Điều này chỉ ra rằng phần lớn doanh thu được tạo ra bởi các đơn hàng nhỏ lẻ ổn định, nhưng sự đột biến và tăng trưởng đột phá lại phụ thuộc vào một nhóm nhỏ các giao dịch có giá trị cực lớn.")
    st.markdown('</div>', unsafe_allow_html=True)

# 3. Kiểm Định Giả Thuyết & Thống Kê Suy Diễn (Hypothesis Testing)
st.markdown("---")
st.markdown("### 🔬 Trung Tâm Kiểm Định Giả Thuyết & Thống Kê Suy Diễn (Hypothesis Testing)")
st.markdown("""
Sử dụng các phương pháp thống kê suy diễn chuyên sâu để kiểm chứng các giả thuyết khoa học về sự khác biệt doanh thu, lợi nhuận giữa các phân khúc khách hàng, danh mục sản phẩm hoặc khu vực địa lý.
""")

import scipy.stats as stats

test_type = st.radio(
    "Chọn phương pháp kiểm định giả thuyết:",
    options=["Kiểm định t hai mẫu độc lập (Two-Sample t-Test)", "Phân tích phương sai một nhân tố (One-Way ANOVA)"],
    horizontal=True
)

# Lấy danh sách các cột phân loại và số liệu thích hợp
cat_candidates = ['Segment', 'Region', 'Category', 'Ship Mode']
cat_cols = [c for c in cat_candidates if c in df_calc.columns and df_calc[c].nunique() >= 2]
num_cols = []
if sales_col: num_cols.append(sales_col)
if profit_col: num_cols.append(profit_col)

if not cat_cols or not num_cols:
    st.warning("Không tìm thấy các cột phân loại và số liệu thích hợp để tiến hành kiểm định.")
else:
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        selected_num = st.selectbox("Chọn chỉ số khảo sát (Biến liên tục):", options=num_cols)
    with col_sel2:
        selected_cat = st.selectbox("Chọn biến phân loại (Biến phân loại):", options=cat_cols)
    
    if test_type == "Kiểm định t hai mẫu độc lập (Two-Sample t-Test)":
        unique_groups = sorted(df_calc[selected_cat].dropna().unique())
        if len(unique_groups) < 2:
            st.error("Trường phân loại cần có ít nhất 2 nhóm khác biệt.")
        else:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                g1 = st.selectbox("Chọn nhóm thứ nhất (Mẫu 1):", options=unique_groups, index=0)
            with col_g2:
                g2 = st.selectbox("Chọn nhóm thứ hai (Mẫu 2):", options=unique_groups, index=min(1, len(unique_groups)-1))
                
            if g1 == g2:
                st.warning("Vui lòng chọn hai nhóm khác nhau để thực hiện kiểm định.")
            else:
                series_g1 = df_calc[df_calc[selected_cat] == g1][selected_num].dropna()
                series_g2 = df_calc[df_calc[selected_cat] == g2][selected_num].dropna()
                
                # Chạy kiểm định Welch's t-test (không giả định phương sai bằng nhau)
                t_stat, p_val = stats.ttest_ind(series_g1, series_g2, equal_var=False)
                
                st.markdown(f"##### **🧬 Kết quả Kiểm định t-Test độc lập (Welch's t-Test)**")
                st.markdown(f"* **Giả thuyết Không ($H_0$):** Không có sự khác biệt có ý nghĩa thống kê về trung bình `{selected_num}` giữa `{g1}` và `{g2}` ($\mu_1 = \mu_2$).")
                st.markdown(f"* **Giả thuyết Đối ($H_1$):** Có sự khác biệt có ý nghĩa thống kê về trung bình `{selected_num}` giữa `{g1}` và `{g2}` ($\mu_1 \\neq \mu_2$).")
                
                # Hiển thị các chỉ số đo lường
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid #1E88E5;">
                        <div class="metric-label">Trung bình {g1}</div>
                        <div class="metric-value" style="font-size: 1.4rem;">${series_g1.mean():,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid #E53935;">
                        <div class="metric-label">Trung bình {g2}</div>
                        <div class="metric-value" style="font-size: 1.4rem;">${series_g2.mean():,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid #8E24AA;">
                        <div class="metric-label">Trị số t (t-stat)</div>
                        <div class="metric-value" style="font-size: 1.4rem;">{t_stat:.4f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with c4:
                    p_display = f"{p_val:.4f}" if p_val >= 0.0001 else f"{p_val:.2e}"
                    p_color = "#43A047" if p_val < 0.05 else "#FB8C00"
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid {p_color};">
                        <div class="metric-label">Trị số p (p-value)</div>
                        <div class="metric-value" style="font-size: 1.4rem; color: {p_color};">{p_display}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Biểu đồ so sánh phân vị và phân phối bằng Box plot
                fig_comp = px.box(
                    df_calc[df_calc[selected_cat].isin([g1, g2])],
                    x=selected_cat,
                    y=selected_num,
                    color=selected_cat,
                    points="outliers",
                    title=f"Biểu đồ Hộp so sánh phân phối {selected_num} giữa {g1} và {g2}",
                    color_discrete_sequence=['#1E88E5', '#E53935']
                )
                fig_comp.update_layout(template="plotly_white", height=380, margin=dict(l=40, r=40, t=50, b=40))
                st.plotly_chart(fig_comp, use_container_width=True)
                
                # Kết luận học thuật chuẩn đồ án tốt nghiệp
                st.markdown('<div class="metric-card" style="border-left: 4px solid #00ACC1; padding: 20px; text-align: left; line-height: 1.6;">', unsafe_allow_html=True)
                if p_val < 0.05:
                    st.markdown(f"##### **Kết luận thống kê (Mức ý nghĩa 5%):**")
                    st.markdown(f"👉 **BÁC BỎ GIẢ THUYẾT KHÔNG ($H_0$):** Trị số $p$ (`{p_display}`) < `0.05`. Đủ cơ sở thống kê để khẳng định sự khác biệt về mức độ `{selected_num}` trung bình giữa **{g1}** (Trung bình: `${series_g1.mean():,.2f}`) và **{g2}** (Trung bình: `${series_g2.mean():,.2f}`) **có ý nghĩa thống kê**.")
                    st.markdown(f"💡 **Ý nghĩa thực tế:** Hai phân khúc này có hành vi kinh doanh/khách hàng thực sự khác biệt rõ rệt chứ không phải do trùng hợp ngẫu nhiên. Doanh nghiệp cần xây dựng chính sách tiếp cận và tối ưu chi phí riêng biệt cho từng nhóm để tối đa hóa hiệu quả.")
                else:
                    st.markdown(f"##### **Kết luận thống kê (Mức ý nghĩa 5%):**")
                    st.markdown(f"👉 **CHƯA ĐỦ CƠ SỞ BÁC BỎ GIẢ THUYẾT KHÔNG ($H_0$):** Trị số $p$ (`{p_display}`) $\geq$ `0.05`. Chưa có đủ minh chứng thống kê cho thấy sự khác biệt về `{selected_num}` trung bình giữa **{g1}** và **{g2}**.")
                    st.markdown(f"💡 **Ý nghĩa thực tế:** Hành vi tài chính của hai phân khúc này tương tự nhau trong tập mẫu hiện tại. Doanh nghiệp có thể gộp nhóm hoặc áp dụng chung một chiến dịch quản trị và phân bổ nguồn lực để tiết kiệm chi phí vận hành.")
                st.markdown('</div>', unsafe_allow_html=True)
                
    elif test_type == "Phân tích phương sai một nhân tố (One-Way ANOVA)":
        unique_groups = sorted(df_calc[selected_cat].dropna().unique())
        if len(unique_groups) < 3:
            st.warning("Phương pháp ANOVA phù hợp hơn khi so sánh từ 3 nhóm trở lên. Nếu chỉ có 2 nhóm, vui lòng chuyển qua Kiểm định t-Test ở trên.")
            
        groups_data = [df_calc[df_calc[selected_cat] == g][selected_num].dropna() for g in unique_groups]
        
        # Thực hiện kiểm định ANOVA một nhân tố
        f_stat, p_val = stats.f_oneway(*groups_data)
        
        st.markdown(f"##### **🧬 Kết quả Kiểm định Phân tích Phương sai (One-Way ANOVA)**")
        st.markdown(f"* **Giả thuyết Không ($H_0$):** Giá trị trung bình `{selected_num}` của tất cả các nhóm thuộc danh mục `{selected_cat}` đều bằng nhau ($\mu_1 = \mu_2 = \dots = \mu_k$).")
        st.markdown(f"* **Giả thuyết Đối ($H_1$):** Có ít nhất một cặp nhóm có giá trị trung bình `{selected_num}` khác nhau có ý nghĩa thống kê.")
        
        # Hiển thị các chỉ số
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            st.markdown(f"""
            <div class="metric-card" style="border-left: 4px solid #1E88E5;">
                <div class="metric-label">Số lượng nhóm so sánh</div>
                <div class="metric-value" style="font-size: 1.4rem;">{len(unique_groups)} nhóm</div>
            </div>
            """, unsafe_allow_html=True)
        with ac2:
            st.markdown(f"""
            <div class="metric-card" style="border-left: 4px solid #8E24AA;">
                <div class="metric-label">Trị số F (F-stat)</div>
                <div class="metric-value" style="font-size: 1.4rem;">{f_stat:.4f}</div>
            </div>
            """, unsafe_allow_html=True)
        with ac3:
            p_display = f"{p_val:.4f}" if p_val >= 0.0001 else f"{p_val:.2e}"
            p_color = "#43A047" if p_val < 0.05 else "#FB8C00"
            st.markdown(f"""
            <div class="metric-card" style="border-left: 4px solid {p_color};">
                <div class="metric-label">Trị số p (p-value)</div>
                <div class="metric-value" style="font-size: 1.4rem; color: {p_color};">{p_display}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Biểu đồ Violin mật độ phân phối
        fig_anova = px.violin(
            df_calc,
            x=selected_cat,
            y=selected_num,
            color=selected_cat,
            box=True,
            points="outliers",
            title=f"Biểu đồ Violin so sánh phân phối mật độ {selected_num} giữa các nhóm của {selected_cat}"
        )
        fig_anova.update_layout(template="plotly_white", height=380, margin=dict(l=40, r=40, t=50, b=40))
        st.plotly_chart(fig_anova, use_container_width=True)
        
        # Kết luận học thuật ANOVA chuẩn
        st.markdown('<div class="metric-card" style="border-left: 4px solid #00ACC1; padding: 20px; text-align: left; line-height: 1.6;">', unsafe_allow_html=True)
        if p_val < 0.05:
            st.markdown(f"##### **Kết luận thống kê (Mức ý nghĩa 5%):**")
            st.markdown(f"👉 **BÁC BỎ GIẢ THUYẾT KHÔNG ($H_0$):** Trị số $p$ (`{p_display}`) < `0.05`. Đủ cơ sở thống kê khẳng định có sự khác biệt có ý nghĩa thống kê về mức trung bình `{selected_num}` giữa các nhóm thuộc danh mục **{selected_cat}**.")
            st.markdown(f"💡 **Ý nghĩa thực tế:** Ít nhất một nhóm có sức mua hoặc tạo lợi nhuận vượt trội (hoặc kém) rõ rệt so với các nhóm khác. Doanh nghiệp cần tiến hành kiểm tra sâu hậu kiểm (Post-hoc test) để tối ưu hóa nguồn lực vào phân nhóm tiềm năng nhất.")
        else:
            st.markdown(f"##### **Kết luận thống kê (Mức ý nghĩa 5%):**")
            st.markdown(f"👉 **CHƯA ĐỦ CƠ SỞ BÁC BỎ GIẢ THUYẾT KHÔNG ($H_0$):** Trị số $p$ (`{p_display}`) $\geq$ `0.05`. Chưa có đủ minh chứng thống kê cho thấy sự khác biệt về `{selected_num}` trung bình giữa các phân nhóm.")
            st.markdown(f"💡 **Ý nghĩa thực tế:** Doanh số và lợi nhuận được phân bổ đồng đều một cách ổn định, không chịu tác động đột phá từ việc phân loại nhóm hiện tại. Chiến lược phát triển diện rộng đồng đều là phù hợp.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# 4. Kỹ Nghệ Đặc Trưng (Feature Engineering Lab)
st.markdown("---")
st.markdown("### 🛠️ Trung Tâm Kỹ Nghệ Đặc Trưng (Feature Engineering Lab)")
st.markdown("""
Áp dụng các kỹ thuật tiền xử lý dữ liệu và tạo đặc trưng mới (Feature Engineering) nâng cao để chuẩn hóa dữ liệu, loại bỏ độ lệch (Skewness) phục vụ trực tiếp cho mô hình Học Máy (Machine Learning).
""")

import numpy as np

fe_method = st.radio(
    "Chọn phương pháp biến đổi đặc trưng:",
    options=[
        "Biến đổi Logarithm (Loại bỏ Skewness)", 
        "Phân nhóm Giá trị (Binning/Discretization)", 
        "Chuẩn hóa Thống kê (MinMax / Standard Scaling)",
        "Mã hóa biến danh mục (One-Hot / Label Encoding)"
    ],
    horizontal=True,
    key="app_fe_method_radio"
)

# Tạo một bản sao dữ liệu đã biến đổi riêng biệt cho app.py để tránh đè dữ liệu của Lab
if 'engineered_df_app' not in st.session_state:
    st.session_state['engineered_df_app'] = df_calc.copy()

app_eng_df = st.session_state['engineered_df_app']

if fe_method == "Biến đổi Logarithm (Loại bỏ Skewness)":
    st.markdown("##### **📈 Biến đổi Logarithm: $y = \\log(x + 1)$**")
    st.markdown("Giúp kéo dẹt các cột số có phân phối lệch phải mạnh (Right-skewed) với Kurtosis cao trở về phân phối chuẩn đối xứng (Bell curve).")
    
    log_col = st.selectbox("Chọn cột số để áp dụng biến đổi Log:", options=num_cols, key="app_log_col_select")
    
    if st.button("Áp dụng Biến đổi Log", key="app_apply_log_btn"):
        new_col_name = f"Log_{log_col}"
        app_eng_df[new_col_name] = np.log1p(app_eng_df[log_col])
        st.session_state['engineered_df_app'] = app_eng_df
        st.success(f"✅ Đã tạo thành công đặc trưng mới: `{new_col_name}`!")

    new_col_name = f"Log_{log_col}"
    if new_col_name in app_eng_df.columns:
        # Vẽ biểu đồ so sánh trước/sau
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            fig_before = px.histogram(app_eng_df, x=log_col, title=f"Trước biến đổi: {log_col} (Lệch mạnh)", color_discrete_sequence=['#E53935'])
            fig_before.update_layout(template="plotly_white", height=300)
            st.plotly_chart(fig_before, use_container_width=True)
        with col_b2:
            fig_after = px.histogram(app_eng_df, x=new_col_name, title=f"Sau biến đổi Log: {new_col_name} (Chuẩn đối xứng)", color_discrete_sequence=['#43A047'])
            fig_after.update_layout(template="plotly_white", height=300)
            st.plotly_chart(fig_after, use_container_width=True)

elif fe_method == "Phân nhóm Giá trị (Binning/Discretization)":
    st.markdown("##### **📊 Phân nhóm Giá trị: Liên tục $\\rightarrow$ Rời rạc**")
    st.markdown("Chia các giá trị số liên tục thành các khoảng/phân khúc logic (ví dụ: Thấp, Trung bình, Cao) để dễ dàng lập chiến lược marketing.")
    
    bin_col = st.selectbox("Chọn cột số để phân nhóm:", options=num_cols, key="app_bin_col_select")
    num_bins = st.slider("Số lượng nhóm muốn chia:", min_value=2, max_value=5, value=3, key="app_num_bins_slider")
    
    bin_labels = []
    st.markdown("Nhập nhãn cho từng nhóm (từ thấp đến cao):")
    col_lbls = st.columns(num_bins)
    for idx in range(num_bins):
        with col_lbls[idx]:
            default_label = ["Thấp (Low)", "Trung bình (Medium)", "Cao (High)", "Rất cao (Very High)", "Vượt trội"][idx]
            label_val = st.text_input(f"Nhãn nhóm {idx+1}:", value=default_label, key=f"app_label_bin_{idx}")
            bin_labels.append(label_val)
            
    if st.button("Áp dụng Phân nhóm", key="app_apply_binning_btn"):
        new_bin_col = f"Grouped_{bin_col}"
        try:
            app_eng_df[new_bin_col] = pd.qcut(app_eng_df[bin_col], q=num_bins, labels=bin_labels, duplicates='drop')
            st.session_state['engineered_df_app'] = app_eng_df
            st.success(f"✅ Đã tạo thành công phân nhóm mới: `{new_bin_col}`!")
        except Exception as e:
            st.error(f"Lỗi khi phân nhóm: {e}. Thử giảm số lượng nhóm.")

    new_bin_col = f"Grouped_{bin_col}"
    if new_bin_col in app_eng_df.columns:
        counts = app_eng_df[new_bin_col].value_counts().reset_index()
        counts.columns = ['Phân khúc nhóm', 'Tần suất']
        fig_bins = px.bar(
            counts,
            x='Phân khúc nhóm',
            y='Tần suất',
            title=f"Phân bố số lượng bản ghi trên các nhóm mới tạo của `{new_bin_col}`",
            color_discrete_sequence=['#00ACC1']
        )
        fig_bins.update_layout(template="plotly_white", height=350)
        st.plotly_chart(fig_bins, use_container_width=True)

elif fe_method == "Chuẩn hóa Thống kê (MinMax / Standard Scaling)":
    st.markdown("##### **📐 Chuẩn hóa Thống kê (Scaling)**")
    st.markdown("Điều chỉnh khoảng giá trị của biến số về một khoảng cố định (0-1) hoặc quy chuẩn hóa về phân phối có trung bình bằng 0 và độ lệch chuẩn bằng 1.")
    
    scale_col = st.selectbox("Chọn cột số để chuẩn hóa:", options=num_cols, key="app_scale_col_select")
    scale_type = st.selectbox("Chọn phương pháp chuẩn hóa:", options=["MinMax Scaling (Quy về khoảng 0 đến 1)", "Standard Scaling (Z-score: trung bình=0, std=1)"], key="app_scale_type_select")
    
    if st.button("Áp dụng Chuẩn hóa", key="app_apply_scaling_btn"):
        new_scale_col = f"Scaled_{scale_col}"
        series = app_eng_df[scale_col].dropna()
        if scale_type.startswith("MinMax"):
            app_eng_df[new_scale_col] = (app_eng_df[scale_col] - series.min()) / (series.max() - series.min())
        else:
            app_eng_df[new_scale_col] = (app_eng_df[scale_col] - series.mean()) / series.std()
        st.session_state['engineered_df_app'] = app_eng_df
        st.success(f"✅ Đã chuẩn hóa thành công! Tạo cột mới: `{new_scale_col}`")

    new_scale_col = f"Scaled_{scale_col}"
    if new_scale_col in app_eng_df.columns:
        st.markdown(f"**Thống kê mô tả cột `{new_scale_col}` sau chuẩn hóa:**")
        st.dataframe(app_eng_df[[scale_col, new_scale_col]].describe().T, use_container_width=True)

elif fe_method == "Mã hóa biến danh mục (One-Hot / Label Encoding)":
    st.markdown("##### **🔤 Mã hóa biến danh mục (Categorical Encoding)**")
    st.markdown("Chuyển đổi dữ liệu chuỗi/chữ thành định dạng số giúp các mô hình toán học và học máy có thể tính toán được.")
    
    enc_col = st.selectbox("Chọn cột danh mục để mã hóa:", options=cat_cols, key="app_enc_col_select")
    enc_type = st.selectbox("Chọn thuật toán mã hóa:", options=["Label Encoding (Mã hóa số thứ tự: 0, 1, 2...)", "One-Hot Encoding (Tạo các cột nhị phân 0/1)"], key="app_enc_type_select")
    
    if st.button("Áp dụng Mã hóa", key="app_apply_encoding_btn"):
        if enc_type.startswith("Label"):
            new_enc_col = f"Encoded_{enc_col}"
            app_eng_df[new_enc_col] = app_eng_df[enc_col].astype('category').cat.codes
            st.session_state['engineered_df_app'] = app_eng_df
            st.success(f"✅ Mã hóa thành công! Đã tạo cột số nguyên: `{new_enc_col}`")
        else:
            dummies = pd.get_dummies(app_eng_df[enc_col], prefix=f"OneHot_{enc_col}").astype(int)
            app_eng_df = pd.concat([app_eng_df, dummies], axis=1)
            st.session_state['engineered_df_app'] = app_eng_df
            st.success(f"✅ One-Hot Encoding thành công! Đã lồng ghép {dummies.shape[1]} cột nhị phân mới vào bảng dữ liệu.")

    st.markdown("**Bảng xem trước đặc trưng mã hóa hiện tại:**")
    preview_cols = [c for c in app_eng_df.columns if "Encoded" in c or "OneHot" in c]
    if preview_cols:
        st.dataframe(app_eng_df[[enc_col] + preview_cols[:10]].dropna().head(10), use_container_width=True)
    else:
        st.info("Chưa áp dụng mã hóa nào.")

st.markdown("---")
st.markdown("##### **💾 Xuất dữ liệu đã hoàn thiện Kỹ nghệ Đặc trưng (Export Dataset)**")
st.markdown("Tải xuống tệp dữ liệu đã được tiền xử lý và tích hợp toàn bộ các đặc trưng mới được tạo ra từ Lab.")

csv_data = app_eng_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Tải xuống Dataset đã hoàn thiện Feature Engineering (.csv)",
    data=csv_data,
    file_name="engineered_superstore_dataset.csv",
    mime="text/csv",
    use_container_width=True,
    key="app_download_engineered_csv_btn"
)

# Inject Floating Chat
rfm_df = calculate_rfm(df)
render_floating_chat(df, rfm_df)
