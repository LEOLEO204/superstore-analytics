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
        
        agent = create_pandas_dataframe_agent(
            llm, 
            [df, rfm_df], 
            verbose=False, 
            allow_dangerous_code=True,
            prefix=PREFIX,
            agent_type="tool-calling",
            max_iterations=2,
            max_execution_time=5
        )
        # KHÔNG ĐƯỢC DÙNG setattr vì agent là Pydantic Model cấm gán cứng
        return agent
    except Exception as e:
        print(f"Agent Init Err: {e}")
        return None

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
