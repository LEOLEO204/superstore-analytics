import os
import pandas as pd
import sys

sys.path.append(".")
from utils.data_processor import load_and_clean_data, calculate_rfm
from utils.chatbot_logic import get_ai_agent, ask_agent

df = load_and_clean_data()
rfm_df = calculate_rfm(df)

agent = get_ai_agent(df, rfm_df)

print("Invoking CALCULATION Query...")
prompt = "Tính giúp em tổng số lượng dòng dữ liệu trong bảng df1?"
print(f"Prompting: '{prompt}'")

try:
    response = ask_agent(agent, prompt)
    print("\n--- AGENT RESPONSE ---")
    print(response)
    print("----------------------")
except Exception as e:
    print(f"EXCEPTION CAUGHT: {e}")
