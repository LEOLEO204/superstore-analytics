import os
# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_groq import ChatGroq
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from utils.i18n import t

# Hủy bỏ st.cache_resource vì việc băm (hash) DataFrame kích thước lớn của Streamlit gây đơ trình duyệt cực kỳ lâu.
# Việc khởi tạo Agent chỉ tốn <0.1s, rẻ hơn hàng nghìn lần so với việc Hash cache!
def get_ai_agent(df, rfm_df):
    load_dotenv(override=True)
    try:
        api_key = st.session_state.get("USER_GROQ_KEY")
        if not api_key:
            api_key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY"))
    except Exception:
        api_key = os.environ.get("GROQ_API_KEY")
    
    # Debug chẩn đoán nhanh không in ra giá trị bảo mật
    if not api_key or api_key == "your_google_api_key_here":
        # Liệt kê các keys hiện có trong Secrets để người dùng đối chiếu (KHÔNG IN GIÁ TRỊ KEY)
        existing_keys = list(st.secrets.keys()) if st.secrets else []
        raise ValueError(f"Không tìm thấy 'GROQ_API_KEY'. Các biến có trong Secrets hiện tại là: {existing_keys}")
        
    try:
        llm = ChatGroq(
            model_name="llama-3.3-70b-versatile", 
            api_key=api_key, 
            temperature=0.2
        )
        
        PREFIX = f"""
        BẠN LÀ MỘT CHUYÊN GIA KẾ TOÁN DỮ LIỆU VÀ CHỈ ĐƯỢC PHÉP NÓI SỰ THẬT.
        
        🔥 QUY TẮC SỐNG CÒN (CẤM VI PHẠM):
        1. BẮT BUỘC DÙNG DỮ LIỆU CÓ SẴN: Bạn chỉ được phép sử dụng 2 biến dataframe ĐÃ CÓ SẴN trong bộ nhớ là `df1` (Giao dịch - {df.shape}) và `df2` (RFM - {rfm_df.shape}).
        2. CẤM TUYỆT ĐỐI TẠO DỮ LIỆU GIẢ: Không bao giờ dùng lệnh `pd.DataFrame(...)` để tạo bảng mới. Bất kỳ hành vi tạo bảng dữ liệu giả nào để tính toán đều bị coi là SAI TRÁI.
        3. TÍNH TOÁN THỰC TẾ: Mọi con số thống kê PHẢI được tính bằng cách gọi công cụ Python trực tiếp trên `df1` hoặc `df2`. Không được tự suy diễn.
        4. CHỈ HIỂN THỊ KẾT QUẢ: Thực thi mã code NGẦM. Tuyệt đối CẤM hiển thị code Python ra màn hình chat. Hãy định dạng số liệu đẹp (Ví dụ: $1,234,567).
        5. Xưng hô: Xưng "Em", gọi "Anh/Chị" thân thiện và chuyên nghiệp.
        """
        
        agent = create_pandas_dataframe_agent(
            llm, 
            [df, rfm_df], 
            verbose=False, 
            allow_dangerous_code=True,
            prefix=PREFIX,
            agent_type="tool-calling",
            max_iterations=4, # Tăng số lần lặp để AI có thể suy nghĩ sâu hơn và sửa lỗi code nếu gặp lỗi
            max_execution_time=15 # Tăng thời gian để có đủ tài nguyên xử lý query phức tạp
        )
        return agent
    except Exception as e:
        # Thay vì trả về None (khiến UI báo nhầm là thiếu Key), hãy NÉM LỖI ra ngoài để UI báo cáo đúng nguyên nhân thật sự!
        raise RuntimeError(f"Lỗi khởi tạo LangChain Agent: {str(e)}")

def ask_agent(agent, prompt):
    """
    Router thông minh: Cấp cứu tức thời nếu Agent bị treo hoặc lỗi Pydantic.
    """
    # Khởi tạo nhanh Raw LLM để dự phòng khẩn cấp
    fallback_llm = None
    try:
        api_key = st.session_state.get("USER_GROQ_KEY")
        if not api_key:
            api_key = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY"))
        if api_key and api_key != "your_google_api_key_here":
            fallback_llm = ChatGroq(
                model_name="llama-3.3-70b-versatile", 
                api_key=api_key, 
                temperature=0.2
            )
    except:
        pass

    try:
        # CHỈ XÉT CÂU HỎI MỚI NHẤT ĐỂ PHÂN LOẠI (Tránh việc History chứa từ khóa "chào" làm sai lệch Router)
        raw_user_query = prompt # Mặc định
        try:
            if "chat_history" in st.session_state and len(st.session_state.chat_history) > 0:
                raw_user_query = st.session_state.chat_history[-1]["content"]
        except:
            pass
            
        query_lower = raw_user_query.lower()
        # Phân biệt lý thuyết thuần túy
        is_theory = any(kw in query_lower for kw in [
            "là gì", "thế nào", "giải thích", "định nghĩa", "là sao"
        ])
        # Cần kiểm tra xem trong câu có hỏi về số liệu không (Ưu tiên 1)
        has_data_keywords = any(kw in query_lower for kw in [
            "bao nhiêu", "mấy", "thống kê", "tổng", "số lượng", "trung bình", "tỷ lệ", "list", "danh sách"
        ])
        
        # ROUTE 1: Lý thuyết THUẦN TÚY (Không hề đả động đến số liệu) -> Raw LLM
        if is_theory and not has_data_keywords and fallback_llm:
            response = fallback_llm.invoke(prompt)
            return response.content
            
        # ROUTE 2: Nếu chỉ là chào hỏi ngắn gọn (Dưới 4 từ) -> Raw LLM cho nhanh
        if len(query_lower.split()) <= 3 and any(kw in query_lower for kw in ["chào", "hi", "hello"]) and fallback_llm:
             response = fallback_llm.invoke(prompt)
             return response.content

        # ROUTE 2: Phân tích số liệu -> Pandas Agent
        if agent is None and fallback_llm:
            # Cứu hộ nếu agent bị lỗi khởi tạo
            return fallback_llm.invoke(prompt).content
            
        response = agent.invoke({"input": prompt})
        return response["output"]
    except Exception as e:
        # ROUTE 3: Fallback cứu cánh cuối cùng
        if fallback_llm:
            try:
                res = fallback_llm.invoke(prompt)
                return res.content
            except:
                pass
        return f"{t('ai_error')} {e}"
