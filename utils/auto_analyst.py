import os
import pandas as pd
import streamlit as st
from langchain_groq import ChatGroq
from dotenv import load_dotenv

def compute_dataset_metadata(df):
    """
    Trích xuất thông tin cấu trúc và thống kê tóm tắt của dataset một cách nhanh chóng.
    Sử dụng thuật toán nhận diện cột tự động để hỗ trợ mọi miền dữ liệu (HR, Tài chính, Bán lẻ...).
    """
    from utils.data_processor import detect_standard_columns
    col_map = detect_standard_columns(df)
    
    sales_col = col_map['Sales']
    profit_col = col_map['Profit']
    cust_col = col_map['Customer ID']
    date_col = col_map['Order Date']
    
    metadata = {}
    metadata['rows'] = int(df.shape[0])
    metadata['cols'] = int(df.shape[1])
    metadata['columns'] = list(df.columns)
    
    # Đếm số lượng giá trị khuyết thiếu (nếu có)
    missing = df.isnull().sum()
    metadata['missing_values'] = {k: int(v) for k, v in missing.items() if v > 0}
    
    # Tính các đại lượng thống kê cơ bản dựa trên các cột được tự động nhận dạng
    if sales_col:
        metadata['detected_value_column'] = sales_col
        metadata['total_value'] = float(df[sales_col].sum())
        metadata['avg_value'] = float(df[sales_col].mean())
        # Tìm cột phân loại (Category/Group)
        category_candidates = ['Category', 'category', 'Segment', 'segment', 'Product', 'product', 'Department', 'department', 'Group', 'group', 'Ngành hàng', 'ngành hàng', 'Type', 'type']
        cat_col = None
        for c in category_candidates:
            if c in df.columns:
                cat_col = c
                break
        if not cat_col:
            # Lấy cột kiểu Object/String đầu tiên có ít nhóm duy nhất (phù hợp làm phân loại)
            obj_cols = df.select_dtypes(include=['object']).columns
            for c in obj_cols:
                try:
                    if df[c].nunique() < 20:
                        cat_col = c
                        break
                except Exception:
                    pass
        if cat_col:
            metadata['classification_column'] = cat_col
            try:
                metadata['top_categories'] = df.groupby(cat_col)[sales_col].sum().sort_values(ascending=False).head(3).to_dict()
            except Exception:
                pass
    
    if profit_col and sales_col:
        try:
            metadata['detected_profit_column'] = profit_col
            metadata['total_profit'] = float(df[profit_col].sum())
            metadata['profit_margin'] = float((df[profit_col].sum() / df[sales_col].sum()) * 100) if df[sales_col].sum() > 0 else 0.0
        except Exception:
            pass
    
    if cust_col:
        try:
            metadata['detected_entity_column'] = cust_col
            metadata['unique_entities'] = int(df[cust_col].nunique())
        except Exception:
            pass
        
    if date_col:
        metadata['detected_date_column'] = date_col
        
    return metadata

@st.cache_data(show_spinner=False)
def generate_cached_ai_report(metadata_str):
    """
    Gọi LLM Llama-3.3-70b để tạo báo cáo chẩn đoán và nhận định dữ liệu tự động dựa trên metadata chuỗi.
    """
    load_dotenv(override=True)
    try:
        api_key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY"))
    except Exception:
        api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key or api_key == "your_google_api_key_here":
        return "⚠️ Không tìm thấy API Key hoặc API Key không hợp lệ. Vui lòng kiểm tra lại file `.env`."
        
    try:
        llm = ChatGroq(
            model_name="llama-3.3-70b-versatile", 
            api_key=api_key, 
            temperature=0.3
        )
        
        prompt = f"""
        Bạn là một Chuyên gia Khoa học Dữ liệu (Data Scientist) và Chuyên viên Phân tích Kinh doanh (Business Intelligence Analyst) cấp cao.
        Dưới đây là thông tin chẩn đoán thống kê sơ bộ của tập dữ liệu mới tải lên:
        {metadata_str}
        
        Nhiệm vụ của bạn là viết một Báo cáo Chẩn đoán Dữ liệu & Nhận định Kinh doanh Tự động (Automated Dataset Diagnostic Report) bằng tiếng Việt cực kỳ chuyên nghiệp, sâu sắc và rành mạch.
        Hãy phân tích cấu trúc dữ liệu và số liệu thống kê sơ bộ trên, rồi trình bày báo cáo theo các cấu trúc cụ thể sau:

        1. **📊 Đánh Giá Chất Lượng Dữ Liệu (Data Quality Assessment):**
           - Nhận định về kích thước dataset (số dòng, số cột) và mức độ đầy đủ của dữ liệu (các trường khuyết thiếu).
           - Đánh giá sự phân bổ và cấu trúc cột xem đã chuẩn hóa và sẵn sàng cho phân tích sâu hay chưa.

        2. **💡 Nhận Định Phân Tích Nổi Bật (Key Business & Data Insights):**
           - Phân tích hiệu quả hoạt động dựa trên các chỉ số chính được tự động nhận diện (như Tổng số lượng, Tổng giá trị, Tỷ suất nếu có) của tập dữ liệu.
           - Nhận định về các nhóm phân loại (Category/Group) đóng góp giá trị hàng đầu và các yếu tố hoạt động hiệu quả nhất.

        3. **🚀 Khuyến Nghị Chiến Lược (Strategic Recommendations):**
           - Đưa ra ít nhất 3 đề xuất chiến lược cụ thể, thực tế và có chiều sâu dựa trên số liệu phân tích của tập dữ liệu này để tăng trưởng hiệu quả hoạt động, tối ưu hóa quy trình hoặc cải thiện chất lượng quản lý.

        **Yêu cầu phong cách trình bày:**
        - Tự động điều chỉnh thuật ngữ phân tích phù hợp với miền dữ liệu của tệp tải lên (ví dụ: nếu là dữ liệu bán hàng thì dùng Doanh thu/Khách hàng, nếu là Nhân sự thì dùng Nhân viên/Phòng ban, nếu là Kho vận thì dùng Hàng hóa/Kho...).
        - Sử dụng các biểu tượng emoji phù hợp ở mỗi đầu mục để tạo tính trực quan sinh động.
        - Giọng văn chuyên nghiệp, lập luận sắc bén, súc tích, đi thẳng vào bản chất của số liệu.
        - Trình bày dạng Markdown sạch sẽ, sử dụng bảng hoặc danh sách bullet points để người dùng dễ theo dõi nhất.
        """
        
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"❌ Đã xảy ra lỗi trong quá trình tạo báo cáo AI: {str(e)}"

@st.cache_data(show_spinner=False, hash_funcs={pd.DataFrame: lambda d: f"{d.shape[0]}_{d.shape[1]}_{d.columns.tolist()}"})
def get_automated_dataset_report(df):
    """
    Hàm giao tiếp chính để tính toán metadata và sinh báo cáo tự động (có cache).
    Sử dụng cơ chế hash tùy chỉnh cực nhẹ giúp không bị giật lag khi rerun trang.
    """
    metadata = compute_dataset_metadata(df)
    # Chuyển đổi metadata thành chuỗi dạng JSON hoặc string để có thể băm (hash) làm khóa cache cho Streamlit
    metadata_str = str(sorted(metadata.items()))
    return generate_cached_ai_report(metadata_str)
