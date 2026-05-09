import os
# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_groq import ChatGroq
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from utils.i18n import t

@st.cache_resource
def get_ai_agent(df, rfm_df):
    load_dotenv(override=True)
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key or api_key == "your_google_api_key_here":
        return None
        
    try:
        llm = ChatGroq(
            model_name="llama-3.3-70b-versatile", 
            api_key=api_key, 
            temperature=0
        )
        
        PREFIX = f"""
        Bạn là Trợ lý AI thông minh của chuỗi siêu thị Superstore.
        Bạn đang được cung cấp 2 Dataframes:
        1. df1: Giao dịch chi tiết (Transactions). Kích thước (số dòng, số cột): {df.shape}, Các cột: {list(df.columns)}
        2. df2: Phân tích khách hàng (RFM). Kích thước: {rfm_df.shape}, Các cột: {list(rfm_df.columns)}
        
        MẸO TỐI ƯU TỐC ĐỘ: NẾU câu hỏi của người dùng đơn giản (ví dụ: "có bao nhiêu dữ liệu", "có bao nhiêu dòng", "dữ liệu gồm những gì"), HÃY TRẢ LỜI NGAY LẬP TỨC dựa vào Kích thước và Các cột được cung cấp ở trên mà KHÔNG CẦN gọi công cụ Python.
        Chỉ dùng Python tool khi cần tính toán phức tạp (tổng, trung bình, đếm điều kiện...).
        Nhiệm vụ của bạn là đưa ra các nhận định sắc bén về tình hình kinh doanh, trả lời niềm nở, thân thiện và tự nhiên nhưng tránh rườm rà thừa thãi. Hãy đi thẳng vào nội dung chính, cung cấp phân tích có chiều sâu thay vì chỉ liệt kê số liệu cộc lốc, và tuyệt đối không lặp lại câu chào hay câu chúc xã giao dập khuôn ở mỗi câu trả lời.
        Luôn xưng hô "Em" và gọi người dùng là "Anh/Chị".
        """
        
        agent = create_pandas_dataframe_agent(
            llm, 
            [df, rfm_df], 
            verbose=True, 
            allow_dangerous_code=True,
            prefix=PREFIX,
            agent_type="tool-calling",
            handle_parsing_errors=True,
            max_iterations=3,
            max_execution_time=8
        )
        return agent
    except Exception as e:
        print(f"Agent Initialization Error: {e}")
        return None

def ask_agent(agent, prompt):
    try:
        response = agent.invoke({"input": prompt})
        return response["output"]
    except Exception as e:
        error_str = str(e)
        # Bắt lỗi 429 Quota Exceeded (Hết hạn mức API)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            return t("ai_overloaded")
            
        if "OUTPUT_PARSING_FAILURE" in error_str:
            parts = error_str.split("`")
            if len(parts) > 1:
                return parts[1]
        return f"{t('ai_error')} {e}"
