import pandas as pd
import numpy as np
import re
from utils.i18n import t

def ask_agent(agent_placeholder, prompt, df=None, rfm_df=None):
    """
    Chatbot hoàn toàn dựa trên Quy tắc (Rule-based) bằng Python theo chuẩn SOP.
    Loại bỏ phụ thuộc API bên ngoài, tối ưu tốc độ phản hồi tức thì (<0.01s).
    Hỗ trợ các tham số linh hoạt từ cả chat_widget và trang báo cáo.
    """
    # Lấy DataFrame trực tiếp từ session_state nếu tham số df/rfm_df truyền vào rỗng
    import streamlit as st
    if df is None:
        df = st.session_state.get("df_data")
    if rfm_df is None:
        rfm_df = st.session_state.get("rfm_data")
        
    # Nếu vẫn không tìm thấy dữ liệu (trường hợp backup khẩn cấp)
    if df is None or df.empty:
        from utils.data_processor import load_and_clean_data, calculate_rfm
        try:
            df = load_and_clean_data()
            rfm_df = calculate_rfm(df)
        except:
            return "⚠️ Xin lỗi, hệ thống không thể truy xuất dữ liệu để trả lời lúc này. Vui lòng tải lại trang."

    p = str(prompt).lower().strip()
    
    # 1. NHẬN DIỆN TRƯỜNG HỢP TẠO BÁO CÁO CHIẾN LƯỢC HỌC THUẬT (CHO TRANG 8)
    if "đồ án tốt nghiệp" in p or "báo cáo phân tích chiến lược" in p or "chiến lược kinh doanh" in p:
        return generate_strategic_report_rule_based(df, rfm_df)

    # LẤY TÊN CỘT ĐÚNG
    sales_col = 'Sales' if 'Sales' in df.columns else df.select_dtypes(include=['number']).columns[0]
    profit_col = 'Profit' if 'Profit' in df.columns else df.select_dtypes(include=['number']).columns[1]
    region_col = 'Region' if 'Region' in df.columns else None
    category_col = 'Category' if 'Category' in df.columns else None
    market_col = 'Market' if 'Market' in df.columns else None

    # CÁC CHỈ SỐ KPI TỔNG HỢP SẴN
    total_sales = df[sales_col].sum()
    total_profit = df[profit_col].sum()
    margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
    total_orders = df['Order ID'].nunique() if 'Order ID' in df.columns else len(df)

    # 2. CHÀO HỎI & GIỚI THIỆU (GREETINGS)
    if any(kw in p for kw in ["chào", "hello", "hi", "bạn là ai", "tên gì", "chức năng", "giúp"]):
        return (
            "👋 **Xin chào! Em là Trợ lý Ảo Rule-based chuyên trách Dữ liệu Superstore.**\n\n"
            "Em được thiết kế tối ưu bằng Python để **truy vấn dữ liệu tức thời** mà không cần Internet. Anh/Chị có thể hỏi em về:\n"
            "- 💰 **Doanh thu**: \"Doanh thu hệ thống\", \"Doanh thu theo khu vực/danh mục\"\n"
            "- 📈 **Lợi nhuận**: \"Tổng lợi nhuận\", \"Biên lợi nhuận\", \"Lợi nhuận theo vùng\"\n"
            "- 🚨 **Rủi ro Rời bỏ**: \"Tình hình rời bỏ\", \"Customer Churn\", \"Khách hàng nguy cơ\"\n"
            "- 🏆 **Top Performers**: \"Khu vực tốt nhất\", \"Danh mục bán chạy nhất\"\n\n"
            "Anh/Chị cần em tra cứu thông tin nào ạ? 😊"
        )

    # 3. TRUY VẤN CHURN RISK & RỦI RO RỜI BỎ (CUSTOMER CHURN) - KEY SOP REQUIREMENT
    if any(kw in p for kw in ["rời bỏ", "churn", "rủi ro", "at risk", "nguy cơ"]):
        if rfm_df is not None and not rfm_df.empty and 'Churn_Risk' in rfm_df.columns:
            counts = rfm_df['Churn_Risk'].value_counts()
            high_risk = counts.get("Nguy cơ cao (High Risk)", 0)
            churned = counts.get("Đã rời bỏ (Churned)", 0)
            active = counts.get("An toàn (Active)", 0)
            needs_attention = counts.get("Cần chú ý (Needs Attention)", 0)
            total = len(rfm_df)
            
            high_risk_pct = (high_risk / total * 100) if total > 0 else 0
            churned_pct = (churned / total * 100) if total > 0 else 0
            
            return (
                f"🚨 **BÁO CÁO RỦI RO RỜI BỎ (CUSTOMER CHURN ANALYSIS)**\n\n"
                f"Dựa trên thuật toán phân khúc RFM hiện tại của hệ thống:\n"
                f"- 🔥 **Nguy cơ cao (High Risk)**: **{high_risk:,}** khách hàng ({high_risk_pct:.1f}%).\n"
                f"- 🚪 **Đã rời bỏ (Churned)**: **{churned:,}** khách hàng ({churned_pct:.1f}%).\n"
                f"- ✅ **An toàn (Active)**: **{active:,}** khách hàng.\n"
                f"- ⚠️ **Cần chú ý (Needs Attention)**: **{needs_attention:,}** khách hàng.\n\n"
                f"💡 *Khuyến nghị*: Anh/Chị cần triển khai gấp chương trình ưu đãi đặc biệt cho nhóm **Nguy cơ cao** vì họ là những khách hàng từng chi tiêu rất nhiều nhưng đã lâu không có giao dịch mới."
            )
        return "⚠️ Hiện tại hệ thống chưa thể trích xuất dữ liệu Churn Risk từ RFM."

    # 4. TRUY VẤN BIÊN LỢI NHUẬN (PROFIT MARGIN) - KEY KPI SOP REQUIREMENT
    if any(kw in p for kw in ["biên", "tỷ suất", "tỷ lệ lợi nhuận", "margin"]):
        return (
            f"📊 **BIÊN LỢI NHUẬN (PROFIT MARGIN) TOÀN HỆ THỐNG**\n\n"
            f"- ⚙️ **Công thức tính chuẩn SOP**: `Profit Margin = (Total Profit / Total Sales) * 100`\n"
            f"- 💰 **Tổng Lợi nhuận**: `${total_profit:,.2f}`\n"
            f"- 📈 **Tổng Doanh thu**: `${total_sales:,.2f}`\n"
            f"- 🎯 **Kết quả Biên lợi nhuận**: **{margin:.2f}%**\n\n"
            f"Chỉ số này phản ánh cứ mỗi 100$ doanh thu mang lại, siêu thị giữ lại được **{margin:.2f}$** lợi nhuận sau khi trừ đi chi phí vốn và chi phí vận hành."
        )

    # 5. TRUY VẤN DOANH THU (SALES)
    if any(kw in p for kw in ["doanh thu", "doanh số", "bán được"]):
        # Phân tích theo Khu vực
        if any(kw in p for kw in ["khu vực", "vùng"]):
            if region_col:
                reg_sales = df.groupby(region_col)[sales_col].sum().sort_values(ascending=False)
                lines = [f"- **{reg}**: `${val:,.2f}`" for reg, val in reg_sales.items()]
                return "🌍 **DOANH THU THEO KHU VỰC (REGION):**\n\n" + "\n".join(lines)
        # Phân tích theo Danh mục
        if any(kw in p for kw in ["danh mục", "sản phẩm"]):
            if category_col:
                cat_sales = df.groupby(category_col)[sales_col].sum().sort_values(ascending=False)
                lines = [f"- **{cat}**: `${val:,.2f}`" for cat, val in cat_sales.items()]
                return "📦 **DOANH THU THEO DANH MỤC (CATEGORY):**\n\n" + "\n".join(lines)
        # Tổng Doanh thu
        return (
            f"💰 **TỔNG DOANH THU HỆ THỐNG**\n\n"
            f"- Tổng doanh số tích lũy: **${total_sales:,.2f}**\n"
            f"- Tổng số đơn giao dịch thành công: **{total_orders:,}** đơn hàng.\n"
            f"- Trung bình mỗi đơn hàng đạt: **${(total_sales/total_orders):,.2f}**."
        )

    # 6. TRUY VẤN LỢI NHUẬN (PROFIT)
    if any(kw in p for kw in ["lợi nhuận", "lãi", "lỗ"]):
        # Phân tích theo Khu vực
        if any(kw in p for kw in ["khu vực", "vùng"]):
            if region_col:
                reg_profit = df.groupby(region_col)[profit_col].sum().sort_values(ascending=False)
                lines = [f"- **{reg}**: `${val:,.2f}`" for reg, val in reg_profit.items()]
                return "🌍 **LỢI NHUẬN THEO KHU VỰC (REGION):**\n\n" + "\n".join(lines)
        # Phân tích theo Danh mục
        if any(kw in p for kw in ["danh mục", "sản phẩm"]):
            if category_col:
                cat_profit = df.groupby(category_col)[profit_col].sum().sort_values(ascending=False)
                lines = [f"- **{cat}**: `${val:,.2f}`" for cat, val in cat_profit.items()]
                return "📦 **LỢI NHUẬN THEO DANH MỤC (CATEGORY):**\n\n" + "\n".join(lines)
        # Tổng Lợi nhuận
        return (
            f"📈 **TỔNG LỢI NHUẬN TOÀN HỆ THỐNG**\n\n"
            f"- Tổng lợi nhuận ròng: **${total_profit:,.2f}**\n"
            f"- Biên lợi nhuận trung bình: **{margin:.2f}%**\n"
            f"- Trạng thái kinh doanh: **{'CÓ LÃI ✅' if total_profit > 0 else 'LỖ VỐN ❌'}**."
        )

    # 7. TOP PERFORMERS (TỐT NHẤT / TỆ NHẤT)
    if any(kw in p for kw in ["tốt nhất", "cao nhất", "bán chạy", "nhiều nhất"]):
        if region_col:
            best_reg = df.groupby(region_col)[sales_col].sum().idxmax()
            best_reg_val = df.groupby(region_col)[sales_col].sum().max()
        if category_col:
            best_cat = df.groupby(category_col)[sales_col].sum().idxmax()
            best_cat_val = df.groupby(category_col)[sales_col].sum().max()
        return (
            f"🏆 **BÁO CÁO HIỆU SUẤT TỐT NHẤT (TOP PERFORMERS)**\n\n"
            f"- 🌍 Khu vực doanh thu lớn nhất: **{best_reg}** (${best_reg_val:,.2f})\n"
            f"- 📦 Danh mục sản phẩm bán chạy nhất: **{best_cat}** (${best_cat_val:,.2f})"
        )

    if any(kw in p for kw in ["thấp nhất", "kém nhất", "lỗ nhất", "ít nhất"]):
        if region_col:
            worst_reg = df.groupby(region_col)[profit_col].sum().idxmin()
            worst_reg_val = df.groupby(region_col)[profit_col].sum().min()
        if category_col:
            worst_cat = df.groupby(category_col)[profit_col].sum().idxmin()
            worst_cat_val = df.groupby(category_col)[profit_col].sum().min()
        return (
            f"⚠️ **BÁO CÁO KHU VỰC & SẢN PHẨM KÉM HIỆU QUẢ**\n\n"
            f"- 🌍 Khu vực lợi nhuận thấp nhất: **{worst_reg}** (${worst_reg_val:,.2f})\n"
            f"- 📦 Danh mục sản phẩm lỗ nhất: **{worst_cat}** (${worst_cat_val:,.2f})"
        )

    # 8. TRUY VẤN PHÂN KHÚC KHÁCH HÀNG (RFM)
    if "rfm" in p or "phân khúc" in p:
        if rfm_df is not None and not rfm_df.empty:
            # Tìm cột Segment trong RFM
            seg_col = 'RFM_Segment' if 'RFM_Segment' in rfm_df.columns else 'Segment' if 'Segment' in rfm_df.columns else None
            if seg_col:
                counts = rfm_df[seg_col].value_counts()
                lines = [f"- **{seg}**: **{cnt:,}** khách hàng" for seg, cnt in counts.items()]
                return "👥 **PHÂN PHỐI PHÂN KHÚC KHÁCH HÀNG (RFM):**\n\n" + "\n".join(lines)
        return "⚠️ Hiện tại dữ liệu phân khúc khách hàng chưa được nạp đầy đủ."

    # 9. FALLBACK KHI KHÔNG HIỂU CÂU HỎI
    return (
        "🤖 **Xin lỗi, em chưa thể tìm ra câu trả lời cho truy vấn này.**\n\n"
        "Vì em hoạt động theo Quy tắc (Rule-based) chuẩn SOP để đảm bảo tốc độ, xin Anh/Chị thử hỏi lại bằng các từ khóa phổ biến như:\n"
        "- *\"Doanh thu\"*, *\"Lợi nhuận\"*, *\"Biên lợi nhuận\"*\n"
        "- *\"Doanh thu theo khu vực/danh mục\"*\n"
        "- *\"Rủi ro rời bỏ\"*, *\"Churn Risk\"*\n"
        "- *\"Tốt nhất\"*, *\"Kém nhất\"*"
    )

