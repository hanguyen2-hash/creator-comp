import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. BACKEND LOGIC
# ==========================================
class CampaignOptimizer:
    def __init__(self):
        # Dữ liệu gốc
        self.tiers = ['1K to <10K', '10K to <50K', '50K to <150K', '150K to < 500K', '500K and up']
        
        # Mapping 1-1 cho 5 nhóm
        self.tier_groups = {
            'Nano (1K-10K)':     ['1K to <10K'],
            'Micro (10K-50K)':   ['10K to <50K'],
            'Mid (50K-150K)':    ['50K to <150K'],
            'Macro (150K-500K)': ['150K to < 500K'],
            'Mega (>500K)':      ['500K and up']
        }
        
        # Hardcoded Data
        self.raw_data = {
            'Instagram': {
                'Reach': [3258, 21417, 87664, 264830, 2206768],
                'Cost_Post': [268.22, 443.84, 1140.22, 3315.63, 11059.85],
                'Supply': [246209, 68181, 20454, 9461, 5305],
                'Reach_Rate': [0.25, 0.15, 0.10, 0.05, 0.03] 
            },
            'Twitter': {
                'Reach': [4952, 21765, 85206, 266771, 1838483],
                'Cost_Post': [131.34, 207.33, 504.2, 1490.99, 4656.37],
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
                    'True_Reach': data['Reach'][i] * data['Reach_Rate'][i],
                    'Unit_Price': data['Cost_Post'][i],
                    'Supply': int(data['Supply'][i])
                }
                data_list.append(row)
        return pd.DataFrame(data_list)

    def optimize_segment(self, segment_budget, target_tiers, content_per_kol):
        if segment_budget <= 0: return pd.DataFrame()
        df = self.df_model[self.df_model['Tier'].isin(target_tiers)].copy()
        df['Pack_Cost'] = df['Unit_Price'] * content_per_kol
        df['ROI'] = df['True_Reach'] / df['Pack_Cost']
        df = df.sort_values(by='ROI', ascending=False)
        
        allocations = []
        remaining = segment_budget
        df['Participants'] = 0
        
        for index, row in df.iterrows():
            if remaining <= 0: break
            unit_price = row['Pack_Cost']
            supply = row['Supply']
            if unit_price > remaining:
                count = int(remaining // unit_price)
            else:
                count = min(int(remaining // unit_price), supply)
            if count > 0:
                df.at[index, 'Participants'] = count
                remaining -= count * unit_price
        
        return df[df['Participants'] > 0].copy()

    def optimize_allocation(self, total_budget, allocations, content_per_kol):
        final_results = []
        unused_budget = 0
        for group_name, percent in allocations.items():
            sub_budget = total_budget * percent
            target_tiers = self.tier_groups[group_name]
            res_df = self.optimize_segment(sub_budget, target_tiers, content_per_kol)
            if not res_df.empty:
                res_df['Group'] = group_name
                res_df['Total_Cost'] = res_df['Participants'] * res_df['Pack_Cost']
                res_df['Total_Reach'] = res_df['Participants'] * res_df['True_Reach']
                spent = res_df['Total_Cost'].sum()
                unused_budget += (sub_budget - spent)
                final_results.append(res_df)
            else:
                unused_budget += sub_budget
                
        if final_results:
            return pd.concat(final_results), unused_budget
        return pd.DataFrame(), total_budget

# ==========================================
# 2. STREAMLIT UI - 5 TIERS & HISTORICAL DATA
# ==========================================
st.set_page_config(page_title="5-Tier Campaign Planner", layout="wide", page_icon="⚡")

st.title("⚡ Kế hoạch Phân bổ Ngân sách (5 Nhóm Influencer)")
st.markdown("Tối ưu hóa chi tiết cho 5 phân khúc: **Nano, Micro, Mid, Macro, Mega**.")

# --- DỮ LIỆU HISTORICAL TEMPLATES (Updated for 5 Tiers) ---
HISTORICAL_TEMPLATES = {
    "Tự chỉnh (Custom)": 
        {'nano': 20, 'micro': 20, 'mid': 20, 'macro': 20, 'mega': 20, 'desc': "Tự do điều chỉnh."},
    
    "🚀 Launching (Mass Seeding)": 
        {'nano': 50, 'micro': 30, 'mid': 20, 'macro': 0, 'mega': 0, 
         'desc': "Dồn 80% ngân sách cho Nano & Micro để tạo hiệu ứng 'ai cũng nhắc tới'."},
         
    "💎 Branding (Big Image)": 
        {'nano': 0, 'micro': 0, 'mid': 10, 'macro': 40, 'mega': 50, 
         'desc': "90% ngân sách cho Macro & Mega để xây dựng hình ảnh thương hiệu đẳng cấp."},
         
    "⚖️ Conversion (Performance)": 
        {'nano': 10, 'micro': 40, 'mid': 40, 'macro': 10, 'mega': 0, 
         'desc': "Tập trung mạnh vào Micro & Mid-tier (80%) - nhóm có ROI và Conversion tốt nhất."},
}

# --- SESSION STATE ---
# Khởi tạo mặc định
defaults = {'nano': 20, 'micro': 20, 'mid': 20, 'macro': 20, 'mega': 20}
for k, v in defaults.items():
    if f'alloc_{k}' not in st.session_state:
        st.session_state[f'alloc_{k}'] = v

def update_sliders():
    selected = st.session_state.template_selector
    vals = HISTORICAL_TEMPLATES[selected]
    st.session_state['alloc_nano'] = vals['nano']
    st.session_state['alloc_micro'] = vals['micro']
    st.session_state['alloc_mid'] = vals['mid']
    st.session_state['alloc_macro'] = vals['macro']
    st.session_state['alloc_mega'] = vals['mega']
    if selected != "Tự chỉnh (Custom)":
        st.toast(f"Đã áp dụng mẫu: {selected}", icon="✅")

# --- SIDEBAR CONTROL ---
st.sidebar.header("1. Cấu hình & Ngân sách")
budget_input = st.sidebar.number_input("Tổng Ngân sách ($)", value=22000, step=1000)
content_input = st.sidebar.number_input("Số bài đăng/KOL", value=1, min_value=1)

st.sidebar.markdown("---")
st.sidebar.header("2. Chọn Template Chiến Dịch")
template_choice = st.sidebar.selectbox(
    "Mục tiêu là gì?",
    options=list(HISTORICAL_TEMPLATES.keys()),
    index=1,
    key="template_selector",
    on_change=update_sliders
)
st.sidebar.info(HISTORICAL_TEMPLATES[template_choice]['desc'])

st.sidebar.markdown("---")
st.sidebar.header("3. Điều chỉnh Tỷ lệ (Total: 100%)")

# 5 SLIDERS
col_s1, col_s2, col_s3, col_s4, col_s5 = st.sidebar.columns([1,1,1,1,1]) # Trick to align if needed, but sidebar is vertical
# Vertical Sliders
a_nano = st.sidebar.slider("Nano (1-10K)", 0, 100, st.session_state['alloc_nano'], key="slider_nano")
a_micro = st.sidebar.slider("Micro (10-50K)", 0, 100, st.session_state['alloc_micro'], key="slider_micro")
a_mid = st.sidebar.slider("Mid (50-150K)", 0, 100, st.session_state['alloc_mid'], key="slider_mid")
a_macro = st.sidebar.slider("Macro (150-500K)", 0, 100, st.session_state['alloc_macro'], key="slider_macro")
a_mega = st.sidebar.slider("Mega (>500K)", 0, 100, st.session_state['alloc_mega'], key="slider_mega")

# Validation
total_alloc = a_nano + a_micro + a_mid + a_macro + a_mega
if total_alloc != 100:
    st.sidebar.error(f"⚠️ Tổng: {total_alloc}% (Cần chỉnh về 100%)")
    valid = False
else:
    st.sidebar.success("✅ Tổng: 100% (Hợp lệ)")
    valid = True

# --- MAIN ---
optimizer = CampaignOptimizer()

if valid and st.button("🚀 Chạy Kế Hoạch", type="primary"):
    
    # Map input -> Logic
    alloc_map = {
        'Nano (1K-10K)':     a_nano / 100.0,
        'Micro (10K-50K)':   a_micro / 100.0,
        'Mid (50K-150K)':    a_mid / 100.0,
        'Macro (150K-500K)': a_macro / 100.0,
        'Mega (>500K)':      a_mega / 100.0
    }
    
    result_df, remainder = optimizer.optimize_allocation(budget_input, alloc_map, content_input)
    
    if result_df.empty:
        st.warning("Không tìm thấy phương án tối ưu cho cấu hình này.")
    else:
        # Metrics Row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng Reach (Est)", f"{result_df['Total_Reach'].sum():,.0f}")
        c2.metric("Số lượng KOL", f"{result_df['Participants'].sum():,.0f}")
        c3.metric("Chi tiêu", f"${result_df['Total_Cost'].sum():,.0f}")
        c4.metric("Dư ngân sách", f"${remainder:,.0f}")
        
        st.divider()
        
        # Charts Area
        c_chart, c_data = st.columns([1, 1])
        
        with c_chart:
            st.subheader("💰 Phân bổ tiền tệ")
            # Order tiers for chart logic
            tier_order = ['Nano (1K-10K)', 'Micro (10K-50K)', 'Mid (50K-150K)', 'Macro (150K-500K)', 'Mega (>500K)']
            chart_df = result_df.groupby('Group')['Total_Cost'].sum().reindex(tier_order, fill_value=0).reset_index()
            st.bar_chart(chart_df.set_index('Group'))
            
        with c_data:
            st.subheader("📊 Tỷ trọng Reach")
            reach_df = result_df.groupby('Group')['Total_Reach'].sum().reindex(tier_order, fill_value=0).reset_index()
            st.bar_chart(reach_df.set_index('Group'), color="#00CC96") # Màu khác cho dễ phân biệt

        # Detailed Table
        st.subheader("📋 Kế hoạch chi tiết theo từng Platform")
        
        # Pivot table cho dễ nhìn: Cột là Tier, Dòng là Platform
        summary = result_df.groupby(['Platform', 'Group']).agg({
            'Participants': 'sum',
            'Total_Cost': 'sum'
        }).reset_index()
        
        # Format cột tiền
        summary['Total_Cost'] = summary['Total_Cost'].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(
            summary, 
            use_container_width=True,
            column_order=("Group", "Platform", "Participants", "Total_Cost"),
            hide_index=True
        )
