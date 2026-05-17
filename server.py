import os
# Khắc phục lỗi phân bổ bộ nhớ OpenBLAS trên Windows
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import os
import json
from typing import List, Optional

# Import existing data utilities
from utils.data_processor import (
    load_and_clean_data, 
    get_monthly_trends_sql, 
    get_category_revenue_sql, 
    get_geo_revenue_sql,
    calculate_rfm
)
from utils.chatbot_logic import ask_agent

app = FastAPI(title="Superstore Analytics API")

# Configure CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
class LoginRequest(BaseModel):
    username: str
    password: str

class FilterRequest(BaseModel):
    years: List[int] = []
    regions: List[str] = []

class ChatRequest(BaseModel):
    message: str
    language: str = "vi"

# --- HELPER: Load core DataFrame ---
def get_df():
    df = load_and_clean_data()
    # Fill mandatory safe-guards
    if 'Order Year' not in df.columns:
        df['Order Year'] = 2026
    if 'Region' not in df.columns:
        df['Region'] = 'All Regions'
    return df

# --- API ENDPOINTS ---

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    if req.username == "admin" and req.password == "admin123":
        return {"status": "success", "token": "mock-auth-token-admin", "username": "admin"}
    raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không chính xác.")

@app.get("/api/filters")
async def get_filters():
    df = get_df()
    years = sorted([int(y) for y in df['Order Year'].dropna().unique()], reverse=True)
    regions = sorted([str(r) for r in df['Region'].dropna().unique()])
    markets = sorted([str(m) for m in df['Market'].dropna().unique()]) if 'Market' in df.columns else []
    
    return {
        "years": years,
        "regions": regions,
        "markets": markets
    }

@app.post("/api/dashboard/overview")
async def get_dashboard_overview(req: FilterRequest):
    df = get_df()
    
    # Safeguard Years/Regions
    all_years = sorted(list(df['Order Year'].unique()))
    all_regions = list(df['Region'].unique())
    
    valid_years = [y for y in req.years if y in all_years] if req.years else all_years
    valid_regions = [r for r in req.regions if r in all_regions] if req.regions else all_regions
    
    # Filter primary DF
    df_filtered = df[(df['Order Year'].isin(valid_years)) & (df['Region'].isin(valid_regions))]
    
    # 1. KPI Computations
    total_sales = float(df_filtered['Sales'].sum())
    total_profit = float(df_filtered['Profit'].sum())
    profit_margin = float((total_profit / total_sales * 100) if total_sales != 0 else 0)
    total_orders = int(df_filtered['Order ID'].nunique())
    total_quantity = float(df_filtered['Quantity'].sum())
    
    # 2. Monthly Trends (SQL Optimized)
    trend_df = get_monthly_trends_sql(valid_years, valid_regions)
    monthly_trends = trend_df.to_dict(orient='records')
    
    # 3. Category Pie Chart / Sales
    cat_sales_df = df_filtered.groupby('Category')['Sales'].sum().reset_index()
    cat_sales = [{"category": str(row['Category']), "sales": float(row['Sales'])} for _, row in cat_sales_df.iterrows()]
    
    # 4. Region Profit Bar Chart
    reg_profit_df = df_filtered.groupby('Region')['Profit'].sum().sort_values().reset_index()
    reg_profit = [{"region": str(row['Region']), "profit": float(row['Profit'])} for _, row in reg_profit_df.iterrows()]
    
    # 5. Market Sales Bar Chart
    mkt_sales_df = df_filtered.groupby('Market')['Sales'].sum().sort_values(ascending=False).reset_index()
    mkt_sales = [{"market": str(row['Market']), "sales": float(row['Sales'])} for _, row in mkt_sales_df.iterrows()]
    
    # 6. Top 10 Best Selling Products
    top_prod_df = df_filtered.groupby('Product Name')['Sales'].sum().nlargest(10).reset_index()
    top_prod = [{"product": str(row['Product Name']), "sales": float(row['Sales'])} for _, row in top_prod_df.iterrows()]
    
    # 7. Recent Transactions (first 100 rows for response speed)
    cols = ['Order ID', 'Order Date', 'Customer Name', 'Region', 'Category', 'Product Name', 'Sales', 'Profit']
    cols = [c for c in cols if c in df_filtered.columns]
    
    display_df = df_filtered[cols].sort_values('Order Date', ascending=False).head(100).copy()
    # Stringify dates for JSON compatibility
    for d_col in ['Order Date']:
        if d_col in display_df.columns:
            display_df[d_col] = display_df[d_col].astype(str)
            
    transactions = display_df.to_dict(orient='records')
    
    return {
        "kpis": {
            "totalSales": total_sales,
            "totalProfit": total_profit,
            "profitMargin": round(profit_margin, 2),
            "totalOrders": total_orders,
            "totalQuantity": total_quantity
        },
        "monthlyTrends": monthly_trends,
        "categorySales": cat_sales,
        "regionProfit": reg_profit,
        "marketSales": mkt_sales,
        "topProducts": top_prod,
        "transactions": transactions
    }