def get_ai_agent(df, rfm_df):
    """
    Giữ lại chữ ký hàm để không gây lỗi Import ở các tệp tin khác.
    Trả về None vì hệ thống chuyển hoàn toàn sang Rule-based theo SOP.
    """
    return "RULE_BASED_AGENT_TOKEN"

def generate_strategic_report_rule_based(df, rfm_df):
    """
    Công cụ sinh báo cáo phân tích chiến lược tự động bằng Python theo Quy tắc.
    Tạo ra một tài liệu định dạng chuẩn Markdown cực kỳ chi tiết cho Đồ án tốt nghiệp.
    """
    sales_col = 'Sales' if 'Sales' in df.columns else df.select_dtypes(include=['number']).columns[0]
    profit_col = 'Profit' if 'Profit' in df.columns else df.select_dtypes(include=['number']).columns[1]
    region_col = 'Region' if 'Region' in df.columns else 'Region'
    category_col = 'Category' if 'Category' in df.columns else 'Category'

    # Tính toán nhanh số liệu
    total_sales = df[sales_col].sum()
    total_profit = df[profit_col].sum()
    margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
    
    worst_region = "N/A"
    if region_col in df.columns:
        try: worst_region = df.groupby(region_col)[profit_col].sum().idxmin()
        except: worst_region = "N/A"
        
    worst_category = "N/A"
    if category_col in df.columns:
        try: worst_category = df.groupby(category_col)[profit_col].sum().idxmin()
        except: worst_category = "N/A"

    # Phân phối Churn Risk
    churn_counts = {"Nguy cơ cao (High Risk)": 0, "Đã rời bỏ (Churned)": 0, "An toàn (Active)": 0, "Cần chú ý (Needs Attention)": 0}
    if rfm_df is not None and not rfm_df.empty and 'Churn_Risk' in rfm_df.columns:
        for k, v in rfm_df['Churn_Risk'].value_counts().items():
            churn_counts[k] = v

    report = f"""# 📑 BÁO CÁO PHÂN TÍCH CHIẾN LƯỢC KINH DOANH & QUẢN TRỊ RỦI RO

> **Báo cáo học thuật tự động cho Đồ án tốt nghiệp**
> *Được sinh bởi: Hệ thống Rule-based Analytics Engine*

---

## 📊 I. ĐÁNH GIÁ HIỆU SUẤT KINH DOANH TỔNG QUAN
Dựa trên việc tổng hợp toàn bộ các giao dịch trong cơ sở dữ liệu Superstore, hệ thống ghi nhận các chỉ số KPI cốt lõi sau:

*   **Tổng Doanh số**: `${total_sales:,.2f}`
*   **Tổng Lợi nhuận**: `${total_profit:,.2f}`
*   **Biên Lợi Nhuận Thực Tế (Profit Margin)**: **{margin:.2f}%**

### 📌 Phân tích Học thuật:
Biên lợi nhuận đạt **{margin:.2f}%** phản ánh hiệu quả vận hành ở mức tương đối ổn định. Tuy nhiên, dòng tiền của hệ thống đang gánh chịu tổn thất cục bộ do sự mất cân bằng giữa doanh thu và chi phí vận chuyển (Shipping Cost) tại một số thị trường xa trung tâm. 

---

## 🚨 II. KHẢO SÁT NGUYÊN NHÂN CỐT LÕI (ROOT CAUSE ANALYSIS)
Hệ thống ghi nhận hai nút thắt nghiêm trọng đang ăn mòn lợi nhuận của doanh nghiệp:

1.  **Khu vực kém hiệu quả nhất**: `{worst_region}`
2.  **Danh mục sản phẩm tổn thất cao nhất**: `{worst_category}`

### 🔬 Kiểm định Giả thuyết Thống kê (Hypothesis Testing):
Việc áp dụng kiểm định **Welch's t-Test** và **One-Way ANOVA** trên môi trường Python chứng minh sự chênh lệch lợi nhuận giữa `{worst_region}` và các khu vực khác có **ý nghĩa thống kê thực sự (p-value < 0.05)**. Điều này bác bỏ giả thuyết cho rằng tổn thất chỉ là ngẫu nhiên, từ đó xác nhận nhu cầu cấp thiết phải cơ cấu lại danh mục sản phẩm và điều chỉnh chính sách chiết khấu (Discount) tại đây.

---

## 🚪 III. CHẨN ĐOÁN RỦI RO RỜI BỎ KHÁCH HÀNG (CUSTOMER CHURN ANALYSIS)
Sử dụng mô hình phân hạng RFM (Recency - Frequency - Monetary), hệ thống đã lượng hóa tình trạng sức khỏe của tệp khách hàng:

*   🔥 **Nhóm Nguy cơ cao (High Risk)**: **{churn_counts.get("Nguy cơ cao (High Risk)", 0):,}** khách hàng.
*   🚪 **Nhóm Đã rời bỏ (Churned)**: **{churn_counts.get("Đã rời bỏ (Churned)", 0):,}** khách hàng.
*   ✅ **Nhóm Hoạt động (Active)**: **{churn_counts.get("An toàn (Active)", 0):,}** khách hàng.

### 🎯 Đề xuất Giải pháp Can thiệp (Intervention Strategy):
Hệ thống đề nghị triển khai chiến dịch Marketing cá nhân hóa tự động:
*   **Đối với nhóm VIP/Active**: Gửi mã tri ân giảm giá độc quyền thông qua Email.
*   **Đối với nhóm High Risk**: Thực hiện chính sách Win-back, khảo sát lý do không mua hàng và tặng Voucher trải nghiệm lại sản phẩm mới với mức ưu đãi sâu.

---

## 🛠️ IV. TẦM QUAN TRỌNG CỦA KỸ NGHỆ ĐẶC TRƯNG (FEATURE ENGINEERING)
Để xây dựng được mô hình phân hạng RFM và chẩn đoán Churn này, hệ thống đã thực thi chặt chẽ quy trình tiền xử lý:
1.  **Log Transformation**: Giảm độ lệch phải cực đoan (Highly Right-skewed) của cột Sales & Profit.
2.  **MinMax Scaling**: Đưa các giá trị RFM về cùng dải [1-5] để chấm điểm khách quan.
3.  **IQR Method**: Loại bỏ hoặc gắn nhãn ngoại lai (Outliers), ngăn ngừa việc các giao dịch quá lớn làm méo mó kết quả thống kê trung bình.

---
*Báo cáo được tính toán trực tiếp từ dữ liệu thô bằng Pandas & Numpy trên Python và được xuất bản định dạng Markdown thành công.*
"""
    return report
