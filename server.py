import os
# Khắc phục lỗi phân bổ bộ nhớ OpenBLAS trên Windows
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
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

    # 1. Pareto Data (Top 15 Customers by Sales)
    pareto_df = df_filtered.groupby('Customer Name')['Sales'].sum().sort_values(ascending=False).reset_index()
    pareto_df['Cum_Sales'] = pareto_df['Sales'].cumsum()
    tot_sales = pareto_df['Sales'].sum()
    pareto_df['Cum_Percentage'] = (pareto_df['Cum_Sales'] / tot_sales * 100) if tot_sales > 0 else 0
    
    top_15_pareto = pareto_df.head(15)
    pareto_data = [{
        "customer": str(row['Customer Name']),
        "sales": float(row['Sales']),
        "cumPercent": float(row['Cum_Percentage'])
    } for _, row in top_15_pareto.iterrows()]

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

@app.post("/api/dashboard/shipping")
async def get_shipping_data(filters: FilterRequest):
    df = get_df()
    
    all_years = sorted(list(df['Order Year'].unique()))
    all_regions = list(df['Region'].unique())
    
    valid_years = [y for y in filters.years if y in all_years] if filters.years else all_years
    valid_regions = [r for r in filters.regions if r in all_regions] if filters.regions else all_regions
    
    df_filtered = df[(df['Order Year'].isin(valid_years)) & (df['Region'].isin(valid_regions))].copy()
    
    if len(df_filtered) == 0:
        return {
            "summary": {"avgDeliveryDays": 0, "totalShippingCost": 0, "avgShippingCost": 0, "shippingCostRatio": 0},
            "deliveryByMode": [],
            "costVsSales": [],
            "performanceByRegion": []
        }
        
    avg_delivery_days = float(df_filtered['Delivery Days'].mean()) if 'Delivery Days' in df_filtered.columns else 0
    total_shipping_cost = float(df_filtered['Shipping Cost'].sum()) if 'Shipping Cost' in df_filtered.columns else 0
    avg_shipping_cost = float(df_filtered['Shipping Cost'].mean()) if 'Shipping Cost' in df_filtered.columns else 0
    total_sales = float(df_filtered['Sales'].sum()) if 'Sales' in df_filtered.columns else 0
    shipping_cost_ratio = (total_shipping_cost / total_sales * 100) if total_sales > 0 else 0
    
    # 1. Delivery by Mode (Boxplot Quantiles)
    delivery_by_mode = []
    if 'Ship Mode' in df_filtered.columns and 'Delivery Days' in df_filtered.columns:
        for mode in df_filtered['Ship Mode'].unique():
            mode_data = df_filtered[df_filtered['Ship Mode'] == mode]['Delivery Days'].dropna()
            if len(mode_data) > 0:
                delivery_by_mode.append({
                    "mode": str(mode),
                    "min": float(mode_data.min()),
                    "q1": float(mode_data.quantile(0.25)),
                    "median": float(mode_data.median()),
                    "q3": float(mode_data.quantile(0.75)),
                    "max": float(mode_data.max())
                })
                
    # 2. Cost vs Sales (Scatter)
    cost_vs_sales = []
    if 'Sales' in df_filtered.columns and 'Shipping Cost' in df_filtered.columns:
        scatter_cols = ['Sales', 'Shipping Cost']
        if 'Order Priority' in df_filtered.columns:
            scatter_cols.append('Order Priority')
            
        scatter_df = df_filtered[scatter_cols].dropna().sample(min(300, len(df_filtered)))
        for _, row in scatter_df.iterrows():
            cost_vs_sales.append({
                "sales": float(row['Sales']),
                "cost": float(row['Shipping Cost']),
                "priority": str(row.get('Order Priority', 'Unknown'))
            })
            
    # 3. Performance by Region
    performance_by_region = []
    if 'Region' in df_filtered.columns and 'Delivery Days' in df_filtered.columns and 'Shipping Cost' in df_filtered.columns:
        region_perf = df_filtered.groupby('Region').agg(
            Avg_Delivery_Days=('Delivery Days', 'mean'),
            Avg_Shipping_Cost=('Shipping Cost', 'mean')
        ).reset_index()
        for _, row in region_perf.iterrows():
            performance_by_region.append({
                "region": str(row['Region']),
                "avgDeliveryDays": float(row['Avg_Delivery_Days']),
                "avgShippingCost": float(row['Avg_Shipping_Cost'])
            })
            
    return {
        "summary": {
            "avgDeliveryDays": avg_delivery_days,
            "totalShippingCost": total_shipping_cost,
            "avgShippingCost": avg_shipping_cost,
            "shippingCostRatio": shipping_cost_ratio
        },
        "deliveryByMode": delivery_by_mode,
        "costVsSales": cost_vs_sales,
        "performanceByRegion": performance_by_region
    }

