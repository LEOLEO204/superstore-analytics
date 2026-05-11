import pandas as pd
import os
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# Load local dataset that matches user's numbers
df = pd.read_csv('data/superstore (1).csv', sep=';', encoding='latin1')
df_rfm = pd.DataFrame({'test': [1, 2, 3]}) # dummy RFM

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile", 
    api_key=os.getenv("GROQ_API_KEY"), 
    temperature=0.2
)

PREFIX = """
BẠN LÀ MỘT CÔNG CỤ KẾ TOÁN KHÔNG CÓ BỘ NHỚ.
BẮT BUỘC:
1. BẠN PHẢI DÙNG CÔNG CỤ PYTHON ĐỂ TÍNH TOÁN.
2. BẮT BUỘC DÙNG BIẾN CÓ SẴN: Chỉ được phép dùng `df1` (Dữ liệu giao dịch) và `df2` (Dữ liệu RFM) ĐÃ CÓ SẴN trong bộ nhớ của bạn.
3. CẤM TUYỆT ĐỐI: Cấm tạo bảng dữ liệu mới (Cấm dùng lệnh `pd.DataFrame(...)`). Nếu bạn tạo bảng mới, bạn sẽ bị phạt.
4. CẤM HIỂN THỊ MÃ CODE.
"""

agent = create_pandas_dataframe_agent(
    llm, 
    [df, df_rfm], 
    verbose=True, 
    allow_dangerous_code=True,
    prefix=PREFIX,
    agent_type="tool-calling",
    max_iterations=4,
    max_execution_time=15
)

print("\n--- RUNNING AGENT DIAGNOSTIC ---\n")
resp = agent.invoke({"input": "tổng doanh thu là bao nhiêu"})
print("\n--- FINAL RESPONSE ---\n")
print(resp)
