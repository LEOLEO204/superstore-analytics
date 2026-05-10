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
    
    if not api_key or api_key == "your_google_api_key_here":
        return None
        
    try:
        llm = ChatGroq(
            model_name="llama-3.3-70b-versatile", 
            api_key=api_key, 
            temperature=0.2
        )
        
        PREFIX = f"""
        Bạn là Trợ lý AI của siêu thị Superstore. Bạn đang được cấp 2 DataFrame: 
        1. df1: Transactions {df.shape}. 2. df2: Customer RFM {rfm_df.shape}.
        
        NẾU câu hỏi CHỈ LÀ giải thích khái niệm hoặc chào hỏi (KHÔNG cần tính toán số liệu), hãy trả lời thẳng mà KHÔNG dùng python.
        Hãy thân thiện xưng Em, trả lời chuyên sâu và tập trung vào phân tích kinh doanh.
        """
        
        # Trả về cả LLM và Agent để hệ thống có thể lựa chọn Routing thông minh ở dưới
        agent = create_pandas_dataframe_agent(
            llm, 
            [df, rfm_df], 
            verbose=False, 
            allow_dangerous_code=True,
            prefix=PREFIX,
            agent_type="tool-calling",
            handle_parsing_errors=True,
            max_iterations=2, # Giảm số vòng lặp để tối đa hóa tốc độ
            max_execution_time=5 # Chặn đứng hiện tượng treo sau 5 giây
        )
        # Đính kèm raw LLM vào agent object để sử dụng trong ask_agent nếu cần Routing
        setattr(agent, 'raw_llm', llm)
        return agent
    except Exception as e:
        print(f"Agent Init Err: {e}")
        return None

def ask_agent(agent, prompt):
    """
    Hàm xử lý định tuyến thông minh (Router): 
    - Nếu là câu hỏi lý thuyết/giải thích -> Trả lời bằng LLM gốc (Cực nhanh, 0.5 giây)
    - Nếu là câu hỏi dữ liệu -> Gọi Pandas Agent (Tốn 3-5 giây)
    """
    try:
        query_lower = prompt.lower()
        # TẬP TRUNG TỐI ƯU TỐC ĐỘ: Nhận diện từ khóa lý thuyết
        is_theory = any(kw in query_lower for kw in [
            "là gì", "thế nào", "giải thích", "lợi ích", "giúp ích", "tại sao", "xin chào", "hello", "chào em"
        ])
        
        # EXPRESS ROUTE: Trả lời lý thuyết siêu tốc
        if is_theory and hasattr(agent, 'raw_llm'):
            response = agent.raw_llm.invoke(prompt)
            return response.content

        # ROUTE DỮ LIỆU: Phân tích số liệu bằng Agent
        # Tối ưu hóa: Ép kiểu timeout để đảm bảo không bao giờ treo 2 phút
        response = agent.invoke({"input": prompt})
        return response["output"]
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            return t("ai_overloaded")
        if "OUTPUT_PARSING_FAILURE" in error_str:
            parts = error_str.split("`")
            return parts[1] if len(parts) > 1 else str(e)
        # Nếu Agent lỗi, hãy thử fallback lần cuối bằng Raw LLM thay vì báo lỗi chết
        if hasattr(agent, 'raw_llm'):
            try:
                return agent.raw_llm.invoke(prompt).content
            except:
                pass
        return f"{t('ai_error')} {e}"
