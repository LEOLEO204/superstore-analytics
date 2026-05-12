import pandas as pd
import numpy as np
import datetime
import os
import sqlite3
import streamlit as st


DB_PATH = 'data/superstore.db'

def get_active_dataset_path():
    if os.path.exists('data/current_dataset.csv'):
        return 'data/current_dataset.csv'
    elif os.path.exists('current_dataset.csv'):
        return 'current_dataset.csv'
    
    # Nếu không có thì dùng file gốc
    if os.path.exists('data/superstore (1).csv'):
        return 'data/superstore (1).csv'
    elif os.path.exists('superstore (1).csv'):
        return 'superstore (1).csv'
        
    return 'data/superstore (1).csv'

def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)

def validate_and_clean_sop(df):
    """
    Thực thi Quy trình chuẩn SOP: Bước 2 (Kiểm tra cấu trúc) và Bước 3 (Làm sạch dữ liệu).
    """
    # --- BƯỚC 2: KIỂM TRA CẤU TRÚC DỮ LIỆU ---
    required_cols = [
        'Order ID', 'Order Date', 'Ship Date', 'Ship Mode', 
        'Customer ID', 'Customer Name', 'Segment', 
        'City', 'State', 'Country', 'Region', 'Market', 
        'Product ID', 'Category', 'Sub-Category', 'Product Name', 
        'Sales', 'Quantity', 'Discount', 'Profit', 'Shipping Cost', 'Order Priority'
    ]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Dataset không hợp lệ. Thiếu các cột bắt buộc: {', '.join(missing_cols)}. Vui lòng kiểm tra lại cấu trúc file.")
    
    df_cleaned = df.copy()
    
    # TRÁNH LỖI DUPLICATE COLUMN (CASE-INSENSITIVE): Xóa mọi cột sinh tự động (dù viết hoa hay thường) có sẵn trong file
    auto_generated_cols = ['delivery days', 'order year', 'order month', 'year-month', 'profit margin (%)', 'is_outlier']
    
    # Tìm chính xác các cột trong dataframe trùng khớp (không phân biệt hoa thường)
    cols_to_drop = [
        c for c in df_cleaned.columns 
        if c.lower() in auto_generated_cols
    ]
    if cols_to_drop:
        df_cleaned = df_cleaned.drop(columns=cols_to_drop)

    # --- BƯỚC 3: LÀM SẠCH DỮ LIỆU ---
    # 3.1. Xóa dòng trống
    df_cleaned = df_cleaned.dropna(subset=['Order ID', 'Order Date', 'Sales', 'Profit'])
    
    # 3.2. Chuẩn hóa ngày tháng (Hỗ trợ tự động định dạng dd/mm/yyyy hoặc yyyy-mm-dd)
    for date_col in ['Order Date', 'Ship Date']:
        df_cleaned[date_col] = pd.to_datetime(df_cleaned[date_col], dayfirst=True, errors='coerce')
    
    # Kiểm tra lỗi dữ liệu ngày tháng (SOP Step 9)
    if df_cleaned['Order Date'].isnull().any() or df_cleaned['Ship Date'].isnull().any():
        # Chỉ giữ lại những dòng chuyển đổi ngày thành công
        df_cleaned = df_cleaned.dropna(subset=['Order Date', 'Ship Date'])
        
    # 3.3. Chuyển Sales, Profit, Discount, Quantity, Shipping Cost sang dạng số
    numeric_cols = ['Sales', 'Profit', 'Discount', 'Quantity', 'Shipping Cost']
    for col in numeric_cols:
        if df_cleaned[col].dtype == object:
            # Xử lý nếu cột có dấu phẩy ngăn cách hàng nghìn hoặc ký tự tiền tệ
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace(',', '').str.replace('$', '')
        df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        df_cleaned[col] = df_cleaned[col].fillna(0)
        
    # 3.4. Tính toán Delivery Days, Order Year, Order Month nếu chưa có
    df_cleaned['Delivery Days'] = (df_cleaned['Ship Date'] - df_cleaned['Order Date']).dt.days
    df_cleaned['Order Year'] = df_cleaned['Order Date'].dt.year.astype(int)
    df_cleaned['Order Month'] = df_cleaned['Order Date'].dt.month.astype(int)
    df_cleaned['Year-Month'] = df_cleaned['Order Date'].dt.to_period('M').astype(str)
    
    # Feature Engineering (Step 4): Profit Margin = Profit / Sales
    df_cleaned['Profit Margin (%)'] = df_cleaned.apply(
        lambda x: (x['Profit'] / x['Sales'] * 100) if x['Sales'] != 0 else 0, 
        axis=1
    )
    
    # Chuyển đổi ngày về String ISO để lưu SQLite tốt hơn
    df_cleaned['Order Date'] = df_cleaned['Order Date'].dt.strftime('%Y-%m-%d')
    df_cleaned['Ship Date'] = df_cleaned['Ship Date'].dt.strftime('%Y-%m-%d')
    
    return df_cleaned

