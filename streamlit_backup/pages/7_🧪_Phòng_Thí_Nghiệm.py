# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import os
import plotly.express as px
import os
import sys
# Thêm thư mục gốc vào sys.path để có thể import module utils
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "..", "..")) if "pages" in current_dir else os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from utils.data_processor import detect_standard_columns, calculate_distribution_stats, load_and_clean_data, calculate_rfm
from utils.auto_analyst import get_automated_dataset_report
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header
from utils.i18n import t

st.set_page_config(page_title="Phòng Thí Nghiệm", page_icon="🧪", layout="wide")
import importlib
import utils.ui_components
importlib.reload(utils.ui_components)
import utils.chat_widget
importlib.reload(utils.chat_widget)
from utils.chat_widget import render_floating_chat
from utils.ui_components import check_authentication
check_authentication("Phòng Thí Nghiệm")
inject_custom_css()
render_top_bar()

# Tải trước dữ liệu hệ thống phục vụ Chatbot
df_system = load_and_clean_data()
rfm_df_system = calculate_rfm(df_system)
render_floating_chat(df_system, rfm_df_system)
st.sidebar.markdown("---")
st.sidebar.success("🤖 Trợ Lý AI: Đã sẵn sàng trong Lab!")

# CSS bổ sung cho thẻ chỉ số và tiêu đề
st.markdown("""
<style>
    .metric-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 15px;
        margin-bottom: 20px;
    }
    .stat-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #2a5298;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        transition: transform 0.2s ease;
    }
    .stat-box:hover {
        transform: translateY(-3px);
    }
    .stat-label {
        font-size: 0.85rem;
        color: #757575;
        font-weight: 600;
        text-transform: uppercase;
    }
    .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

render_page_header("Phòng Thí Nghiệm 📊 Phân Tích Marketing", "Nền tảng phân tích chuyên biệt các chỉ số chiến dịch, tối ưu hóa hiệu suất Quảng cáo & ROAS", "🎯", "blue")

# Quản lý file tải lên riêng biệt trên trang này
st.sidebar.markdown("### 📁 Nạp dữ liệu Lab")
uploaded_lab_file = st.sidebar.file_uploader("Nạp file Dataset mới (.csv)", type=["csv"], key="lab_uploader")

if uploaded_lab_file is not None:
    try:
        # Bổ sung tùy chọn nâng cao ngay bên dưới File Uploader
        st.sidebar.markdown("⚙️ **Cấu hình nạp tệp:**")
        skip_rows = st.sidebar.number_input("Bỏ qua số dòng đầu:", min_value=0, value=0)
        
        # Tự động nhận diện dấu phân cách
        sample = uploaded_lab_file.read(4096).decode('utf-8', errors='ignore')
        uploaded_lab_file.seek(0)
        separator = ';' if sample.count(';') > sample.count(',') else ','
        
        # Thử nhiều định dạng mã hóa khác nhau, ưu tiên utf-8-sig cho tiếng Việt Excel
        encodings_to_try = ['utf-8-sig', 'utf-8', 'latin1', 'windows-1252', 'utf-16']
        df_lab = None
        
        for enc in encodings_to_try:
            try:
                uploaded_lab_file.seek(0)
                df_lab = pd.read_csv(
                    uploaded_lab_file, 
                    sep=separator, 
                    encoding=enc, 
                    skiprows=skip_rows
                )
                break
            except Exception:
                continue
                
        if df_lab is None:
            st.sidebar.error("Không thể xác định bảng mã phù hợp cho tệp này.")
        else:
            # Smart Cleanup Tự động cho bảng tính bẩn:
            # 1. Bỏ các dòng hoàn toàn rỗng (thường do export thừa)
            df_lab = df_lab.dropna(how='all')
            # 2. Bỏ các cột Unnamed nếu chúng hoàn toàn rỗng
            unnamed_empty = [c for c in df_lab.columns if "Unnamed" in str(c) and df_lab[c].isnull().all()]
            if unnamed_empty:
                df_lab = df_lab.drop(columns=unnamed_empty)
                
            st.sidebar.markdown("🧹 **Công cụ dọn dẹp nhanh:**")
            enable_ffill = st.sidebar.checkbox("Điền đầy dòng trống (Forward Fill)", value=False, help="Hữu ích cho dữ liệu bị gộp ô ngày tháng.")
            if enable_ffill:
                df_lab = df_lab.ffill()

            enable_clean_currency = st.sidebar.checkbox("Làm sạch Tiền tệ (Số + Đ, $...)", value=False, help="Tự động xóa các chữ đ, $, dấu chấm thừa để đưa về số chuẩn.")
            if enable_clean_currency:
                def clean_numeric(val):
                    if pd.isna(val): return val
                    val_str = str(val).lower()
                    # Xóa các ký tự đặc biệt tiền tệ
                    for char in ['đ', '$', 'vnd', 'usd', '€']:
                        val_str = val_str.replace(char, '')
                    val_str = val_str.strip()
                    # Xử lý chuẩn Việt Nam: dấu chấm là phân tách hàng nghìn (ví dụ 58.000 đ -> 58000)
                    if '.' in val_str and ',' not in val_str:
                        # Giả định trường hợp 58.000 -> 58000
                        parts = val_str.split('.')
                        if len(parts[-1]) == 3:
                             val_str = val_str.replace('.', '')
                    # Xử lý dấu phẩy (ví dụ 2,768,000)
                    val_str = val_str.replace(',', '')
                    
                    try:
                        return float(val_str)
                    except Exception:
                        return val
                
                # Quét và thử convert các cột object có chứa chữ số
                for col in df_lab.columns:
                    if df_lab[col].dtype == 'object':
                        try:
                            # Chỉ xử lý nếu có ít nhất 1 ô chứa chữ số
                            if df_lab[col].dropna().astype(str).str.contains(r'\d', regex=True).any():
                                df_lab[col] = df_lab[col].apply(clean_numeric)
                        except Exception:
                            pass

            st.session_state['lab_df'] = df_lab
            # CẬP NHẬT ĐỒNG BỘ: Reset lại dataframe kỹ nghệ đặc trưng cho file mới
            st.session_state['engineered_df'] = df_lab.copy()
            
            st.sidebar.success(f"✅ Đã nạp ({enc})!")
    except Exception as ex:
        st.sidebar.error(f"Lỗi khi xử lý file: {ex}")

# Kiểm tra xem có dữ liệu trong Lab không
if 'lab_df' in st.session_state:
    df = st.session_state['lab_df']
    
    # 1. Tổng quan cấu trúc file
    st.markdown("### 📊 Tổng Quan Cấu Trúc Tập Dữ Liệu Tải Lên")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-box" style="border-left-color: #1E88E5;">
            <div class="stat-label">Tổng số dòng (Rows)</div>
            <div class="stat-value">{df.shape[0]:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-box" style="border-left-color: #43A047;">
            <div class="stat-label">Tổng số cột (Columns)</div>
            <div class="stat-value">{df.shape[1]:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        # Đảm bảo kiểm tra an toàn nếu shape = (0, 0)
        missing_count = df.isnull().sum().sum() if not df.empty else 0
        st.markdown(f"""
        <div class="stat-box" style="border-left-color: #E53935;">
            <div class="stat-label">Tổng ô khuyết thiếu (NaN)</div>
            <div class="stat-value">{missing_count:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        dup_count = df.duplicated().sum()
        st.markdown(f"""
        <div class="stat-box" style="border-left-color: #8E24AA;">
            <div class="stat-label">Dòng trùng lặp (Duplicates)</div>
            <div class="stat-value">{dup_count:,}</div>
        </div>
        """, unsafe_allow_html=True)
        
    # Xem trước bảng dữ liệu tải lên
    with st.expander("🔍 Xem bảng dữ liệu thô (Raw Data Preview)", expanded=False):
        st.dataframe(df.head(100), use_container_width=True)
        
    # 2. Nhận diện cột động Marketing Domain
    st.markdown("---")
    st.markdown("### 📈 Ánh Xạ Kênh Dữ Liệu Marketing (Dynamic Marketing Mapping)")

    def detect_marketing_cols(dframe):
        m_map = {'Cost': None, 'Clicks': None, 'Revenue': None, 'Conversions': None, 'Campaign': None, 'Impr': None}
        cols = [str(c) for c in dframe.columns]
        low_cols = [str(c).lower() for c in dframe.columns]
        
        pairs = [
            ('Cost', ['cost', 'spend', 'chi phí', 'ngân sách', 'budget']),
            ('Clicks', ['clicks', 'click', 'nhấp', 'truy cập', 'visits']),
            ('Revenue', ['revenue', 'sales', 'doanh thu', 'giá trị', 'value']),
            ('Conversions', ['conversions', 'leads', 'mua', 'chuyển đổi']),
            ('Campaign', ['campaign', 'chiến dịch', 'kênh', 'channel', 'ad set']),
            ('Impr', ['impressions', 'reach', 'hiển thị', 'tiếp cận'])
        ]
        
        for key, candidates in pairs:
            for i, c in enumerate(low_cols):
                if any(cand in c for cand in candidates):
                    m_map[key] = cols[i]
                    break
        
        # Fallback to any numeric columns if not found
        num_cols = list(dframe.select_dtypes(include=['number']).columns)
        if not m_map['Cost'] and len(num_cols) > 0: m_map['Cost'] = num_cols[0]
        if not m_map['Clicks'] and len(num_cols) > 1: m_map['Clicks'] = num_cols[1]
        
        return m_map

    m_auto = detect_marketing_cols(df)
    all_cols = list(df.columns)
    
    with st.expander("⚙️ Cấu hình Cột Dữ liệu Marketing (Điều chỉnh mục tiêu)", expanded=True):
        st.markdown("Để báo cáo marketing chính xác nhất, hãy kiểm tra và ánh xạ lại các chỉ số:")
        mc1, mc2, mc3 = st.columns(3)
        
        with mc1:
            sel_cost = st.selectbox("💰 Chi phí Quảng cáo (Cost/Spend):", options=["--Trống--"] + all_cols, 
                                  index=all_cols.index(m_auto['Cost'])+1 if m_auto['Cost'] in all_cols else 0)
            sel_impr = st.selectbox("👁️ Lượt Hiển thị (Impressions):", options=["--Trống--"] + all_cols, 
                                  index=all_cols.index(m_auto['Impr'])+1 if m_auto['Impr'] in all_cols else 0)
        with mc2:
            sel_click = st.selectbox("🖱️ Lượt Nhấp (Clicks):", options=["--Trống--"] + all_cols, 
                                   index=all_cols.index(m_auto['Clicks'])+1 if m_auto['Clicks'] in all_cols else 0)
            sel_conv = st.selectbox("🎯 Lượt Chuyển đổi (Conversions):", options=["--Trống--"] + all_cols, 
                                  index=all_cols.index(m_auto['Conversions'])+1 if m_auto['Conversions'] in all_cols else 0)
        with mc3:
            sel_rev = st.selectbox("💵 Doanh thu tạo ra (Revenue):", options=["--Trống--"] + all_cols, 
                                 index=all_cols.index(m_auto['Revenue'])+1 if m_auto['Revenue'] in all_cols else 0)
            sel_camp = st.selectbox("🏷️ Tên Chiến dịch/Kênh (Campaign):", options=["--Trống--"] + all_cols, 
                                  index=all_cols.index(m_auto['Campaign'])+1 if m_auto['Campaign'] in all_cols else 0)
            
    # Prepare Values for Dashboard
    c_col = None if sel_cost == "--Trống--" else sel_cost
    i_col = None if sel_impr == "--Trống--" else sel_impr
    cl_col = None if sel_click == "--Trống--" else sel_click
    v_col = None if sel_conv == "--Trống--" else sel_conv
    r_col = None if sel_rev == "--Trống--" else sel_rev
    camp_col = None if sel_camp == "--Trống--" else sel_camp
    
    # Calculate Totals safely
    total_cost = df[c_col].sum() if c_col and c_col in df.columns else 0
    total_clicks = df[cl_col].sum() if cl_col and cl_col in df.columns else 0
    total_impr = df[i_col].sum() if i_col and i_col in df.columns else 0
    total_conv = df[v_col].sum() if v_col and v_col in df.columns else 0
    total_rev = df[r_col].sum() if r_col and r_col in df.columns else 0
    
    st.markdown("### 📊 Bảng Chỉ Số Hiệu Suất Marketing (Marketing Scorecard)")
    
    # Row 1: Core Totals
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="stat-box" style="border-left-color: #E53935;">
            <div class="stat-label">TỔNG CHI PHÍ (COST)</div>
            <div class="stat-value">${total_cost:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat-box" style="border-left-color: #1E88E5;">
            <div class="stat-label">TỔNG CLICKS</div>
            <div class="stat-value">{total_clicks:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="stat-box" style="border-left-color: #43A047;">
            <div class="stat-label">DOANH THU (REVENUE)</div>
            <div class="stat-value">${total_rev:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="stat-box" style="border-left-color: #8E24AA;">
            <div class="stat-label">CHUYỂN ĐỔI (CONV)</div>
            <div class="stat-value">{total_conv:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
    # Row 2: Derived Metrics (CPC, CTR, ROAS, CPA)
    st.markdown("<br>", unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    
    cpc = total_cost / total_clicks if total_clicks > 0 else 0
    roas = total_rev / total_cost if total_cost > 0 else 0
    ctr = (total_clicks / total_impr) * 100 if total_impr > 0 else 0
    cpa = total_cost / total_conv if total_conv > 0 else 0
    
    with d1:
        st.metric("CPC (Giá mỗi Click)", f"${cpc:,.2f}")
    with d2:
        st.metric("ROAS (Tỷ suất doanh thu)", f"{roas:,.2f}x", delta=f"{roas-1:,.2f}x" if roas > 1 else None)
    with d3:
        st.metric("CTR (Tỉ lệ Click)", f"{ctr:.2f}%" if i_col else "N/A")
    with d4:
        st.metric("CPA (Giá mỗi Chuyển đổi)", f"${cpa:,.2f}" if v_col else "N/A")

    # Dynamic Marketing Charts Integration
    if camp_col and c_col:
        st.markdown("---")
        st.markdown(f"### 📊 Phân tích Hiệu Quả theo Chiến Dịch (`{camp_col}`)")
        
        camp_agg = df.groupby(camp_col).agg(
            Spend=(c_col, 'sum'),
            Revenue=(r_col, 'sum') if r_col else (c_col, 'count') # Fallback if no revenue
        ).reset_index()
        
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            # Spend Breakdown
            fig_pie = px.pie(camp_agg, values='Spend', names=camp_col, title="Phân bổ Ngân sách (%)", hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with chart_col2:
            # Cost vs Rev compare if revenue exists
            if r_col:
                camp_agg['ROAS'] = camp_agg['Revenue'] / camp_agg['Spend']
                fig_bar = px.bar(camp_agg.sort_values('ROAS', ascending=False), x=camp_col, y='ROAS', 
                                title="Chỉ số ROAS theo Chiến Dịch (Cao hơn là tốt hơn)", color='ROAS',
                                color_continuous_scale='Greens')
                fig_bar.add_hline(y=1, line_dash="dash", line_color="red", annotation_text="Điểm hòa vốn ROAS=1")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                # Just bar of spend
                fig_bar = px.bar(camp_agg.sort_values('Spend', ascending=False), x=camp_col, y='Spend', title="Tổng Chi tiêu mỗi Chiến Dịch", color='Spend')
                st.plotly_chart(fig_bar, use_container_width=True)

    # Tái sử dụng biến cũ để không làm hỏng AI report phía dưới
    sales_col = r_col
    profit_col = c_col # Trợ lý AI dùng cost thay cho profit mapping
    cust_col = camp_col
    
    # 3. Trung tâm chẩn đoán dữ liệu bằng AI Agent dành riêng cho Lab
    st.markdown("---")
    st.markdown("### 🤖 Trợ Lý AI: Trung Tâm Chẩn Đoán Dữ Liệu Tự Động")
    
    with st.expander("📊 Xem Báo cáo Phân tích Chẩn đoán Dữ liệu từ AI Agent", expanded=True):
        # Sử dụng session state để duy trì kết quả sau khi bấm nút, tránh việc biến mất khi tương tác các widget khác
        if 'ai_report_requested' not in st.session_state:
            st.session_state.ai_report_requested = False
            
        if not st.session_state.ai_report_requested:
            st.markdown("💡 **Gợi ý:** Kích hoạt Trợ lý AI để quét sâu toàn bộ tập dữ liệu và tự động viết báo cáo đề xuất chiến lược.")
            if st.button("🚀 BẮT ĐẦU PHÂN TÍCH BẰNG AI", use_container_width=True):
                st.session_state.ai_report_requested = True
                st.rerun()
        
        if st.session_state.ai_report_requested:
            with st.spinner("AI Agent đang tự động đọc dữ liệu và xây dựng báo cáo phân tích..."):
                try:
                    ai_report = get_automated_dataset_report(df)
                    st.markdown('<div style="background-color: #f8f9fa; border-left: 5px solid #ffd400; padding: 25px; border-radius: 8px; line-height: 1.6;">', unsafe_allow_html=True)
                    st.markdown(ai_report)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if st.button("🔄 Làm mới báo cáo", key="refresh_ai_report"):
                        st.cache_data.clear() # Xóa cache để gọi lại API
                        st.rerun()
                except Exception as e:
                    st.error(f"Không thể tạo báo cáo tự động: {e}")
                    if st.button("Thử lại"):
                        st.rerun()

    # 4. Khảo sát phân phối xác suất chuyên sâu cho TẤT CẢ CỘT SỐ
    st.markdown("---")
    st.markdown("### 📊 Phân Tích Thống Kê Học & Phân Phối Xác Suất (Mọi Cột Số)")
    
    # Tạo bộ tính toán thống kê nội bộ hoàn toàn Agnostic (Không phụ thuộc tên cột)
    numeric_cols_to_analyze = list(df.select_dtypes(include=['number']).columns)
    
    if not numeric_cols_to_analyze:
        st.warning("Không tìm thấy cột dữ liệu số nào để thực hiện phân tích thống kê chuyên sâu. Vui lòng sử dụng công cụ 'Làm sạch Tiền tệ' ở Sidebar để chuyển đổi!")
        dist_stats = {}
    else:
        dist_stats = {}
        for col in numeric_cols_to_analyze:
            series = df[col].dropna()
            if len(series) > 0:
                mean_val = float(series.mean())
                median_val = float(series.median())
                std_val = float(series.std())
                skew_val = float(series.skew())
                kurt_val = float(series.kurt())
                cv_val = float(std_val / mean_val) if mean_val > 0 else 0.0
                
                # Diễn giải
                b_desc = "Lệch phải" if skew_val > 0.5 else ("Lệch trái" if skew_val < -0.5 else "Đối xứng tương đối")
                k_desc = "Đuôi dày/Nhọn" if kurt_val > 3.0 else "Chuẩn/Bẹt"
                
                dist_stats[col] = {
                    'col_name': col,
                    'mean': mean_val,
                    'median': median_val,
                    'std': std_val,
                    'skew': skew_val,
                    'kurt': kurt_val,
                    'cv': cv_val,
                    'bias_interpretation': f"{b_desc}. Giá trị tập trung lệch về một phía của trung bình.",
                    'kurt_interpretation': f"{k_desc}. Phản ánh mức độ xuất hiện của ngoại lai."
                }

    if dist_stats:
        selected_stat_label = st.radio(
            "🎯 Chọn CỘT SỐ bất kỳ bạn muốn khảo sát sâu sắc:",
            options=list(dist_stats.keys()),
            horizontal=True,
            key="lab_stat_radio"
        )
        
        selected_stat = dist_stats[selected_stat_label]
        col_name = selected_stat['col_name']
        
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.markdown(f"""
            <div class="stat-box" style="border-left-color: #1E88E5;">
                <div class="stat-label">Trung bình / Trung vị</div>
                <div class="stat-value" style="font-size: 1.3rem;">${selected_stat['mean']:,.1f} / ${selected_stat['median']:,.1f}</div>
                <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Mất cân bằng: {abs(selected_stat['mean'] - selected_stat['median']) / selected_stat['mean'] * 100:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
            
        with sc2:
            skew_color = "#E53935" if abs(selected_stat['skew']) > 1.0 else ("#FB8C00" if abs(selected_stat['skew']) > 0.5 else "#43A047")
            st.markdown(f"""
            <div class="stat-box" style="border-left-color: {skew_color};">
                <div class="stat-label">Độ lệch (Skewness / Bias)</div>
                <div class="stat-value">{selected_stat['skew']:.3f}</div>
                <div style="font-size: 0.8rem; color: {skew_color}; margin-top: 5px; font-weight: bold;">
                    { "Lệch Phải (Bias Dương)" if selected_stat['skew'] > 0 else "Lệch Trái (Bias Âm)" }
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with sc3:
            kurt_color = "#8E24AA" if selected_stat['kurt'] > 3.0 else "#5E35B1"
            st.markdown(f"""
            <div class="stat-box" style="border-left-color: {kurt_color};">
                <div class="stat-label">Độ nhọn (Kurtosis / Tails)</div>
                <div class="stat-value">{selected_stat['kurt']:.3f}</div>
                <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Mô tả đuôi phân phối</div>
            </div>
            """, unsafe_allow_html=True)
            
        with sc4:
            st.markdown(f"""
            <div class="stat-box" style="border-left-color: #00ACC1;">
                <div class="stat-label">Hệ số Biến thiên (CV)</div>
                <div class="stat-value">{selected_stat['cv']:.3f}</div>
                <div style="font-size: 0.8rem; color: #757575; margin-top: 5px;">Độ phân tán dữ liệu</div>
            </div>
            """, unsafe_allow_html=True)
            
        fig_dist = px.histogram(
            df, 
            x=col_name,
            marginal="box",
            histnorm="probability density",
            title=f"Hàm Mật độ Phân phối Xác suất & Phân vị thực tế của {selected_stat_label}",
            color_discrete_sequence=['#1E88E5'],
            opacity=0.75
        )
        fig_dist.update_layout(
            xaxis_title=selected_stat_label,
            yaxis_title="Mật độ Xác suất",
            template="plotly_white",
            height=400
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        
        # Thẻ diễn giải học thuật
        st.markdown(f"""
        <div style="background-color: #e0f7fa; border-left: 5px solid #00ACC1; padding: 20px; border-radius: 8px; line-height: 1.6;">
            <strong>🔬 Nhận định toán học thống kê:</strong><br>
            • 📐 <strong>Skewness ({selected_stat['skew']:.4f}):</strong> {selected_stat['bias_interpretation']}<br>
            • 🔔 <strong>Kurtosis ({selected_stat['kurt']:.4f}):</strong> {selected_stat['kurt_interpretation']}<br>
            • 💡 <strong>Tính bất đối xứng:</strong> Khoảng cách lệch giữa Trung bình (${selected_stat['mean']:,.1f}) và Trung vị (${selected_stat['median']:,.1f}) chứng minh sự chi phối của các nhóm dữ liệu cực hữu (Outliers), mô tả quy luật Pareto kinh điển trong miền dữ liệu này.
        </div>
        """, unsafe_allow_html=True)

        # 5. Kiểm Định Giả Thuyết & Thống Kê Suy Diễn (Hypothesis Testing)
        st.markdown("---")
        st.markdown("### 🔬 Trung Tâm Kiểm Định Giả Thuyết & Thống Kê Suy Diễn (Hypothesis Testing)")
        st.markdown("""
        Sử dụng các phương pháp thống kê suy diễn chuyên sâu để kiểm chứng các giả thuyết khoa học về sự khác biệt giá trị giữa các phân loại nhóm thuộc tập dữ liệu tải lên.
        """)

        import scipy.stats as stats

        lab_test_type = st.radio(
            "Chọn phương pháp kiểm định giả thuyết Lab:",
            options=["Kiểm định t hai mẫu độc lập (Two-Sample t-Test)", "Phân tích phương sai một nhân tố (One-Way ANOVA)"],
            horizontal=True,
            key="lab_test_type_radio"
        )

        # Lấy danh sách cột phân loại phù hợp (có số lượng giá trị duy nhất từ 2 đến 10)
        lab_cat_cols = [c for c in df.columns if df[c].nunique() >= 2 and df[c].nunique() <= 10]
        lab_num_cols = []
        if sales_col: lab_num_cols.append(sales_col)
        if profit_col: lab_num_cols.append(profit_col)
        # Bổ sung thêm các cột số nếu có
        for c in df.select_dtypes(include=['number']).columns:
            if c not in lab_num_cols:
                lab_num_cols.append(c)

        if not lab_cat_cols or not lab_num_cols:
            st.warning("Không tìm thấy đủ trường phân loại và số liệu thích hợp trong file để tiến hành kiểm định.")
        else:
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                lab_selected_num = st.selectbox("Chọn chỉ số số liệu khảo sát (Lab):", options=lab_num_cols, key="lab_num_select")
            with col_l2:
                lab_selected_cat = st.selectbox("Chọn trường phân loại (Lab):", options=lab_cat_cols, key="lab_cat_select")
            
            if lab_test_type == "Kiểm định t hai mẫu độc lập (Two-Sample t-Test)":
                lab_unique_groups = sorted(df[lab_selected_cat].dropna().unique())
                if len(lab_unique_groups) < 2:
                    st.error("Trường phân loại cần có ít nhất 2 nhóm khác biệt.")
                else:
                    col_lg1, col_lg2 = st.columns(2)
                    with col_lg1:
                        lg1 = st.selectbox("Chọn nhóm thứ nhất (Lab):", options=lab_unique_groups, index=0, key="lg1_select")
                    with col_lg2:
                        lg2 = st.selectbox("Chọn nhóm thứ hai (Lab):", options=lab_unique_groups, index=min(1, len(lab_unique_groups)-1), key="lg2_select")
                        
                    if lg1 == lg2:
                        st.warning("Vui lòng chọn hai nhóm khác nhau để thực hiện kiểm định.")
                    else:
                        series_lg1 = df[df[lab_selected_cat] == lg1][lab_selected_num].dropna()
                        series_lg2 = df[df[lab_selected_cat] == lg2][lab_selected_num].dropna()
                        
                        # Chạy kiểm định Welch's t-test
                        t_stat, p_val = stats.ttest_ind(series_lg1, series_lg2, equal_var=False)
                        
                        st.markdown(f"##### **🧬 Kết quả Kiểm định t-Test độc lập (Welch's t-Test)**")
                        st.markdown(f"* **Giả thuyết Không ($H_0$):** Không có sự khác biệt có ý nghĩa thống kê về trung bình `{lab_selected_num}` giữa `{lg1}` và `{lg2}`.")
                        st.markdown(f"* **Giả thuyết Đối ($H_1$):** Có sự khác biệt có ý nghĩa thống kê về trung bình `{lab_selected_num}` giữa `{lg1}` và `{lg2}`.")
                        
                        lc1, lc2, lc3, lc4 = st.columns(4)
                        with lc1:
                            st.markdown(f"""
                            <div class="stat-box" style="border-left-color: #1E88E5;">
                                <div class="stat-label">Trung bình {lg1}</div>
                                <div class="stat-value" style="font-size: 1.3rem;">${series_lg1.mean():,.2f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with lc2:
                            st.markdown(f"""
                            <div class="stat-box" style="border-left-color: #E53935;">
                                <div class="stat-label">Trung bình {lg2}</div>
                                <div class="stat-value" style="font-size: 1.3rem;">${series_lg2.mean():,.2f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with lc3:
                            st.markdown(f"""
                            <div class="stat-box" style="border-left-color: #8E24AA;">
                                <div class="stat-label">Trị số t (t-stat)</div>
                                <div class="stat-value" style="font-size: 1.3rem;">{t_stat:.4f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        with lc4:
                            p_display = f"{p_val:.4f}" if p_val >= 0.0001 else f"{p_val:.2e}"
                            p_color = "#43A047" if p_val < 0.05 else "#FB8C00"
                            st.markdown(f"""
                            <div class="stat-box" style="border-left-color: {p_color};">
                                <div class="stat-label">Trị số p (p-value)</div>
                                <div class="stat-value" style="font-size: 1.3rem; color: {p_color};">{p_display}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        fig_comp = px.box(
                            df[df[lab_selected_cat].isin([lg1, lg2])],
                            x=lab_selected_cat,
                            y=lab_selected_num,
                            color=lab_selected_cat,
                            points="outliers",
                            title=f"Biểu đồ Hộp so sánh phân phối {lab_selected_num} giữa {lg1} và {lg2}",
                            color_discrete_sequence=['#1E88E5', '#E53935']
                        )
                        fig_comp.update_layout(template="plotly_white", height=350)
                        st.plotly_chart(fig_comp, use_container_width=True)
                        
                        st.markdown('<div class="stat-box" style="border-left-color: #00ACC1; padding: 20px; line-height: 1.6;" unsafe_allow_html=True>', unsafe_allow_html=True)
                        if p_val < 0.05:
                            st.markdown(f"##### **Kết luận thống kê (Mức ý nghĩa 5%):**")
                            st.markdown(f"👉 **BÁC BỎ GIẢ THUYẾT KHÔNG ($H_0$):** Trị số $p$ (`{p_display}`) < `0.05`. Đủ cơ sở khẳng định sự khác biệt có ý nghĩa thống kê rõ rệt về mức `{lab_selected_num}` trung bình giữa **{lg1}** (Trung bình: `${series_lg1.mean():,.2f}`) và **{lg2}** (Trung bình: `${series_lg2.mean():,.2f}`).")
                        else:
                            st.markdown(f"##### **Kết luận thống kê (Mức ý nghĩa 5%):**")
                            st.markdown(f"👉 **CHƯA ĐỦ CƠ SỞ BÁC BỎ GIẢ THUYẾT KHÔNG ($H_0$):** Trị số $p$ (`{p_display}`) $\geq$ `0.05`. Chưa có đủ căn cứ thống kê cho thấy sự khác biệt về `{lab_selected_num}` trung bình giữa **{lg1}** và **{lg2}**.")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
            elif lab_test_type == "Phân tích phương sai một nhân tố (One-Way ANOVA)":
                lab_unique_groups = sorted(df[lab_selected_cat].dropna().unique())
                if len(lab_unique_groups) < 3:
                    st.warning("Phương pháp ANOVA phù hợp so sánh từ 3 nhóm trở lên. Dưới 3 nhóm, vui lòng chuyển sang Kiểm định t-Test.")
                else:
                    groups_data = [df[df[lab_selected_cat] == g][lab_selected_num].dropna() for g in lab_unique_groups]
                    f_stat, p_val = stats.f_oneway(*groups_data)
                    
                    st.markdown(f"##### **🧬 Kết quả Kiểm định Phân tích Phương sai (One-Way ANOVA)**")
                    st.markdown(f"* **Giả thuyết Không ($H_0$):** Giá trị trung bình của tất cả các nhóm đều bằng nhau.")
                    st.markdown(f"* **Giả thuyết Đối ($H_1$):** Có ít nhất một cặp nhóm có giá trị trung bình khác nhau.")
                    
                    lac1, lac2, lac3 = st.columns(3)
                    with lac1:
                        st.markdown(f"""
                        <div class="stat-box" style="border-left-color: #1E88E5;">
                            <div class="stat-label">Số nhóm so sánh</div>
                            <div class="stat-value">{len(lab_unique_groups)} nhóm</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with lac2:
                        st.markdown(f"""
                        <div class="stat-box" style="border-left-color: #8E24AA;">
                            <div class="stat-label">Trị số F (F-stat)</div>
                            <div class="stat-value">{f_stat:.4f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with lac3:
                        p_display = f"{p_val:.4f}" if p_val >= 0.0001 else f"{p_val:.2e}"
                        p_color = "#43A047" if p_val < 0.05 else "#FB8C00"
                        st.markdown(f"""
                        <div class="stat-box" style="border-left-color: {p_color};">
                            <div class="stat-label">Trị số p (p-value)</div>
                            <div class="stat-value" style="color: {p_color}; font-size: 1.3rem;">{p_display}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    fig_anova = px.violin(
                        df,
                        x=lab_selected_cat,
                        y=lab_selected_num,
                        color=lab_selected_cat,
                        box=True,
                        points="outliers",
                        title=f"Biểu đồ Violin so sánh phân phối {lab_selected_num} giữa các nhóm của {lab_selected_cat}"
                    )
                    fig_anova.update_layout(template="plotly_white", height=350)
                    st.plotly_chart(fig_anova, use_container_width=True)
                    
                    st.markdown('<div class="stat-box" style="border-left-color: #00ACC1; padding: 20px; line-height: 1.6;">', unsafe_allow_html=True)
                    if p_val < 0.05:
                        st.markdown(f"##### **Kết luận thống kê (Mức ý nghĩa 5%):**")
                        st.markdown(f"👉 **BÁC BỎ GIẢ THUYẾT KHÔNG ($H_0$):** Trị số $p$ (`{p_display}`) < `0.05`. Đủ cơ sở khẳng định sự khác biệt có ý nghĩa thống kê về trị số `{lab_selected_num}` giữa các nhóm.")
                    else:
                        st.markdown(f"##### **Kết luận thống kê (Mức ý nghĩa 5%):**")
                        st.markdown(f"👉 **CHƯA ĐỦ CƠ SỞ BÁC BỎ GIẢ THUYẾT KHÔNG ($H_0$):** Trị số $p$ (`{p_display}`) $\geq$ `0.05`. Chưa có đủ minh chứng thống kê chứng tỏ sự khác biệt trung bình giữa các nhóm.")
                    st.markdown('</div>', unsafe_allow_html=True)

        # 6. Kỹ Nghệ Đặc Trưng (Feature Engineering Lab)
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
            key="fe_method_radio"
        )

        # Tạo một bản sao dữ liệu đã biến đổi để không làm hỏng dữ liệu gốc
        if 'engineered_df' not in st.session_state:
            st.session_state['engineered_df'] = df.copy()

        eng_df = st.session_state['engineered_df']

        if fe_method == "Biến đổi Logarithm (Loại bỏ Skewness)":
            st.markdown("##### **📈 Biến đổi Logarithm: $y = \\log(x + 1)$**")
            st.markdown("Giúp kéo dẹt các cột số có phân phối lệch phải mạnh (Right-skewed) với Kurtosis cao trở về phân phối chuẩn đối xứng (Bell curve).")
            
            log_col = st.selectbox("Chọn cột số để áp dụng biến đổi Log:", options=lab_num_cols, key="log_col_select")
            
            if st.button("Áp dụng Biến đổi Log", key="apply_log_btn"):
                # Áp dụng log1p (tránh lỗi log(0))
                new_col_name = f"Log_{log_col}"
                eng_df[new_col_name] = np.log1p(eng_df[log_col])
                st.session_state['engineered_df'] = eng_df
                st.success(f"✅ Đã tạo thành công đặc trưng mới: `{new_col_name}`!")

            new_col_name = f"Log_{log_col}"
            if new_col_name in eng_df.columns:
                # Vẽ biểu đồ so sánh trước/sau
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    fig_before = px.histogram(eng_df, x=log_col, title=f"Trước biến đổi: {log_col} (Lệch mạnh)", color_discrete_sequence=['#E53935'])
                    fig_before.update_layout(template="plotly_white", height=300)
                    st.plotly_chart(fig_before, use_container_width=True)
                with col_b2:
                    fig_after = px.histogram(eng_df, x=new_col_name, title=f"Sau biến đổi Log: {new_col_name} (Chuẩn đối xứng)", color_discrete_sequence=['#43A047'])
                    fig_after.update_layout(template="plotly_white", height=300)
                    st.plotly_chart(fig_after, use_container_width=True)

        elif fe_method == "Phân nhóm Giá trị (Binning/Discretization)":
            st.markdown("##### **📊 Phân nhóm Giá trị: Liên tục $\\rightarrow$ Rời rạc**")
            st.markdown("Chia các giá trị số liên tục thành các khoảng/phân khúc logic (ví dụ: Thấp, Trung bình, Cao) để dễ dàng lập chiến lược marketing.")
            
            bin_col = st.selectbox("Chọn cột số để phân nhóm:", options=lab_num_cols, key="bin_col_select")
            num_bins = st.slider("Số lượng nhóm muốn chia:", min_value=2, max_value=5, value=3, key="num_bins_slider")
            
            bin_labels = []
            st.markdown("Nhập nhãn cho từng nhóm (từ thấp đến cao):")
            col_lbls = st.columns(num_bins)
            for idx in range(num_bins):
                with col_lbls[idx]:
                    default_label = ["Thấp (Low)", "Trung bình (Medium)", "Cao (High)", "Rất cao (Very High)", "Vượt trội"][idx]
                    label_val = st.text_input(f"Nhãn nhóm {idx+1}:", value=default_label, key=f"label_bin_{idx}")
                    bin_labels.append(label_val)
                    
            if st.button("Áp dụng Phân nhóm", key="apply_binning_btn"):
                new_bin_col = f"Grouped_{bin_col}"
                try:
                    # Phân nhóm dựa trên khoảng chia đều (qcut hoặc cut)
                    eng_df[new_bin_col] = pd.qcut(eng_df[bin_col], q=num_bins, labels=bin_labels, duplicates='drop')
                    st.session_state['engineered_df'] = eng_df
                    st.success(f"✅ Đã tạo thành công phân nhóm mới: `{new_bin_col}`!")
                except Exception as e:
                    st.error(f"Lỗi khi phân nhóm: {e}. Thử giảm số lượng nhóm.")

            new_bin_col = f"Grouped_{bin_col}"
            if new_bin_col in eng_df.columns:
                # Vẽ đồ thị đếm phân bố của nhóm mới tạo
                counts = eng_df[new_bin_col].value_counts().reset_index()
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
            
            scale_col = st.selectbox("Chọn cột số để chuẩn hóa:", options=lab_num_cols, key="scale_col_select")
            scale_type = st.selectbox("Chọn phương pháp chuẩn hóa:", options=["MinMax Scaling (Quy về khoảng 0 đến 1)", "Standard Scaling (Z-score: trung bình=0, std=1)"], key="scale_type_select")
            
            if st.button("Áp dụng Chuẩn hóa", key="apply_scaling_btn"):
                new_scale_col = f"Scaled_{scale_col}"
                series = eng_df[scale_col].dropna()
                if scale_type.startswith("MinMax"):
                    eng_df[new_scale_col] = (eng_df[scale_col] - series.min()) / (series.max() - series.min())
                else:
                    eng_df[new_scale_col] = (eng_df[scale_col] - series.mean()) / series.std()
                st.session_state['engineered_df'] = eng_df
                st.success(f"✅ Đã chuẩn hóa thành công! Tạo cột mới: `{new_scale_col}`")

            new_scale_col = f"Scaled_{scale_col}"
            if new_scale_col in eng_df.columns:
                st.markdown(f"**Thống kê mô tả cột `{new_scale_col}` sau chuẩn hóa:**")
                st.dataframe(eng_df[[scale_col, new_scale_col]].describe().T, use_container_width=True)

        elif fe_method == "Mã hóa biến danh mục (One-Hot / Label Encoding)":
            st.markdown("##### **🔤 Mã hóa biến danh mục (Categorical Encoding)**")
            st.markdown("Chuyển đổi dữ liệu chuỗi/chữ thành định dạng số giúp các mô hình toán học và học máy có thể tính toán được.")
            
            enc_col = st.selectbox("Chọn cột danh mục để mã hóa:", options=lab_cat_cols, key="enc_col_select")
            enc_type = st.selectbox("Chọn thuật toán mã hóa:", options=["Label Encoding (Mã hóa số thứ tự: 0, 1, 2...)", "One-Hot Encoding (Tạo các cột nhị phân 0/1)"], key="enc_type_select")
            
            if st.button("Áp dụng Mã hóa", key="apply_encoding_btn"):
                if enc_type.startswith("Label"):
                    new_enc_col = f"Encoded_{enc_col}"
                    eng_df[new_enc_col] = eng_df[enc_col].astype('category').cat.codes
                    st.session_state['engineered_df'] = eng_df
                    st.success(f"✅ Mã hóa thành công! Đã tạo cột số nguyên: `{new_enc_col}`")
                else:
                    dummies = pd.get_dummies(eng_df[enc_col], prefix=f"OneHot_{enc_col}").astype(int)
                    eng_df = pd.concat([eng_df, dummies], axis=1)
                    st.session_state['engineered_df'] = eng_df
                    st.success(f"✅ One-Hot Encoding thành công! Đã lồng ghép {dummies.shape[1]} cột nhị phân mới vào bảng dữ liệu.")

            # Hiển thị preview 10 cột mới mã hóa nếu có
            st.markdown("**Bảng xem trước đặc trưng mã hóa hiện tại:**")
            preview_cols = [c for c in eng_df.columns if "Encoded" in c or "OneHot" in c]
            if preview_cols:
                st.dataframe(eng_df[[enc_col] + preview_cols[:10]].dropna().head(10), use_container_width=True)
            else:
                st.info("Chưa áp dụng mã hóa nào.")

        # Nút xuất dữ liệu đã biến đổi
        st.markdown("---")
        st.markdown("##### **💾 Xuất dữ liệu đã hoàn thiện Kỹ nghệ Đặc trưng (Export Dataset)**")
        st.markdown("Tải xuống tệp dữ liệu đã được tiền xử lý và tích hợp toàn bộ các đặc trưng mới được tạo ra từ Lab.")
        
        csv_data = eng_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Tải xuống Dataset đã hoàn thiện Feature Engineering (.csv)",
            data=csv_data,
            file_name="engineered_dataset_lab.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_engineered_csv_btn"
        )

else:
    # --- Dataset Storage & Management Center ---
    st.markdown("""
    <div style="background-color: #f8f9fa; padding: 25px; border-radius: 12px; border-left: 5px solid #1E88E5; margin-bottom: 25px;">
        <h4 style="margin-top: 0; color: #1E88E5;">📂 Trung tâm Phân Tích Dữ Liệu Marketing (Marketing Hub)</h4>
        <p style="font-size: 0.95rem; color: #555; margin-bottom: 0;">Chào mừng bạn đến với Trình Phân Tích Marketing chuyên biệt. Bạn có thể nạp nhanh tệp chiến dịch mẫu hoặc sử dụng bộ tải lên ở Sidebar bên trái để bắt đầu tính toán CPC, CTR và ROAS tự động:</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown("""
        <div style="border: 1px solid #ddd; padding: 20px; border-radius: 10px; background-color: white; height: 160px;">
            <strong style="color: #2a5298; font-size: 1.1rem;">📊 Dataset 1: german_credit_data.csv</strong><br>
            <span style="font-size: 0.85rem; color: #666; display: block; margin-top: 8px;">
                • Kích thước: 139 KB<br>
                • Mô tả: Tập dữ liệu xếp hạng rủi ro tín dụng của các khách hàng ngân hàng Đức.
            </span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Nạp dữ liệu Tín dụng Đức vào Lab", key="load_german_csv_btn", use_container_width=True):
            try:
                df_german = pd.read_csv('data/german_credit_data.csv', sep=',')
                st.session_state['lab_df'] = df_german
                st.session_state['engineered_df'] = df_german.copy()
                st.rerun()
            except Exception as e:
                st.error(f"Không tìm thấy hoặc không đọc được file data/german_credit_data.csv: {e}")
                
    with col_f2:
        st.markdown("""
        <div style="border: 1px solid #ddd; padding: 20px; border-radius: 10px; background-color: white; height: 160px;">
            <strong style="color: #2a5298; font-size: 1.1rem;">📦 Dataset 2: superstore (1).csv</strong><br>
            <span style="font-size: 0.85rem; color: #666; display: block; margin-top: 8px;">
                • Kích thước: 12.4 MB<br>
                • Mô tả: Tập dữ liệu bán hàng siêu thị chuẩn hóa quốc tế với đầy đủ thuộc tính logistics.
            </span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Nạp dữ liệu Superstore vào Lab", key="load_superstore_csv_btn", use_container_width=True):
            try:
                df_super = pd.read_csv('data/superstore (1).csv', sep=';', encoding='latin1')
                st.session_state['lab_df'] = df_super
                st.session_state['engineered_df'] = df_super.copy()
                st.rerun()
            except Exception as e:
                st.error(f"Không tìm thấy hoặc không đọc được file data/superstore (1).csv: {e}")
                
    st.markdown("""
    <div style="text-align: center; padding: 40px 20px; color: #757575;">
        <span style="font-size: 4rem;">📈</span>
        <h4 style="margin-top: 15px;">Hệ thống Phân tích Chiến Dịch Marketing Tự Động</h4>
        <p style="max-width: 600px; margin: 5px auto 0 auto; line-height: 1.6;">
            Giải pháp đo lường ROAS, tối ưu hóa ngân sách quảng cáo tự động dựa trên dữ liệu thô từ Facebook Ads, Google Ads hoặc TikTok Ads của bạn!
        </p>
    </div>
    """, unsafe_allow_html=True)

# Hoàn tất trang