@app.post("/api/dashboard/recommendations")
async def get_recommendations_data(filters: FilterRequest):
    df = get_df()
    all_years = sorted(list(df['Order Year'].unique()))
    all_regions = list(df['Region'].unique())
    valid_years = [y for y in filters.years if y in all_years] if filters.years else all_years
    valid_regions = [r for r in filters.regions if r in all_regions] if filters.regions else all_regions
    
    df_filtered = df[(df['Order Year'].isin(valid_years)) & (df['Region'].isin(valid_regions))].copy()
    
    if len(df_filtered) == 0 or 'Order ID' not in df_filtered.columns or 'Sub-Category' not in df_filtered.columns:
        return {"heatmap": [], "pairs": [], "uniqueItems": []}
        
    order_counts = df_filtered['Order ID'].value_counts()
    multi_item_orders = order_counts[order_counts > 1].index
    filtered_orders_df = df_filtered[df_filtered['Order ID'].isin(multi_item_orders)]
    
    total_orders = len(multi_item_orders)
    if total_orders == 0:
        return {"heatmap": [], "pairs": [], "uniqueItems": []}
        
    order_groups = filtered_orders_df.groupby('Order ID')['Sub-Category'].apply(set).tolist()
    
    from collections import defaultdict
    pair_counts = defaultdict(int)
    item_counts = defaultdict(int)
    
    for group in order_groups:
        items = sorted(list(group))
        for item in items:
            item_counts[item] += 1
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                pair_counts[(items[i], items[j])] += 1
                
    pairs_list = []
    for (item_a, item_b), count in pair_counts.items():
        support = count / total_orders
        conf_a_b = count / item_counts[item_a] if item_counts[item_a] > 0 else 0
        conf_b_a = count / item_counts[item_b] if item_counts[item_b] > 0 else 0
        pairs_list.append({
            "itemA": str(item_a),
            "itemB": str(item_b),
            "count": int(count),
            "support": float(support),
            "confAB": float(conf_a_b),
            "confBA": float(conf_b_a)
        })
        
    pairs_list = sorted(pairs_list, key=lambda x: x['count'], reverse=True)
    unique_items = sorted(list(item_counts.keys()))
    
    heatmap = []
    for (item_a, item_b), count in pair_counts.items():
        heatmap.append({"x": str(item_a), "y": str(item_b), "val": int(count)})
        heatmap.append({"x": str(item_b), "y": str(item_a), "val": int(count)}) # symmetric
        
    for item in unique_items:
        heatmap.append({"x": str(item), "y": str(item), "val": 0}) # diagonal
        
    return {
        "heatmap": heatmap,
        "pairs": pairs_list,
        "uniqueItems": unique_items
    }