def initialize_database(force_reload=False, uploaded_df=None):
    """
    Khởi tạo cơ sở dữ liệu SQLite từ DataFrame hoặc file CSV.
    Thực thi theo SOP Bước 1, 2, 3.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        table_exists = cursor.fetchone()
        
        if not table_exists or force_reload:
            print("🚀 Bắt đầu khởi tạo cơ sở dữ liệu SQLite theo quy trình chuẩn SOP...")
            
            if uploaded_df is not None:
                df = uploaded_df
            else:
                file_path = get_active_dataset_path()
                # BƯỚC 1: Đọc file
                try:
                    df = pd.read_csv(file_path, sep=';', encoding='latin1')
                except Exception:
                    df = pd.read_csv(file_path, sep=',', encoding='latin1') # Fallback
            
            # BƯỚC 2 & 3: Làm sạch và Kiểm định dữ liệu chặt chẽ theo SOP
            df_final = validate_and_clean_sop(df)
            
            # BƯỚC 4: Flag Outliers & Lưu vào SQLite
            df_final = flag_outliers(df_final)
            df_final.to_sql('orders', conn, if_exists='replace', index=False)
            print(f"✅ Đã khởi tạo SQLite thành công với {len(df_final)} dòng dữ liệu.")
    finally:
        conn.close()

@st.cache_data(show_spinner=False)
def load_and_clean_data(file_path=None):
    initialize_database()
    
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    
    # Ép kiểu ngược lại về datetime
    for col in ['Order Date', 'Ship Date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
    return df

def detect_standard_columns(df):
    """
    Tự động nhận diện các cột Doanh số, Lợi nhuận, Khách hàng, Ngày tháng từ bất kỳ dataset nào.
    Giúp ứng dụng hoàn toàn độc lập với cấu trúc cột (Schema-agnostic).
    """
    col_map = {
        'Sales': None,
        'Profit': None,
        'Customer ID': None,
        'Order Date': None
    }
    
    # 1. Nhận diện cột Sales (Doanh số)
    sales_candidates = ['Sales', 'sales', 'Revenue', 'revenue', 'Amount', 'amount', 'Doanh thu', 'doanh thu', 'Total', 'total', 'Doanh Số']
    for c in sales_candidates:
        if c in df.columns:
            col_map['Sales'] = c
            break
    if not col_map['Sales']:
        num_cols = df.select_dtypes(include=['number']).columns
        if len(num_cols) > 0:
            col_map['Sales'] = num_cols[0]
            
    # 2. Nhận diện cột Profit (Lợi nhuận)
    profit_candidates = ['Profit', 'profit', 'Lợi nhuận', 'lợi nhuận', 'Earnings', 'earnings', 'Lợi Nhuận']
    for c in profit_candidates:
        if c in df.columns:
            col_map['Profit'] = c
            break
    if not col_map['Profit']:
        num_cols = df.select_dtypes(include=['number']).columns
        if len(num_cols) > 1:
            col_map['Profit'] = num_cols[1]
        elif len(num_cols) > 0:
            col_map['Profit'] = num_cols[0]
            
    # 3. Nhận diện cột Customer ID (Khách hàng)
    cust_candidates = ['Customer ID', 'customer_id', 'Customer', 'customer', 'Mã khách hàng', 'mã khách hàng', 'ID', 'id', 'User ID', 'user_id', 'Email', 'email']
    for c in cust_candidates:
        if c in df.columns:
            col_map['Customer ID'] = c
            break
    if not col_map['Customer ID']:
        col_map['Customer ID'] = df.columns[0] if len(df.columns) > 0 else None
        
    # 4. Nhận diện cột Order Date (Ngày mua)
    date_candidates = ['Order Date', 'order_date', 'Date', 'date', 'Ngày', 'ngày', 'Created At', 'created_at']
    for c in date_candidates:
        if c in df.columns:
            col_map['Order Date'] = c
            break
    if not col_map['Order Date']:
        for c in df.columns:
            if 'date' in c.lower() or 'time' in c.lower() or pd.api.types.is_datetime64_any_dtype(df[c]):
                col_map['Order Date'] = c
                break
                
    return col_map

def get_monthly_trends_sql(selected_years, selected_regions):
    """
    Truy vấn SQL tối ưu để tính Xu hướng Doanh thu và Lợi nhuận theo tháng.
    """
    initialize_database()
    conn = get_db_connection()
    
    years_clause = ",".join([str(y) for y in selected_years])
    regions_clause = ",".join([f"'{r}'" for r in selected_regions])
    
    if not years_clause:
        years_clause = "-1"
    if not regions_clause:
        regions_clause = "''"
        
    query = f"""
        SELECT "Year-Month", SUM(Sales) AS Sales, SUM(Profit) AS Profit
        FROM orders
        WHERE "Order Year" IN ({years_clause}) AND "Region" IN ({regions_clause})
        GROUP BY "Year-Month"
        ORDER BY "Year-Month"
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_category_revenue_sql(selected_years, selected_regions):
    """
    Truy vấn SQL tối ưu để tính Doanh thu theo Category và Sub-Category.
    """
    initialize_database()
    conn = get_db_connection()
    
    years_clause = ",".join([str(y) for y in selected_years])
    regions_clause = ",".join([f"'{r}'" for r in selected_regions])
    
    if not years_clause:
        years_clause = "-1"
    if not regions_clause:
        regions_clause = "''"
        
    query = f"""
        SELECT Category, "Sub-Category", SUM(Sales) AS Sales
        FROM orders
        WHERE "Order Year" IN ({years_clause}) AND "Region" IN ({regions_clause})
        GROUP BY Category, "Sub-Category"
        ORDER BY Sales DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_geo_revenue_sql(selected_years, selected_regions):
    """
    Truy vấn SQL tối ưu để tính Doanh thu theo Market và Region.
    """
    initialize_database()
    conn = get_db_connection()
    
    years_clause = ",".join([str(y) for y in selected_years])
    regions_clause = ",".join([f"'{r}'" for r in selected_regions])
    
    if not years_clause:
        years_clause = "-1"
    if not regions_clause:
        regions_clause = "''"
        
    query = f"""
        SELECT Market, Region, SUM(Sales) AS Sales
        FROM orders
        WHERE "Order Year" IN ({years_clause}) AND "Region" IN ({regions_clause})
        GROUP BY Market, Region
        ORDER BY Sales DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def flag_outliers(df, columns=['Sales', 'Profit']):
    """
    Phát hiện ngoại lai dựa trên phương pháp IQR.
    Thêm cột Is_Outlier = True nếu dòng đó chứa giá trị ngoại lai ở Sales hoặc Profit.
    """
    df_out = df.copy()
    df_out['Is_Outlier'] = False
    
    existing_cols = [col for col in columns if col in df_out.columns]
    for col in existing_cols:
        try:
            Q1 = df_out[col].quantile(0.25)
            Q3 = df_out[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            # Đánh dấu ngoại lai
            outlier_condition = (df_out[col] < lower_bound) | (df_out[col] > upper_bound)
            df_out['Is_Outlier'] = df_out['Is_Outlier'] | outlier_condition
        except Exception:
            pass
        
    return df_out

def calculate_rfm(df):
    """
    Tính toán chỉ số RFM (Recency, Frequency, Monetary) để đánh giá Churn Risk.
    Có bổ sung xử lý an toàn cho mọi bộ dữ liệu khác nhau.
    """
    col_map = detect_standard_columns(df)
    
    date_col = col_map['Order Date']
    sales_col = col_map['Sales']
    cust_col = col_map['Customer ID']
    
    # Kiểm tra nếu thiếu các cột cốt lõi để tính RFM, trả về dataframe rỗng nhưng có cấu trúc đúng
    if not date_col or not sales_col or not cust_col:
        return pd.DataFrame(columns=['Customer ID', 'Recency', 'Frequency', 'Monetary', 'R_Score', 'F_Score', 'M_Score', 'Churn_Risk', 'Customer Name', 'Segment'])
        
    # Tạo bản sao sạch
    df_rfm = df.dropna(subset=[cust_col, date_col, sales_col]).copy()
    df_rfm[date_col] = pd.to_datetime(df_rfm[date_col], errors='coerce')
    df_rfm = df_rfm.dropna(subset=[date_col])
    
    if len(df_rfm) == 0:
        return pd.DataFrame(columns=['Customer ID', 'Recency', 'Frequency', 'Monetary', 'R_Score', 'F_Score', 'M_Score', 'Churn_Risk', 'Customer Name', 'Segment'])
        
    snapshot_date = df_rfm[date_col].max() + datetime.timedelta(days=1)
    
    # Sử dụng Named Aggregation trong Pandas để đặt tên cột trực tiếp và an toàn tuyệt đối, tránh lỗi lệch trục (Length mismatch)
    rfm_base = df_rfm.groupby(cust_col).agg(
        First_Purchase_Date=(date_col, 'min'),
        Last_Purchase_Date=(date_col, 'max'),
        Frequency=(cust_col, 'count'),
        Monetary=(sales_col, 'sum')
    )
    rfm = rfm_base.reset_index()
    
    rfm['Recency'] = (snapshot_date - rfm['Last_Purchase_Date']).dt.days
    rfm['Is_New_Customer'] = (snapshot_date - rfm['First_Purchase_Date']).dt.days <= 365
    
    # Chấm điểm 1-5 (5 là tốt nhất)
    try:
        rfm['R_Score'] = pd.qcut(rfm['Recency'], 5, labels=[5, 4, 3, 2, 1])
    except Exception:
        try:
            rfm['R_Score'] = pd.qcut(rfm['Recency'].rank(method='first'), 5, labels=[5, 4, 3, 2, 1])
        except Exception:
            rfm['R_Score'] = 3
        
    try:
        rfm['F_Score'] = pd.qcut(rfm['Frequency'], 5, labels=[1, 2, 3, 4, 5])
    except Exception:
        try:
            rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
        except Exception:
            rfm['F_Score'] = 3
        
    try:
        rfm['M_Score'] = pd.qcut(rfm['Monetary'], 5, labels=[1, 2, 3, 4, 5])
    except Exception:
        try:
            rfm['M_Score'] = pd.qcut(rfm['Monetary'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
        except Exception:
            rfm['M_Score'] = 3
        
    # Đánh giá rủi ro rời bỏ (Churn Risk)
    def determine_risk(row):
        try:
            r = int(row['R_Score'])
            f = int(row['F_Score'])
            m = int(row['M_Score'])
            
            if r <= 2 and (f >= 4 or m >= 4):
                return "Nguy cơ cao (High Risk)"
            elif r <= 2 and f < 4 and m < 4:
                return "Đã rời bỏ (Churned)"
            elif r >= 4:
                return "An toàn (Active)"
            else:
                return "Cần chú ý (Needs Attention)"
        except Exception:
            return "Cần chú ý (Needs Attention)"
            
    rfm['Churn_Risk'] = rfm.apply(determine_risk, axis=1)
    
    # Ghép thêm thông tin khách hàng nếu có
    info_cols = [cust_col]
    if 'Customer Name' in df.columns:
        info_cols.append('Customer Name')
    if 'Segment' in df.columns:
        info_cols.append('Segment')
        
    if len(info_cols) > 1:
        cust_info = df[info_cols].drop_duplicates()
        # Ép kiểu dữ liệu cột khóa về string để tránh lỗi lồng ghép khác kiểu (datetime vs str)
        try:
            rfm[cust_col] = rfm[cust_col].astype(str)
            cust_info[cust_col] = cust_info[cust_col].astype(str)
        except Exception:
            pass
        rfm = rfm.merge(cust_info, on=cust_col, how='left')
        
    # Chuẩn hóa tên cột trả về thành 'Customer ID' để tương thích với code cũ
    if cust_col != 'Customer ID':
        rfm = rfm.rename(columns={cust_col: 'Customer ID'})
    
    return rfm

def calculate_distribution_stats(df):
    """
    Tính toán các chỉ số xác suất thống kê chuyên sâu (Skewness, Kurtosis, Bias, Dispersion)
    cho các cột số (Sales, Profit) của bất kỳ tập dữ liệu nào.
    """
    col_map = detect_standard_columns(df)
    sales_col = col_map['Sales']
    profit_col = col_map['Profit']
    
    stats = {}
    
    for label, col in [('Sales', sales_col), ('Profit', profit_col)]:
        if col and col in df.columns:
            series = df[col].dropna()
            if len(series) > 0:
                mean_val = float(series.mean())
                median_val = float(series.median())
                std_val = float(series.std())
                skew_val = float(series.skew())
                kurt_val = float(series.kurt())
                cv_val = float(std_val / mean_val) if mean_val > 0 else 0.0
                
                # Diễn giải Bias (Độ lệch)
                if skew_val > 1.0:
                    bias_desc = "Lệch phải mạnh (Highly Right-skewed). Dữ liệu tập trung chủ yếu ở phân khúc giá trị thấp, nhưng có một vài giao dịch giá trị cực lớn kéo trung bình lên cao."
                elif skew_val > 0.5:
                    bias_desc = "Lệch phải vừa (Moderately Right-skewed)."
                elif skew_val < -1.0:
                    bias_desc = "Lệch trái mạnh (Highly Left-skewed). Dữ liệu tập trung ở phân khúc giá trị cao."
                elif skew_val < -0.5:
                    bias_desc = "Lệch trái vừa (Moderately Left-skewed)."
                else:
                    bias_desc = "Đối xứng tương đối (Approximately Symmetric). Dữ liệu phân bổ khá cân bằng quanh giá trị trung bình."
                    
                # Diễn giải Kurtosis (Độ nhọn)
                if kurt_val > 3.0:
                    kurt_desc = "Phân phối nhọn (Leptokurtic). Có đuôi rất dày, biểu thị tần suất xuất hiện các giá trị cực đoan (outliers) rất cao."
                elif kurt_val < -1.0:
                    kurt_desc = "Phân phối bẹt (Platykurtic). Đuôi mỏng, dữ liệu phân bổ trải đều hơn, ít biến động cực đoan."
                else:
                    kurt_desc = "Phân phối trung bình (Mesokurtic). Độ nhọn tương tự phân phối chuẩn."
                    
                stats[label] = {
                    'col_name': col,
                    'mean': mean_val,
                    'median': median_val,
                    'std': std_val,
                    'skew': skew_val,
                    'kurt': kurt_val,
                    'cv': cv_val,
                    'bias_interpretation': bias_desc,
                    'kurt_interpretation': kurt_desc
                }
    return stats
