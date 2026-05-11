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
        BẠN LÀ CHUYÊN GIA PHÂN TÍCH DỮ LIỆU CẤP CAO (Senior AI Data Analyst) của Superstore.
        Bạn sở hữu quyền truy cập TUYỆT ĐỐI vào toàn bộ cơ sở dữ liệu thực tế sau đây:
        - `df1`: Dữ liệu giao dịch gốc {df.shape} (Bao gồm Sales, Profit, Order Date, Region...).
        - `df2`: Dữ liệu phân tích RFM khách hàng {rfm_df.shape} (Bao gồm Recency, Frequency, Monetary, Churn Risk...).

        QUY TẮC VẬN HÀNH CỐT LÕI (BẮT BUỘC):
        1. PHẢI TRẢ LỜI TOÀN BỘ DỰA TRÊN DATASET: Khi người dùng hỏi về số liệu, BẠN PHẢI viết code Python để quét TOÀN BỘ dataset, tính toán và đưa ra số liệu chính xác 100% (Không đoán, không bịa số liệu).
        2. KHẢ NĂNG HỌC HỎI (LEARNING FROM HISTORY): Luôn đọc kỹ "Lịch sử hội thoại" được cung cấp ở đầu Prompt. Hãy coi những câu trả lời/câu hỏi trước đó như nguồn tri thức đã "train" cho bạn trong phiên làm việc này để thấu hiểu thói quen, sở thích và các yêu cầu nối tiếp của người dùng.
        3. XỬ LÝ LÝ THUYẾT: Nếu người dùng chỉ hỏi khái niệm (không cần tính toán), bạn trả lời thẳng thân thiện bằng giọng văn kinh tế.
        4. Xưng hô lễ phép: Xưng "Em", gọi người dùng là "Anh/Chị", trả lời chuyên nghiệp, sâu sắc và mang tính chiến lược kinh doanh cao.
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
        query_lower = prompt.lower()
        is_theory = any(kw in query_lower for kw in [
            "là gì", "thế nào", "giải thích", "lợi ích", "giúp ích", "tại sao", "xin chào", "hello", "chào em"
        ])
        
        # ROUTE 1: Lý thuyết -> Raw LLM (0.5 giây)
        if is_theory and fallback_llm:
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
