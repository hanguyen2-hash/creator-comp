import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. BACKEND LOGIC
# ==========================================
class CampaignOptimizer:
    def __init__(self):
        self.tiers = ['1K to <10K', '10K to <50K', '50K to <150K', '150K to < 500K', '500K and up']
        self.tier_groups = {
            'Nano (1K-10K)':     ['1K to <10K'],
            'Micro (10K-50K)':   ['10K to <50K'],
            'Mid (50K-150K)':    ['50K to <150K'],
            'Macro (150K-500K)': ['150K to < 500K'],
            'Mega (>500K)':      ['500K and up']
        }
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

    def optimize_segment(self, segment_budget, target_tiers, content_per_kol, selected_platforms):
        """
        Optimizes for a specific budget segment, filtered by tiers AND platforms.
        """
        if segment_budget <= 0: return pd.DataFrame()
        
        # FILTER: Only keep rows where Tier is in target_tiers AND Platform is in selected_platforms
        mask = (self.df_model['Tier'].isin(target_tiers)) & (self.df_model['Platform'].isin(selected_platforms))
        df = self.df_model[mask].copy()
        
        if df.empty: return pd.DataFrame()

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

    def optimize_allocation(self, total_budget, allocations, content_per_kol, selected_platforms):
        final_results = []
        unused_budget = 0
        
        # Iterate through each allocation group (Nano, Micro, etc.)
        for group_name, percent in allocations.items():
            sub_budget = total_budget * percent
            target_tiers = self.tier_groups[group_name]
            
            # Pass selected_platforms to the segment optimizer
            res_df = self.optimize_segment(sub_budget, target_tiers, content_per_kol, selected_platforms)
            
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
# 2. STREAMLIT UI
# ==========================================
st.set_page_config(page_title="Auto-Balancing Planner", layout="wide", page_icon="⚖️")

st.title("⚖️ Smart Budget Planner (Multi-Platform)")
st.markdown("Optimize budget allocation across different tiers and **specific platforms**.")

# --- HISTORICAL TEMPLATES ---
HISTORICAL_TEMPLATES = {
    "Custom (Manual)": 
        {'micro': 20, 'mid': 20, 'macro': 20, 'mega': 20, 'desc': "Fully manual adjustment."},
    
    "🚀 Launching (Mass Seeding)": 
        {'micro': 30, 'mid': 20, 'macro': 0, 'mega': 0, 
         'desc': "Micro & Mid take 50%, remaining 50% for Nano seeding."},
         
    "💎 Branding (Big Image)": 
        {'micro': 0, 'mid': 10, 'macro': 40, 'mega': 50, 
         'desc': "90% budget for Macro & Mega. Nano drops to 0."},
}

# --- SESSION STATE ---
defaults = {'micro': 20, 'mid': 20, 'macro': 20, 'mega': 20}
for k, v in defaults.items():
    if f'alloc_{k}' not in st.session_state:
        st.session_state[f'alloc_{k}'] = v

def update_sliders():
    selected = st.session_state.template_selector
    vals = HISTORICAL_TEMPLATES[selected]
    st.session_state['alloc_micro'] = vals['micro']
    st.session_state['alloc_mid'] = vals['mid']
    st.session_state['alloc_macro'] = vals['macro']
    st.session_state['alloc_mega'] = vals['mega']
    if selected != "Custom (Manual)":
        st.toast(f"Template applied: {selected}", icon="✅")

# --- SIDEBAR ---
st.sidebar.header("1. Configuration")
budget_input = st.sidebar.number_input("Total Budget ($)", value=22000, step=1000)
content_input = st.sidebar.number_input("Content per KOL", value=1, min_value=1)

# === NEW: PLATFORM SELECTION ===
st.sidebar.markdown("---")
st.sidebar.header("2. Platform Strategy")
available_platforms = ['Instagram', 'TikTok', 'Twitter']
selected_platforms = st.sidebar.multiselect(
    "Select Active Platforms:",
    options=available_platforms,
    default=available_platforms, # Default selects all
    help="The optimizer will only buy KOLs from these platforms."
)

if not selected_platforms:
    st.sidebar.error("⚠️ Please select at least one platform!")
    valid_platforms = False
else:
    valid_platforms = True

