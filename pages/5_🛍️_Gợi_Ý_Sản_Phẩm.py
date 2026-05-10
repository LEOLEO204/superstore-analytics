# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_processor import load_and_clean_data, calculate_rfm
from utils.chat_widget import render_floating_chat
import importlib
import utils.ui_components
importlib.reload(utils.ui_components)
from utils.ui_components import inject_custom_css, render_top_bar, render_page_header
from utils.i18n import t

st.set_page_config(page_title="Gợi ý sản phẩm Cross-sell", layout="wide", page_icon="🛍️")
inject_custom_css()
render_top_bar()

# CSS bổ sung cho trang Cross-sell
st.markdown("""
<style>
    .cross-sell-box {
        background-color: #e0f2f1;
        border-left: 5px solid #00796B;
        padding: 20px;
        border-radius: 8px;
        margin-top: 15px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

render_page_header("Phân Tích Giỏ Hàng & Gợi Ý Bán Kèm", "Khai phá mối liên kết tiềm năng giữa các dòng sản phẩm để thiết kế chiến dịch đóng gói Combo tăng trưởng doanh thu", "🛍️", "green")

df = load_and_clean_data()
rfm_df = calculate_rfm(df)

order_id_col = 'Order ID' if 'Order ID' in df.columns else None
sub_cat_col = 'Sub-Category' if 'Sub-Category' in df.columns else None

if not order_id_col or not sub_cat_col:
    st.warning("Tập dữ liệu hiện tại không chứa thông tin về Mã đơn hàng (Order ID) và Danh mục sản phẩm (Sub-Category) để thực hiện khai phá giỏ hàng.")
else:
    # 1. Thuật toán khai phá giỏ hàng (Co-occurrence Matrix)
    # Lọc bỏ đơn hàng chỉ mua 1 sản phẩm đơn lẻ
    order_counts = df[order_id_col].value_counts()
    multi_item_orders = order_counts[order_counts > 1].index
    filtered_orders_df = df[df[order_id_col].isin(multi_item_orders)]
    
    total_orders = len(multi_item_orders)
    
    if total_orders == 0:
        st.info("Không có đơn hàng nào chứa nhiều hơn 1 sản phẩm để thực hiện phân tích bán kèm.")
    else:
        # Nhóm danh mục sản phẩm theo từng Order ID
        order_groups = filtered_orders_df.groupby(order_id_col)[sub_cat_col].apply(set).tolist()
        
        # Đếm tần suất xuất hiện chung (Co-occurrence)
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
                    
        # Chuyển đổi thành DataFrame kết quả
        pairs_list = []
        for (item_a, item_b), count in pair_counts.items():
            support_a_b = count / total_orders
            confidence_a_to_b = count / item_counts[item_a]
            confidence_b_to_a = count / item_counts[item_b]
            
            pairs_list.append({
                'Sản phẩm A': item_a,
                'Sản phẩm B': item_b,
                'Tần suất mua chung': count,
                'Độ hỗ trợ (Support)': support_a_b,
                'Độ tin cậy (A -> B)': confidence_a_to_b,
                'Độ tin cậy (B -> A)': confidence_b_to_a
            })
            
        pairs_df = pd.DataFrame(pairs_list)
        pairs_df = pairs_df.sort_values(by='Tần suất mua chung', ascending=False).reset_index(drop=True)
        
        # 2. Tạo ma trận nhiệt độ (Co-occurrence Heatmap)
        unique_items = sorted(list(item_counts.keys()))
        matrix_size = len(unique_items)
        co_matrix = np.zeros((matrix_size, matrix_size))
        
        for (item_a, item_b), count in pair_counts.items():
            idx_a = unique_items.index(item_a)
            idx_b = unique_items.index(item_b)
            co_matrix[idx_a, idx_b] = count
            co_matrix[idx_b, idx_a] = count # Tính đối xứng
            
        # Trực quan hóa ma trận nhiệt bằng Plotly
        fig_heat = px.imshow(
            co_matrix,
            x=unique_items,
            y=unique_items,
            color_continuous_scale='Teal',
            title="Ma trận nhiệt tần suất mua chung sản phẩm (Market Basket Heatmap)"
        )
        fig_heat.update_layout(height=500, template="plotly_white")
        
        st.plotly_chart(fig_heat, use_container_width=True)
        
        # 3. Trình xuất ý tưởng Combo bán kèm thông minh tương tác (Interactive Recommendation Engine)
        st.divider()
        col_c1, col_c2 = st.columns([1, 1])
        
        with col_c1:
            st.markdown("### 🔍 Trình gợi ý sản phẩm mua kèm tương tác")
            selected_item = st.selectbox(
                "Chọn sản phẩm mục tiêu (Anchor Product) để thiết lập bán chéo:",
                options=unique_items
            )
            
            # Lọc các cặp có chứa sản phẩm được chọn
            recs = []
            for idx, row in pairs_df.iterrows():
                if row['Sản phẩm A'] == selected_item:
                    recs.append({
                        'Sản phẩm gợi ý': row['Sản phẩm B'],
                        'Tần suất mua chung': row['Tần suất mua chung'],
                        'Độ tin cậy (%)': row['Độ tin cậy (A -> B)'] * 100
                    })
                elif row['Sản phẩm B'] == selected_item:
                    recs.append({
                        'Sản phẩm gợi ý': row['Sản phẩm A'],
                        'Tần suất mua chung': row['Tần suất mua chung'],
                        'Độ tin cậy (%)': row['Độ tin cậy (B -> A)'] * 100
                    })
                    
            recs_df = pd.DataFrame(recs)
            if len(recs_df) > 0:
                recs_df = recs_df.sort_values(by='Độ tin cậy (%)', ascending=False).reset_index(drop=True)
                st.markdown(f"**Danh sách sản phẩm được khách hàng chọn mua kèm nhiều nhất với `{selected_item}`:**")
                st.dataframe(recs_df.style.format({'Độ tin cậy (%)': '{:.1f}%'}), use_container_width=True)
                
                best_rec_item = recs_df.iloc[0]['Sản phẩm gợi ý']
                best_confidence = recs_df.iloc[0]['Độ tin cậy (%)']
            else:
                st.info("Không tìm thấy sản phẩm gợi ý phù hợp cho danh mục này.")
                best_rec_item = None
                
        with col_c2:
            st.markdown("### 💡 Đề xuất Kịch bản Đóng gói Combo & Tác nghiệp (Cross-selling)")
            if best_rec_item:
                st.markdown(f"""
                <div class="cross-sell-box">
                    <strong>📦 Gợi ý chiến dịch: COMBO HOÀN HẢO {selected_item.upper()} & {best_rec_item.upper()}</strong><br><br>
                    • <strong>Lý do khoa học:</strong> Khách hàng mua dòng sản phẩm <em>{selected_item}</em> có đến <strong>{best_confidence:.1f}%</strong> tỷ lệ sẽ mua kèm thêm <em>{best_rec_item}</em> ngay trong cùng một đơn hàng.<br>
                    • <strong>Đề xuất hành động kinh doanh:</strong>
                      1. <strong>Sắp xếp kệ hàng thực tế:</strong> Đặt hai kệ hàng của {selected_item} và {best_rec_item} gần nhau hoặc trưng bày trực tiếp tại khu vực quầy thu ngân để kích thích mua hàng ngẫu hứng.<br>
                      2. <strong>Khuyến mãi đóng gói:</strong> Tạo chiến dịch mua combo <em>{selected_item} + {best_rec_item}</em> giảm giá trực tiếp 5% so với mua riêng lẻ.<br>
                      3. <strong>Bán kèm trên Website e-Commerce:</strong> Tự động hiển thị đề xuất: <em>"Những người mua {selected_item} cũng thích mua {best_rec_item}"</em> ngay tại bước thanh toán.<br>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Hãy chọn một sản phẩm hợp lệ bên trái để hiển thị kịch bản đề xuất chi tiết.")
                
        # 4. Top 10 cặp sản phẩm mua kèm nhiều nhất toàn hệ thống
        st.divider()
        st.markdown("### 🏆 Top 10 cặp danh mục sản phẩm mua chung nhiều nhất hệ thống")
        top_10_pairs = pairs_df.head(10)
        st.dataframe(top_10_pairs.style.format({
            'Độ hỗ trợ (Support)': '{:.4f}',
            'Độ tin cậy (A -> B)': '{:.2%}',
            'Độ tin cậy (B -> A)': '{:.2%}'
        }), use_container_width=True)

# Inject Floating Chat
render_floating_chat(df, rfm_df)