@app.post("/api/dashboard/forecast")
async def get_forecast_data(filters: FilterRequest):
    import numpy as np
    import pandas as pd
    
    df = get_df()
    all_years = sorted(list(df['Order Year'].unique()))
    all_regions = list(df['Region'].unique())
    valid_years = [y for y in filters.years if y in all_years] if filters.years else all_years
    valid_regions = [r for r in filters.regions if r in all_regions] if filters.regions else all_regions
    
    df_filtered = df[(df['Order Year'].isin(valid_years)) & (df['Region'].isin(valid_regions))].copy()
    
    if len(df_filtered) == 0:
        return {"actual": [], "forecast": [], "kpis": {}}
        
    df_filtered['Year_Month_DT'] = pd.to_datetime(df_filtered['Order Date']).dt.to_period('M')
    monthly_data = df_filtered.groupby('Year_Month_DT')[['Sales', 'Profit']].sum().reset_index()
    monthly_data['Year_Month_DT'] = monthly_data['Year_Month_DT'].astype(str)
    monthly_data = monthly_data.sort_values('Year_Month_DT').reset_index(drop=True)
    
    if len(monthly_data) < 12:
        return {"actual": [], "forecast": [], "kpis": {}}
        
    forecast_months = 12
    x = np.arange(len(monthly_data))
    y_sales = monthly_data['Sales'].values
    y_profit = monthly_data['Profit'].values
    
    slope_sales, intercept_sales = np.polyfit(x, y_sales, 1)
    slope_profit, intercept_profit = np.polyfit(x, y_profit, 1)
    
    monthly_data['Month_Num'] = pd.to_datetime(monthly_data['Year_Month_DT']).dt.month
    avg_sales_by_month = monthly_data.groupby('Month_Num')['Sales'].mean()
    overall_mean_sales = monthly_data['Sales'].mean()
    seasonal_indices = (avg_sales_by_month / overall_mean_sales).to_dict()
    
    future_x = np.arange(len(monthly_data), len(monthly_data) + forecast_months)
    last_date = pd.to_datetime(monthly_data['Year_Month_DT'].iloc[-1] + "-01")
    future_dates = [ (last_date + pd.DateOffset(months=i)).strftime('%Y-%m') for i in range(1, forecast_months + 1) ]
    
    forecast_sales = []
    forecast_profit = []
    lower_bound_sales = []
    upper_bound_sales = []
    
    std_err_sales = float(np.std(y_sales - (slope_sales * x + intercept_sales)))
    z_score = 1.96 # 95% confidence
    
    for i, fx in enumerate(future_x):
        trend_s = slope_sales * fx + intercept_sales
        trend_p = slope_profit * fx + intercept_profit
        
        f_month = pd.to_datetime(future_dates[i] + "-01").month
        s_index = seasonal_indices.get(f_month, 1.0)
        
        pred_s = max(100.0, trend_s * s_index)
        pred_p = trend_p * s_index
        
        forecast_sales.append(float(pred_s))
        forecast_profit.append(float(pred_p))
        lower_bound_sales.append(float(max(0.0, pred_s - z_score * std_err_sales)))
        upper_bound_sales.append(float(pred_s + z_score * std_err_sales))
        
    actual = []
    for _, row in monthly_data.iterrows():
        actual.append({
            "month": str(row['Year_Month_DT']),
            "sales": float(row['Sales']),
            "profit": float(row['Profit'])
        })
        
    forecast = []
    for i in range(forecast_months):
        forecast.append({
            "month": str(future_dates[i]),
            "sales": float(forecast_sales[i]),
            "profit": float(forecast_profit[i]),
            "lower": float(lower_bound_sales[i]),
            "upper": float(upper_bound_sales[i])
        })
        
    growth_rate = float((slope_sales / overall_mean_sales) * 100) if overall_mean_sales > 0 else 0
    
    return {
        "actual": actual,
        "forecast": forecast,
        "kpis": {
            "firstMonthForecast": float(forecast_sales[0]),
            "totalForecastSales": float(sum(forecast_sales)),
            "totalForecastProfit": float(sum(forecast_profit)),
            "growthRate": growth_rate,
            "startMonth": future_dates[0]
        }
    }