@app.post("/api/dashboard/performance")
async def get_performance_data(filters: FilterRequest):
    df = get_df()
    df_filtered = df[(df['Order Year'].isin(filters.years)) & (df['Region'].isin(filters.regions))].copy()
    
    if len(df_filtered) == 0:
        return {
            "pareto": [],
            "profitMargin": [],
            "geoRevenue": [],
            "subCatSales": []
        }

    # 1. Pareto Data (Top 30 Customers by Sales)
    pareto_df = df_filtered.groupby('Customer Name')['Sales'].sum().sort_values(ascending=False).reset_index()
    pareto_df['Cum_Sales'] = pareto_df['Sales'].cumsum()
    tot_sales = pareto_df['Sales'].sum()
    pareto_df['Cum_Percentage'] = (pareto_df['Cum_Sales'] / tot_sales * 100) if tot_sales > 0 else 0
    
    top_30_pareto = pareto_df.head(30)
    pareto_data = [{
        "customer": str(row['Customer Name']),
        "sales": float(row['Sales']),
        "cumPercent": float(row['Cum_Percentage'])
    } for _, row in top_30_pareto.iterrows()]

    # 2. Profit Margin by Region (%)
    margin_df = df_filtered.groupby('Region').agg(
        Total_Sales=('Sales', 'sum'),
        Total_Profit=('Profit', 'sum')
    ).reset_index()
    margin_df['Profit_Margin'] = (margin_df['Total_Profit'] / margin_df['Total_Sales'] * 100).fillna(0)
    margin_df = margin_df.sort_values(by='Profit_Margin', ascending=False)
    
    margin_data = [{
        "region": str(row['Region']),
        "sales": float(row['Total_Sales']),
        "profit": float(row['Total_Profit']),
        "margin": float(row['Profit_Margin'])
    } for _, row in margin_df.iterrows()]

    # 3. Category Breakdown (Top 15 Sub-Categories by Revenue)
    cat_df = get_category_revenue_sql(filters.years, filters.regions)
    sub_cat_data = [{
        "category": str(row['Category']),
        "subCategory": str(row['Sub-Category']),
        "sales": float(row['Sales'])
    } for _, row in cat_df.head(15).iterrows()]

    # 4. Geo Revenue (Market & Region)
    geo_df = get_geo_revenue_sql(filters.years, filters.regions)
    geo_data = [{
        "market": str(row['Market']),
        "region": str(row['Region']),
        "sales": float(row['Sales'])
    } for _, row in geo_df.iterrows()]

    return {
        "pareto": pareto_data,
        "profitMargin": margin_data,
        "geoRevenue": geo_data,
        "subCatSales": sub_cat_data
    }

@app.post("/api/chat")
async def get_chat_response(req: ChatRequest):
    df = get_df()
    rfm_df = calculate_rfm(df)
    
    # ask_agent normally returns Markdown. We pass simple strings instead of Streamlit objects.
    try:
        # Bypass placeholder since we refactored or pass None
        response = ask_agent(None, req.message, df, rfm_df)
        return {"response": response}
    except Exception as e:
        return {"response": f"Xin lỗi, có lỗi phát sinh khi kết nối trí tuệ nhân tạo: {str(e)}"}

