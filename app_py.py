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
        df
