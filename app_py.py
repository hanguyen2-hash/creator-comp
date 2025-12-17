import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. BACKEND LOGIC
# ==========================================
class CampaignOptimizer:
    def __init__(self):
        # Dữ liệu Benchmark (Hardcoded)
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

    def calculate_staff_cost(self, num_kol, num_content, hourly_rate, hours_per_kol, hours_per_content):
        """Tính chi phí nhân sự dựa trên workload"""
        total_hours = (num_kol * hours_per_kol) + (num_content * hours_per_content)
        cost = total_hours * hourly_rate
        return cost, total_hours

    def optimize(self, total_budget, strategy, content_per_kol, staff_params):
        df = self.df_model.copy()
        
        # 1. Filter Strategy
        if strategy == "mass_seeding":
            target_tiers = ['1K to <10K', '10K to <50K']
            df = df[df['Tier'].isin(target_tiers)]

        # 2. Chuẩn bị số liệu
        df['Pack_Cost'] = df['Unit_Price'] * content_per_kol
        df['ROI'] = df['True_Reach'] / df['Pack_Cost']
        df = df.sort_values(by='ROI', ascending=False)
        
        # 3. Allocation Loop
        allocations = []
        remaining_budget = total_budget
        
        # Tạo bảng tạm để lưu kết quả
        df['Participants'] = 0
        
        for index, row in df.iterrows():
            if remaining_budget <= 0:
                continue
            
            unit_price = row['Pack_Cost']
            supply = row['Supply']
            
            # Tính Marginal Op Cost
            marginal_op_cost = (staff_params['setup_time'] + content_per_kol * staff_params['manage_time']) * staff_params['rate']
            
            total_unit_cost = unit_price + marginal_op_cost
            
            if total_unit_cost > remaining_budget:
                count = int(remaining_budget // total_unit_cost)
            else:
                max_buyable = int(remaining_budget // total_unit_cost)
                count = min(max_buyable, supply)
            
            if count > 0:
                df.at[index, 'Participants'] = count
                cost_media = count * unit_price
                cost_op = count * marginal_op_cost
                remaining_budget -= (cost_media + cost_op)

        # 4. Tính toán tổng kết
        df['Media_Cost'] = df['Participants'] * df['Pack_Cost']
        df['Total_True_Reach'] = df['Participants'] * df['True_Reach']
        df['Total_Content'] = df['Participants'] * content_per_kol
        
        # Tính lại Staff Cost chính xác lần cuối
        final_op_cost, final_hours = self.calculate_staff_cost(
            df['Participants'].sum(), 
            df['Total_Content'].sum(),
            staff_params['rate'],
            staff_params['setup_time'],
            staff_params['manage_time']
        )
        
        return df[df['Participants'] > 0].copy(), remaining_budget, final_op_cost, final_hours

# ==========================================
# 2. STREAMLIT UI
# ==========================================
st.set_page_config(page_title="KOL Budget & Staff Optimizer", layout="wide", page_icon="💼")

st.title("💼 KOL Campaign Budget & Staff Workload Optimizer")
st.markdown("Tối ưu ngân sách bao gồm cả **Chi phí Media (Booking)** và **Chi phí Vận hành (Staff Hours)**.")

# --- SIDEBAR ---
st.sidebar.header("1. Ngân sách & Chiến thuật")
budget_input = st.sidebar.number_input("Tổng Ngân sách ($)", value=22000, step=1000)
strategy_mode = st.sidebar.selectbox("Chiến thuật", ("Mass Seeding (Focus 1K-50K)", "Max Reach (All Tiers)"))
strat_key = "mass_seeding" if "Mass Seeding" in strategy_mode else "max_reach"
content_input = st.sidebar.slider("Số post/KOL", 1, 5, 1)

st.sidebar.header("2. Chi phí Nhân sự (Staff)")
hourly_rate = st.sidebar.number_input("Lương nhân viên ($/giờ)", value=20.0, step=5.0)
setup_time = st.sidebar.number_input("Giờ setup mỗi KOL (Tìm, Deal)", value=2.0, step=0.5)
manage_time = st.sidebar.number_input("Giờ quản lý mỗi Post (Duyệt, Report)", value=1.5, step=0.5)

staff_params = {
    'rate': hourly_rate,
    'setup_time': setup_time,
    'manage_time': manage_time
}

# --- MAIN ---
optimizer = CampaignOptimizer()

if st.sidebar.button("🚀 Tính Toán & Tối Ưu", type="primary"):
    with st.spinner('Đang cân đối giữa Booking và Staffing...'):
        result_df, remainder, op_cost, staff_hours = optimizer.optimize(
            budget_input, strat_key, content_input, staff_params
        )

    if result_df.empty:
        st.error("Không thể tối ưu với ngân sách này (Chi phí vận hành có thể quá cao).")
    else:
        # Metrics
        media_spend = result_df['Media_Cost'].sum()
        total_reach = result_df['Total_True_Reach'].sum()
        total_kols = result_df['Participants'].sum()
        
        # Layout Top
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng Reach Thực Tế", f"{total_reach:,.0f}")
        c2.metric("Số lượng KOLs", f"{total_kols:,.0f} người")
        c3.metric("Tổng Giờ Công (Staff Hours)", f"{staff_hours:,.1f} giờ", help="Tổng thời gian cần thiết để vận hành campaign này")

        st.divider()

        # Breakdown Budget (Visual quan trọng)
        st.subheader("💸 Phân bổ Ngân sách Tổng ($)")
        
        col_chart, col_data = st.columns([1, 1])
        
        with col_chart:
            # SỬA LỖI: Dùng Bar Chart đơn giản thay vì Altair Pie Chart gây lỗi
            cost_data = pd.DataFrame({
                'Category': ['1. Booking (Media)', '2. Staff Ops', '3. Dư (Buffer)'],
                'Amount': [media_spend, op_cost, remainder]
            })
            st.bar_chart(cost_data.set_index('Category'))
            
        with col_data:
            st.write(f"**1. Chi phí Booking (Media):** ${media_spend:,.2f}")
            st.write(f"**2. Chi phí Vận hành (Staff):** ${op_cost:,.2f} ({op_cost/budget_input*100:.1f}%)")
            st.write(f"   - Đơn giá: ${hourly_rate}/h")
            st.write(f"   - Tổng giờ: {staff_hours:.1f}h")
            st.write(f"**3. Dư:** ${remainder:,.2f}")
            st.markdown("---")
            if staff_hours > 160: 
                st.warning(f"⚠️ Cảnh báo: {staff_hours:.0f} giờ tương đương khối lượng công việc của ~{staff_hours/160:.1f} nhân viên full-time trong 1 tháng!")

        # Detailed Table
        st.subheader("📋 Danh sách KOL phân bổ")
        # Format cột tiền tệ hiển thị cho đẹp
        display_df = result_df[['Platform', 'Tier', 'Participants', 'Total_Content', 'Media_Cost', 'Total_True_Reach']].copy()
        display_df.rename(columns={'Media_Cost': 'Media Cost ($)', 'Participants': 'KOLs'}, inplace=True)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "Media Cost ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Total_True_Reach": st.column_config.NumberColumn(format="%d")
            }
        )

else:
    st.info("👈 Nhập thông số Staff Cost ở Sidebar để thấy sự ảnh hưởng đến ngân sách.")