@app.post("/api/eda/analyze")
async def analyze_data(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Dung lượng file quá lớn (tối đa 50MB)")
    
    import io
    try:
        try:
            df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(content), encoding='latin-1')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không thể đọc file CSV: {str(e)}")
    
    if len(df) == 0:
        raise HTTPException(status_code=400, detail="File CSV rỗng hoặc không có dữ liệu phù hợp")
        
    num_rows = int(df.shape[0])
    num_cols = int(df.shape[1])
    
    # Data Health: Null values
    missing_counts = df.isnull().sum()
    missing_percent = (missing_counts / num_rows * 100).round(1)
    
    missing_info = []
    for col in df.columns:
        missing_info.append({
            "column": col,
            "missingCount": int(missing_counts[col]),
            "missingPercent": float(missing_percent[col]),
            "needOptimize": bool(missing_percent[col] > 50.0)
        })
        
    # Duplicates
    num_duplicates = int(df.duplicated().sum())
    
    # Categorical, Temporal, Numeric split
    categorical_cols = []
    temporal_cols = []
    numeric_cols = []
    
    for col in df.columns:
        col_type = str(df[col].dtype)
        col_lower = col.lower()
        
        # Try temporal check
        is_temp = False
        if 'date' in col_lower or 'time' in col_lower:
            try:
                pd.to_datetime(df[col].dropna().head(10))
                is_temp = True
            except:
                pass
                
        # Numeric check excluding ID, code, zip etc.
        is_num = False
        if ('int' in col_type or 'float' in col_type) and not any(k in col_lower for k in ['id', 'code', 'phone', 'zip', 'post', 'year']):
            is_num = True
            
        if is_temp:
            temporal_cols.append(col)
        elif is_num:
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)
            
    # Text summary builder
    min_date = "N/A"
    max_date = "N/A"
    if temporal_cols:
        temp_col = temporal_cols[0]
        try:
            temp_dt = pd.to_datetime(df[temp_col], errors='coerce')
            min_date = str(temp_dt.min().strftime('%Y-%m-%d')) if pd.notnull(temp_dt.min()) else "N/A"
            max_date = str(temp_dt.max().strftime('%Y-%m-%d')) if pd.notnull(temp_dt.max()) else "N/A"
        except:
            pass
            
    summary_text = f"Bộ dữ liệu này chứa {num_rows:,} dòng và {num_cols} cột. Nó bao gồm các cột phân loại chính như {', '.join(categorical_cols[:4])}."
    if temporal_cols and min_date != "N/A":
        summary_text += f" Thời gian ghi nhận dữ liệu kéo dài từ ngày {min_date} đến ngày {max_date}."
        
    # Numeric stats
    numeric_stats = []
    for col in numeric_cols:
        numeric_stats.append({
            "column": col,
            "min": float(df[col].min()) if pd.notnull(df[col].min()) else 0,
            "max": float(df[col].max()) if pd.notnull(df[col].max()) else 0,
            "avg": float(df[col].mean()) if pd.notnull(df[col].mean()) else 0
        })
        
    # Auto-chart suggestion
    suggested_charts = []
    
    # 1. Line: Temporal + Continuous
    if temporal_cols and numeric_cols:
        t_col = temporal_cols[0]
        n_col = numeric_cols[0]
        try:
            temp_df = df.copy()
            temp_df[t_col] = pd.to_datetime(temp_df[t_col], errors='coerce')
            temp_df = temp_df.dropna(subset=[t_col])
            
            # Aggregate by Month or Year
            num_m = temp_df[t_col].dt.to_period('M').nunique()
            if 1 < num_m <= 36:
                temp_df['period'] = temp_df[t_col].dt.to_period('M').astype(str)
            else:
                temp_df['period'] = temp_df[t_col].dt.year.astype(str)
                
            grouped = temp_df.groupby('period')[n_col].sum().reset_index()
            grouped = grouped.sort_values('period')
            
            suggested_charts.append({
                "type": "line",
                "title": f"📈 Xu hướng {n_col} qua thời gian ({t_col})",
                "seriesName": n_col,
                "categories": grouped['period'].tolist(),
                "data": [round(v, 2) for v in grouped[n_col].tolist()]
            })
        except:
            pass
            
    # 2. Bar: Categorical + Continuous
    if categorical_cols and numeric_cols:
        best_cat = None
        for col in categorical_cols:
            card = df[col].nunique()
            if 2 <= card <= 50:
                best_cat = col
                break
        if not best_cat:
            best_cat = categorical_cols[0]
            
        n_col = numeric_cols[0]
        try:
            grouped = df.groupby(best_cat)[n_col].sum().reset_index()
            grouped = grouped.sort_values(n_col, ascending=False).head(10)
            
            suggested_charts.append({
                "type": "bar",
                "title": f"📊 Top 10 {best_cat} theo {n_col}",
                "seriesName": n_col,
                "categories": grouped[best_cat].tolist(),
                "data": [round(v, 2) for v in grouped[n_col].tolist()]
            })
        except:
            pass
            
    return {
        "health": {
            "numRows": num_rows,
            "numCols": num_cols,
            "numDuplicates": num_duplicates,
            "missingInfo": missing_info
        },
        "insights": {
            "summaryText": summary_text,
            "numericStats": numeric_stats,
            "categoricalCols": categorical_cols,
            "temporalCols": temporal_cols,
            "numericCols": numeric_cols
        },
        "charts": suggested_charts
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
