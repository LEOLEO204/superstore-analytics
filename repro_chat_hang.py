import os
import pandas as pd
import sys
from dotenv import load_dotenv

# Add root path to load local utils
sys.path.append(".")

from utils.data_processor import load_and_clean_data, calculate_rfm
from utils.chatbot_logic import get_ai_agent, ask_agent

print("1. Loading Data...")
df = load_and_clean_data()
print(f"DF Loaded: {df.shape}")

rfm_df = calculate_rfm(df)
print(f"RFM DF Built: {rfm_df.shape}")

print("2. Creating Agent...")
agent = get_ai_agent(df, rfm_df)

if not agent:
    print("ERROR: Agent creation failed (API Key missing?)")
    sys.exit(1)

print("Agent Created successfully.")

print("3. Invoking Query...")
prompt = "Phân tích phân khúc khách hàng bằng RFM là gì và nó giúp ích gì cho doanh nghiệp?"
print(f"Prompting: '{prompt}'")

try:
    response = ask_agent(agent, prompt)
    print("\n--- AGENT RESPONSE ---")
    print(response)
    print("----------------------")
except Exception as e:
    print(f"EXCEPTION CAUGHT: {e}")