@app.post("/api/dashboard/customers")
async def get_customer_data(req: FilterRequest):
    df = get_df()
    
    all_years = sorted(list(df['Order Year'].unique()))
    all_regions = list(df['Region'].unique())
    
    valid_years = [y for y in req.years if y in all_years] if req.years else all_years
    valid_regions = [r for r in req.regions if r in all_regions] if req.regions else all_regions
    
    df_filtered = df[(df['Order Year'].isin(valid_years)) & (df['Region'].isin(valid_regions))]
    
    if len(df_filtered) == 0:
        return {
            "summary": {
                "total": 0,
                "active": 0,
                "attention": 0,
                "highRisk": 0,
                "churned": 0
            },
            "riskDistribution": [],
            "customers": []
        }
        
    rfm = calculate_rfm(df_filtered)
    
    # 1. Summary Stats
    total = int(rfm['Customer ID'].nunique())
    active = int((rfm['Churn_Risk'] == 'An toàn (Active)').sum())
    attention = int((rfm['Churn_Risk'] == 'Cần chú ý (Needs Attention)').sum())
    high_risk = int((rfm['Churn_Risk'] == 'Nguy cơ cao (High Risk)').sum())
    churned = int((rfm['Churn_Risk'] == 'Đã rời bỏ (Churned)').sum())
    
    # 2. Risk Distribution for Chart
    risk_dist = [
        {"status": "An toàn (Active)", "count": active},
        {"status": "Cần chú ý (Needs Attention)", "count": attention},
        {"status": "Nguy cơ cao (High Risk)", "count": high_risk},
        {"status": "Đã rời bỏ (Churned)", "count": churned}
    ]
    
    # 3. Top 50 Customers by Monetary Value
    top_50 = rfm.sort_values(by='Monetary', ascending=False).head(50)
    
    # Convert scores to integers for frontend safety
    for col in ['R_Score', 'F_Score', 'M_Score']:
        top_50[col] = top_50[col].astype(int)
        
    customers_list = top_50.to_dict(orient='records')
    
    return {
        "summary": {
            "total": total,
            "active": active,
            "attention": attention,
            "highRisk": high_risk,
            "churned": churned
        },
        "riskDistribution": risk_dist,
        "customers": customers_list
    }

@app.post("/api/dashboard/segments")
async def get_segment_data(filters: FilterRequest):
    df = get_df()
    
    all_years = sorted(list(df['Order Year'].unique()))
    all_regions = list(df['Region'].unique())
    
    valid_years = [y for y in filters.years if y in all_years] if filters.years else all_years
    valid_regions = [r for r in filters.regions if r in all_regions] if filters.regions else all_regions
    
    df_filtered = df[(df['Order Year'].isin(valid_years)) & (df['Region'].isin(valid_regions))].copy()
    
    if len(df_filtered) == 0:
        return {"segmentSales": [], "segmentProfit": [], "segmentByRegion": [], "segmentsList": []}
        
    # Segment Sales
    seg_sales = df_filtered.groupby('Segment')['Sales'].sum().reset_index()
    segment_sales = [{"segment": str(row['Segment']), "sales": float(row['Sales'])} for _, row in seg_sales.iterrows()]
    
    # Segment Profit
    seg_profit = df_filtered.groupby('Segment')['Profit'].sum().reset_index()
    segment_profit = [{"segment": str(row['Segment']), "profit": float(row['Profit'])} for _, row in seg_profit.iterrows()]
    
    # Segment by Region
    seg_reg = df_filtered.groupby(['Region', 'Segment'])['Sales'].sum().reset_index()
    pivot_df = seg_reg.pivot(index='Region', columns='Segment', values='Sales').fillna(0).reset_index()
    segment_by_region = pivot_df.to_dict(orient='records')
    
    # Extract unique segments for charting
    segments_list = list(df_filtered['Segment'].unique())
    
    return {
        "segmentSales": segment_sales,
        "segmentProfit": segment_profit,
        "segmentByRegion": segment_by_region,
        "segmentsList": segments_list
    }

# --- SERVE FRONTEND (Zero-Build Setup) ---
# Ensure directories exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

@app.get("/")
async def index():
    # Fallback redirection to templates index
    if os.path.exists("templates/index.html"):
        return FileResponse("templates/index.html")
    return {"message": "Server is running. frontend index.html not created yet!"}

# In production, mount the static directory
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Superstore Enterprise Server at http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
