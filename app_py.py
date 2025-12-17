import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. BACKEND LOGIC (Class xử lý toán học)
# ==========================================
class CampaignOptimizer:
    def __init__(self):
        # Dữ liệu Hardcode từ Excel + Benchmark Reach thực tế
        self.tiers = ['1K to <10K', '10K to <50K', '50K to <150K', '150K to < 500K', '500K and up']
        self.raw_data = {
            'Instagram': {
                'Reach': [3258, 21417, 87664, 264830, 2206768],
                'Cost_Post': [268.22, 443.84, 1140.22, 3315.63, 11059.85],
                'Supply': [246209, 68181, 20454, 9461, 5305],
                'Reach_Rate': [0.25, 0.15, 0.10, 0.05, 0.03] 
            },
            'Twitter': {
                'Reach': [4952, 21765, 85206, 266771, 1838483],
                'Cost_Post': [131.34, 207.33, 504.2, 1490.99, 4656.37], # Cost Tweet
                'Supply': [2907, 2062, 896, 552, 279],
                'Reach_Rate': [0.15, 0.10, 0.08, 0.05, 0.02]
            },
            'TikTok': {
                'Reach': [4373, 25013, 90230, 275338, 2087679],
                'Cost_Post': [184.57, 335.92, 697.04, 1806.5, 5757.25],
                'Supply': [6233, 7449, 4757, 3746, 2601],
                'Reach_Rate': [0.50, 0.30, 0.20, 0.10, 0.05]
            }
        }
        self.df_model = self._build_model()

    def _build_model(self):
        data_list = []
        for platform, data in self.raw_data.items():
            for i, tier in enumerate(self.tiers):
                row = {
                    'Platform': platform,
                    'Tier': tier,
                    'Followers': data['Reach'][i],
                    'True_Reach': data['Reach'][i] * data['Reach_Rate'][i], # Reach thực tế
                    'Unit_Price': data['Cost_Post'][i],
                    'Supply': int(data['Supply'][i])
                }
                data_list.append(row)
        return pd.DataFrame(data_list)

    def optimize(self, budget, strategy, content_per_kol):
        df = self.df_model.copy()
        
        # Lọc chiến thuật
        if strategy == "mass_seeding":
            target_tiers = ['1K to <10K', '10K to <50K']
            df = df[df['Tier'].isin(target_tiers)]
        
        # Tính toán chi phí & ROI
        df['Pack_Cost'] = df['Unit_Price'] * content_per_kol
        df['ROI'] = df['True_Reach'] / df['Pack_Cost']
        df = df.sort_values(by='ROI', ascending=False)
        
        # Phân bổ ngân sách
        allocations = []
        remaining_budget = budget
        
        for index, row in df.iterrows():
            if remaining_budget <= 0:
                allocations.append(0)
                continue
            
            cost = row['Pack_Cost']
            supply = row['Supply']
            
            if cost > 0:
                max_affordable = int(remaining_budget // cost)
                count = min(max_affordable, supply)
            else:
                count = 0
            
            allocations.append(count)
            remaining_budget -= count * cost
            
        df['Participants'] = allocations
        df['Total_Cost'] = df['Participants'] * df['Pack_Cost']
        df['Total_True_Reach'] = df['Participants'] * df['True_Reach']
        df['Total_Content'] = df['Participants'] * content_per_kol
        
        return df[df['Participants'] > 0].copy(), remaining_budget

# ==========================================
# 2. STREAMLIT FRONTEND (Giao diện)
# ==========================================

# Cấu hình trang
st.set_page_config(page_title="KOL Budget Optimizer", layout="wide", page_icon="📊")

# Header
st.title("📊 KOL Campaign Budget Optimizer")
st.markdown("Công cụ tối ưu hóa phân bổ ngân sách Influencer Marketing dựa trên **True Reach**.")

# --- SIDEBAR: INPUT ---
st.sidebar.header("⚙️ Cấu hình Campaign")

# 1. Nhập ngân sách
budget_input = st.sidebar.number_input("Tổng Ngân sách ($)", value=22000, step=1000, format="%d")

# 2. Chọn chiến thuật
strategy_mode = st.sidebar.selectbox(
    "Chiến thuật Campaign",
    ("Mass Seeding (Focus Nano/Micro)", "Max Reach (All Tiers)")
)
# Map selection về key code
strat_key = "mass_seeding" if "Mass Seeding" in strategy_mode else "max_reach"

# 3. Số lượng content
content_input = st.sidebar.slider("Số bài đăng mỗi KOL (Content Count)", 1, 5, 1)

st.sidebar.markdown("---")
st.sidebar.markdown("ℹ️ **Ghi chú:**\n- **Mass Seeding:** Chỉ chọn KOL 1K-50K Follower.\n- **True Reach:** Đã trừ % ảo.")

# --- MAIN: PROCESS ---
optimizer = CampaignOptimizer()

if st.sidebar.button("🚀 Chạy Tối Ưu Hóa", type="primary"):
    with st.spinner('Đang tính toán phân bổ tốt nhất...'):
        result_df, remainder = optimizer.optimize(budget_input, strat_key, content_input)

    # --- MAIN: DISPLAY RESULTS ---
    if result_df.empty:
        st.error("Ngân sách quá thấp, không thể thuê được KOL nào trong nhóm này!")
    else:
        # 1. Key Metrics Row
        total_spend = result_df['Total_Cost'].sum()
        total_reach = result_df['Total_True_Reach'].sum()
        total_kols = result_df['Participants'].sum()
        total_contents = result_df['Total_Content'].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tổng Chi Phí", f"${total_spend:,.2f}", f"Dư: ${remainder:,.2f}")
        col2.metric("Tổng KOLs", f"{total_kols:,.0f} người")
        col3.metric("Tổng Nội Dung", f"{total_contents:,.0f} posts")
        col4.metric("Reach Thực Tế (Est)", f"{total_reach:,.0f} views", delta_color="normal")

        st.markdown("---")

        # 2. Charts & Data Row
        c_chart, c_table = st.columns([1, 2])

        with c_chart:
            st.subheader("💰 Phân bổ theo Platform")
            # Group by Platform để vẽ biểu đồ
            platform_spend = result_df.groupby('Platform')['Total_Cost'].sum().reset_index()
            st.bar_chart(platform_spend, x='Platform', y='Total_Cost', color='Platform')
            
            st.subheader("👥 Phân bổ theo Tier")
            tier_count = result_df.groupby('Tier')['Participants'].sum().reset_index()
            st.dataframe(tier_count, hide_index=True, use_container_width=True)

        with c_table:
            st.subheader("📋 Kế hoạch chi tiết")
            # Format lại bảng cho đẹp
            display_df = result_df[['Platform', 'Tier', 'Participants', 'Total_Content', 'Total_Cost', 'Total_True_Reach']].copy()
            display_df = display_df.rename(columns={
                'Participants': 'Số KOL',
                'Total_Content': 'Số Post',
                'Total_Cost': 'Chi Phí ($)',
                'Total_True_Reach': 'Reach (Est)'
            })
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Chi Phí ($)": st.column_config.NumberColumn(format="$%.2f"),
                    "Reach (Est)": st.column_config.NumberColumn(format="%d")
                }
            )

else:
    st.info("👈 Nhập thông số ở Sidebar và bấm 'Chạy Tối Ưu Hóa' để xem kết quả.")