st.sidebar.markdown("---")
st.sidebar.header("3. Objective Strategy")
template_choice = st.sidebar.selectbox(
    "Objective:",
    options=list(HISTORICAL_TEMPLATES.keys()),
    index=0,
    key="template_selector",
    on_change=update_sliders
)
st.sidebar.info(HISTORICAL_TEMPLATES[template_choice]['desc'])

st.sidebar.markdown("---")
st.sidebar.header("4. Allocation (Nano Auto-fills)")

# 4 ACTIVE SLIDERS
a_micro = st.sidebar.slider("Micro (10K-50K)", 0, 100, st.session_state['alloc_micro'], key="slider_micro")
a_mid = st.sidebar.slider("Mid (50K-150K)", 0, 100, st.session_state['alloc_mid'], key="slider_mid")
a_macro = st.sidebar.slider("Macro (150K-500K)", 0, 100, st.session_state['alloc_macro'], key="slider_macro")
a_mega = st.sidebar.slider("Mega (>500K)", 0, 100, st.session_state['alloc_mega'], key="slider_mega")

# CALCULATE NANO
total_others = a_micro + a_mid + a_macro + a_mega
a_nano_calc = 100 - total_others

valid_alloc = False
if a_nano_calc < 0:
    st.sidebar.error(f"⚠️ Total is {total_others}%. Reduce by {abs(a_nano_calc)}%!")
    st.sidebar.progress(100, text="Nano: 0% (Over Budget)")
else:
    st.sidebar.slider(f"✅ Nano (1K-10K) - Auto Balanced", 0, 100, a_nano_calc, disabled=True, key="slider_nano_display")
    valid_alloc = True

# --- MAIN APP ---
optimizer = CampaignOptimizer()

# Only run if both Platforms and Allocation are valid
if valid_platforms and valid_alloc and st.button("🚀 Optimize Budget", type="primary"):
    
    alloc_map = {
        'Nano (1K-10K)':     a_nano_calc / 100.0,
        'Micro (10K-50K)':   a_micro / 100.0,
        'Mid (50K-150K)':    a_mid / 100.0,
        'Macro (150K-500K)': a_macro / 100.0,
        'Mega (>500K)':      a_mega / 100.0
    }
    
    # Pass selected_platforms to the optimizer
    result_df, remainder = optimizer.optimize_allocation(budget_input, alloc_map, content_input, selected_platforms)
    
    if result_df.empty:
        st.warning("No optimal plan found. Try increasing budget or selecting more platforms.")
    else:
        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Est. Reach", f"{result_df['Total_Reach'].sum():,.0f}")
        c2.metric("Total KOLs", f"{result_df['Participants'].sum():,.0f}")
        c3.metric("Total Spend", f"${result_df['Total_Cost'].sum():,.0f}")
        c4.metric("Remaining Budget", f"${remainder:,.0f}")
        
        st.divider()
        
        # Charts
        c_chart, c_data = st.columns([1, 1])
        
        with c_chart:
            st.subheader("💰 Spend by Platform")
            # Group by Platform to see where money goes
            plat_spend = result_df.groupby('Platform')['Total_Cost'].sum().reset_index()
            st.bar_chart(plat_spend.set_index('Platform'))
            
        with c_data:
            st.subheader("📊 Reach Distribution")
            tier_order = ['Nano (1K-10K)', 'Micro (10K-50K)', 'Mid (50K-150K)', 'Macro (150K-500K)', 'Mega (>500K)']
            reach_df = result_df.groupby('Group')['Total_Reach'].sum().reindex(tier_order, fill_value=0).reset_index()
            st.bar_chart(reach_df.set_index('Group'), color="#00CC96")

        # Table
        st.subheader("📋 Detailed Plan")
        summary = result_df.groupby(['Group', 'Platform']).agg({
            'Participants': 'sum', 
            'Total_Cost': 'sum',
            'Total_Reach': 'sum'
        }).reset_index()
        
        summary['Total_Cost'] = summary['Total_Cost'].apply(lambda x: f"${x:,.0f}")
        summary['Total_Reach'] = summary['Total_Reach'].apply(lambda x: f"{x:,.0f}")
        
        st.dataframe(
            summary, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Participants": "KOL Count",
                "Total_Cost": "Cost",
                "Total_Reach": "Est. Reach"
            }
        )
