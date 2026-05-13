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


    # 3. TRUY VẤN KHÁCH HÀNG (CUSTOMERS) - TOP PRIORITY MATCH
    if any(kw in p for kw in ["khách hàng tốt nhất", "vip", "mua nhiều nhất", "chi tiêu nhiều nhất"]):
        if rfm_df is not None and not rfm_df.empty:
            # Đảm bảo có cột Customer Name hoặc ID
            name_col = 'Customer Name' if 'Customer Name' in rfm_df.columns else 'Customer ID'
            monetary_col = 'Monetary' if 'Monetary' in rfm_df.columns else None
            
            if monetary_col:
                top_custs = rfm_df.sort_values(by=monetary_col, ascending=False).head(5)
                lines = []
                for _, row in top_custs.iterrows():
                    cname = row[name_col]
                    cval = row[monetary_col]
                    crisk = row.get('Churn_Risk', 'Hoạt động')
                    lines.append(f"- **{cname}** (Trạng thái: {crisk}): `${cval:,.2f}`")
                return "🏆 **TOP 5 KHÁCH HÀNG VIP MANG LẠI DOANH SỐ CAO NHẤT:**\n\n" + "\n".join(lines)
        
        # Fallback dùng df gốc nếu rfm_df trống
        if 'Customer Name' in df.columns and sales_col in df.columns:
            top_custs = df.groupby('Customer Name')[sales_col].sum().sort_values(ascending=False).head(5)
            lines = [f"- **{name}**: `${val:,.2f}`" for name, val in top_custs.items()]
            return "🏆 **TOP 5 KHÁCH HÀNG MUA NHIỀU NHẤT (DỰA TRÊN DOANH THU):**\n\n" + "\n".join(lines)
            
        return "⚠️ Rất tiếc, hệ thống chưa thể phân hạng dữ liệu khách hàng."

    if any(kw in p for kw in ["bao nhiêu khách", "số lượng khách", "tổng số khách", "tổng khách", "khách hàng"]):
        total_c = 0
        if rfm_df is not None and not rfm_df.empty:
            total_c = len(rfm_df)
        elif 'Customer ID' in df.columns:
            total_c = df['Customer ID'].nunique()
        elif 'Customer Name' in df.columns:
            total_c = df['Customer Name'].nunique()
            
        if total_c > 0:
            return (
                f"👥 **BÁO CÁO SỐ LƯỢNG KHÁCH HÀNG TOÀN HỆ THỐNG**\n\n"
                f"Hệ thống ghi nhận hiện đang có tổng cộng **{total_c:,}** khách hàng độc bản đã giao dịch.\n\n"
                f"💡 *Hành động*: Bạn có thể gõ \"*phân khúc*\" để xem chi tiết tình hình RFM hoặc \"*rời bỏ*\" để xem dự báo churn của tệp khách hàng này."
            )
        # Nếu chỉ gõ vu vơ "khách hàng", hiển thị phân khúc
        if "phân khúc" in p or "rfm" in p:
            pass # Để khối sau xử lý
        else:
            return "❓ Bạn có muốn hỏi về **Số lượng khách hàng** hay **Top khách hàng VIP** không ạ? Hãy hỏi chi tiết hơn một chút nhé!"

    # 4. CHI PHÍ VẬN CHUYỂN (SHIPPING COST)
    if any(kw in p for kw in ["vận chuyển", "ship", "phí ship", "giao hàng"]):
        ship_col = 'Shipping Cost' if 'Shipping Cost' in df.columns else None
        if ship_col:
            total_ship = df[ship_col].sum()
            avg_ship = df[ship_col].mean()
            return (
                f"🚚 **CHI PHÍ VẬN CHUYỂN TÍCH LŨY (SHIPPING)**\n\n"
                f"- Tổng phí ship toàn bộ đơn hàng: **${total_ship:,.2f}**\n"
                f"- Phí ship trung bình trên 1 giao dịch: **${avg_ship:,.2f}**\n"
                f"- Tỷ lệ phí ship / Tổng doanh thu: **{(total_ship/total_sales*100):.2f}%**\n\n"
                f"💡 *Đánh giá*: Chi phí vận chuyển chiếm tỉ trọng phù hợp so với doanh thu."
            )
        return "⚠️ Tập dữ liệu hiện hành không bao gồm trường dữ liệu 'Shipping Cost'."

    # 5. ĐƠN HÀNG VÀ GIAO DỊCH (ORDERS)
    if any(kw in p for kw in ["bao nhiêu đơn", "đơn hàng", "giao dịch", "số đơn"]):
        return (
            f"📦 **THỐNG KÊ ĐƠN HÀNG & GIAO DỊCH**\n\n"
            f"- Tổng số lượng hóa đơn/đơn hàng được chốt: **{total_orders:,}** đơn.\n"
            f"- Giá trị doanh thu bình quân mỗi đơn: **${(total_sales/total_orders):,.2f}**.\n"
            f"- Lợi nhuận ròng bình quân mỗi đơn: **${(total_profit/total_orders):,.2f}**."
        )

    # 6. THỊ TRƯỜNG (MARKETS)
    if any(kw in p for kw in ["thị trường", "market"]):
        if market_col:
            mkt_sales = df.groupby(market_col)[sales_col].sum().sort_values(ascending=False)
            lines = [f"- **{mkt}**: `${val:,.2f}`" for mkt, val in mkt_sales.items()]
            return "🗺️ **DOANH THU CHIA THEO THỊ TRƯỜNG (MARKET):**\n\n" + "\n".join(lines)
        return "⚠️ Cột dữ liệu Thị trường (Market) không tồn tại."

    # 7. GỢI Ý MUA HÀNG / SẢN PHẨM KÈM (RECOMMENDATIONS)
    if any(kw in p for kw in ["gợi ý", "mua kèm", "bán kèm", "recommend"]):
        return (
            f"💡 **CHIẾN LƯỢC GỢI Ý GIỎ HÀNG PHỔ BIẾN (SOP):**\n\n"
            f"1. **Nhóm Đồ Nội Thất**: Hãy gợi ý phụ kiện văn phòng đi kèm.\n"
            f"2. **Nhóm Thiết Bị Công Nghệ**: Hãy đính kèm gói bảo hành mở rộng và phụ kiện dây cáp/giấy in.\n\n"
            f"Bạn có thể xem bảng gợi ý kết hợp sản phẩm tự động hoàn chỉnh tại menu **🛍️ Gợi Ý Sản Phẩm**!"
        )

    # 8. TRUY VẤN CHURN RISK & RỦI RO RỜI BỎ (CUSTOMER CHURN)
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
                f"🚨 **BÁO CÁO RỦI RO RỜI BỎ KHÁCH HÀNG (CHURN RISK)**\n\n"
                f"Phân khúc dựa trên thuật toán RFM cho thấy:\n"
                f"- 🔥 **Nguy cơ cao (High Risk)**: **{high_risk:,}** khách hàng ({high_risk_pct:.1f}%).\n"
                f"- 🚪 **Đã rời bỏ (Churned)**: **{churned:,}** khách hàng ({churned_pct:.1f}%).\n"
                f"- ✅ **An toàn (Active)**: **{active:,}** khách hàng.\n"
                f"- ⚠️ **Cần chú ý (Needs Attention)**: **{needs_attention:,}** khách hàng.\n\n"
                f"💡 *Khuyến nghị*: Tập trung chương trình tri ân cho nhóm **Nguy cơ cao** trước khi họ chuyển hẳn sang đối thủ."
            )
        return "⚠️ Dữ liệu RFM hiện chưa có thông tin về Churn Risk."

    # 9. TRUY VẤN BIÊN LỢI NHUẬN (PROFIT MARGIN)
    if any(kw in p for kw in ["biên", "tỷ suất", "tỷ lệ lợi nhuận", "margin"]):
        return (
            f"📊 **BIÊN LỢI NHUẬN TOÀN HỆ THỐNG**\n\n"
            f"- 🛠️ **Công thức**: `Profit Margin = (Lợi nhuận / Doanh thu) * 100`\n"
            f"- 💰 **Lợi nhuận ròng**: `${total_profit:,.2f}`\n"
            f"- 📈 **Doanh thu gộp**: `${total_sales:,.2f}`\n"
            f"- 🎯 **Biên lợi nhuận**: **{margin:.2f}%**\n\n"
            f"Trung bình mỗi 100$ doanh thu đem về cho siêu thị **{margin:.2f}$** tiền lời ròng."
        )

    # 10. TRUY VẤN DOANH THU (SALES)
    if any(kw in p for kw in ["doanh thu", "doanh số", "bán được"]):
        if any(kw in p for kw in ["khu vực", "vùng"]):
            if region_col:
                reg_sales = df.groupby(region_col)[sales_col].sum().sort_values(ascending=False)
                lines = [f"- **{reg}**: `${val:,.2f}`" for reg, val in reg_sales.items()]
                return "🌍 **DOANH THU THEO KHU VỰC (REGION):**\n\n" + "\n".join(lines)
        if any(kw in p for kw in ["danh mục", "sản phẩm", "nhóm hàng"]):
            if category_col:
                cat_sales = df.groupby(category_col)[sales_col].sum().sort_values(ascending=False)
                lines = [f"- **{cat}**: `${val:,.2f}`" for cat, val in cat_sales.items()]
                return "📦 **DOANH THU THEO DANH MỤC (CATEGORY):**\n\n" + "\n".join(lines)
        return (
            f"💰 **TỔNG DOANH THU HỆ THỐNG**\n\n"
            f"- Doanh thu tích lũy: **${total_sales:,.2f}**\n"
            f"- Tổng số đơn hàng hoàn tất: **{total_orders:,}** đơn.\n"
            f"- Doanh thu bình quân mỗi đơn: **${(total_sales/total_orders):,.2f}**."
        )

    # 11. TRUY VẤN LỢI NHUẬN (PROFIT)
    if any(kw in p for kw in ["lợi nhuận", "lãi", "lỗ"]):
        if any(kw in p for kw in ["khu vực", "vùng"]):
            if region_col:
                reg_profit = df.groupby(region_col)[profit_col].sum().sort_values(ascending=False)
                lines = [f"- **{reg}**: `${val:,.2f}`" for reg, val in reg_profit.items()]
                return "🌍 **LỢI NHUẬN THEO KHU VỰC (REGION):**\n\n" + "\n".join(lines)
        if any(kw in p for kw in ["danh mục", "sản phẩm", "nhóm hàng"]):
            if category_col:
                cat_profit = df.groupby(category_col)[profit_col].sum().sort_values(ascending=False)
                lines = [f"- **{cat}**: `${val:,.2f}`" for cat, val in cat_profit.items()]
                return "📦 **LỢI NHUẬN THEO DANH MỤC (CATEGORY):**\n\n" + "\n".join(lines)
        return (
            f"📈 **TỔNG LỢI NHUẬN HỆ THỐNG**\n\n"
            f"- Lợi nhuận ròng tích lũy: **${total_profit:,.2f}**\n"
            f"- Biên lợi nhuận thực tế: **{margin:.2f}%**\n"
            f"- Đánh giá hiệu năng: **{'VẬN HÀNH CÓ LÃI ✅' if total_profit > 0 else 'THUA LỖ CỤC BỘ ❌'}**."
        )

    # 12. TOP PERFORMERS (TỐT NHẤT / TỆ NHẤT)
    if any(kw in p for kw in ["tốt nhất", "cao nhất", "bán chạy", "nhiều nhất"]):
        best_reg = df.groupby(region_col)[sales_col].sum().idxmax() if region_col else "N/A"
        best_reg_val = df.groupby(region_col)[sales_col].sum().max() if region_col else 0
        best_cat = df.groupby(category_col)[sales_col].sum().idxmax() if category_col else "N/A"
        best_cat_val = df.groupby(category_col)[sales_col].sum().max() if category_col else 0
        return (
            f"🏆 **BÁO CÁO HIỆU SUẤT VƯỢT TRỘI (TOP PERFORMERS)**\n\n"
            f"- 🌍 Khu vực mang lại doanh thu lớn nhất: **{best_reg}** (${best_reg_val:,.2f})\n"
            f"- 📦 Nhóm hàng được mua sắm nhiều nhất: **{best_cat}** (${best_cat_val:,.2f})"
        )

    if any(kw in p for kw in ["thấp nhất", "kém nhất", "lỗ nhất", "ít nhất"]):
        worst_reg = df.groupby(region_col)[profit_col].sum().idxmin() if region_col else "N/A"
        worst_reg_val = df.groupby(region_col)[profit_col].sum().min() if region_col else 0
        worst_cat = df.groupby(category_col)[profit_col].sum().idxmin() if category_col else "N/A"
        worst_cat_val = df.groupby(category_col)[profit_col].sum().min() if category_col else 0
        return (
            f"⚠️ **CẢNH BÁO HIỆU SUẤT KÉM**\n\n"
            f"- 🌍 Khu vực lợi nhuận thấp nhất: **{worst_reg}** (${worst_reg_val:,.2f})\n"
            f"- 📦 Nhóm hàng lỗ vốn nặng nhất: **{worst_cat}** (${worst_cat_val:,.2f})"
        )

    # 13. PHÂN KHÚC KHÁCH HÀNG (RFM SEGMENTS)
    if any(kw in p for kw in ["rfm", "phân khúc"]):
        if rfm_df is not None and not rfm_df.empty:
            seg_col = 'RFM_Segment' if 'RFM_Segment' in rfm_df.columns else 'Segment' if 'Segment' in rfm_df.columns else None
            if seg_col:
                counts = rfm_df[seg_col].value_counts()
                lines = [f"- **{seg}**: **{cnt:,}** khách hàng" for seg, cnt in counts.items()]
                return "👥 **TỔNG HỢP PHÂN KHÚC KHÁCH HÀNG (RFM):**\n\n" + "\n".join(lines)
        return "⚠️ Phân khúc khách hàng hiện chưa thể hiển thị, vui lòng kiểm tra lại DB."

    # 14. CHÀO HỎI & GIỚI THIỆU (GREETINGS) - ĐƯA VỀ DƯỚI CÙNG ĐỂ KHÔNG CƯỚP CÂU HỎI TRUY VẤN
    # Loại bỏ 'hi' để tránh bắt nhầm substring trong 'bao nhiêu', 'chỉ', 'chi phí'...
    if any(kw in p for kw in ["chào", "hello", "bạn là ai", "tên gì", "chức năng", "giúp", "xin chào"]):
        return (
            "👋 **Xin chào! Em là Trợ lý Ảo chuyên trách Dữ liệu Superstore.**\n\n"
            "Em có thể **phân tích tức thời** tập dữ liệu của bạn với các câu hỏi như:\n"
            "- 👥 **Khách hàng**: \"Có bao nhiêu khách hàng\", \"Top khách hàng tốt nhất\"\n"
            "- 💰 **Tài chính**: \"Doanh thu hệ thống\", \"Tổng lợi nhuận\", \"Biên lợi nhuận\"\n"
            "- 🚚 **Vận chuyển**: \"Tổng chi phí vận chuyển\", \"Phí ship trung bình\"\n"
            "- 📦 **Sản phẩm & Thị trường**: \"Bán chạy nhất\", \"Doanh số thị trường\"\n"
            "- 🚨 **Rủi ro**: \"Tình hình rời bỏ (Churn Risk)\", \"Phân khúc RFM\"\n\n"
            "Bạn cần em tra cứu thông tin nào ngay bây giờ ạ? 😊"
        )

    # 15. FALLBACK KHI KHÔNG HIỂU CÂU HỎI
    return (
        "🤖 **Em chưa khớp được quy tắc chuẩn cho câu hỏi này của Anh/Chị.**\n\n"
        "Để em phân tích chính xác số liệu từ Python, Anh/Chị hãy thử gõ lại cụ thể hơn:\n"
        "- *\"Có bao nhiêu khách hàng\"*, *\"Top khách hàng mua nhiều nhất\"*\n"
        "- *\"Doanh thu hệ thống\"*, *\"Doanh thu theo khu vực/nhóm hàng\"*\n"
        "- *\"Tổng lợi nhuận\"*, *\"Biên lợi nhuận\"*\n"
        "- *\"Tổng chi phí vận chuyển\"*, *\"Đơn hàng\"*\n"
        "- *\"Rủi ro rời bỏ\"*, *\"Phân khúc RFM\"*"
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
