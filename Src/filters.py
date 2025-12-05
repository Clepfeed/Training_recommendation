import pandas as pd

class SafetyFilter:
    INJURY_MAPPING = {
        'Knee (Колени)': 'Knee_Load',
        'Spine (Позвоночник)': 'Spine_Load',
        'Shoulder (Плечи)': 'Overhead_Mvmt'
    }

    def __init__(self, df):
        self.df = df

    def filter_data(self, user_equipment, user_injuries):
        df_safe = self.df.copy()

        if not user_equipment:
            user_equipment = ['Body Only']
            
        valid_equip = set(user_equipment) | {'Body Only'}
        df_safe = df_safe[df_safe['Equipment'].isin(valid_equip)]

        for injury in user_injuries:
            if injury in self.INJURY_MAPPING:
                col_name = self.INJURY_MAPPING[injury]
                df_safe = df_safe[df_safe[col_name] == 0]

        return df_safe