import pandas as pd
import streamlit as st
from sklearn.preprocessing import MinMaxScaler

class DataLoader:
    def __init__(self, path):
        self.path = path

    @st.cache_data
    def load_data(_self):
        try:
            df = pd.read_csv(_self.path)

            level_map = {'Beginner': 0, 'Intermediate': 1, 'Expert': 2}
            df['Base_Score'] = df['Level'].apply(lambda x: level_map.get(x, 2))

            complexity_keywords = {
                'one arm': 1.0,      
                'one leg': 1.0,
                'weighted': 0.5,     # Доп вес усложняет
                'decline': 1,        # Наклон вниз сложнее
                'incline': 0.3,      # Наклон вверх чуть сложнее базы (иногда)
                'side to side': 0.6, # Сложная координация
                'alternating': 0.4,  # Переменные движения
                'plyo': 1.0,         # Плиометрика всегда сложная
                'explosive': 1.0,
                'clapping': 1.5,     # Отжимания с хлопком - точно не для новичков
                'behind the neck': 0.8, # Травмоопасно и сложно
                'wide grip': 0.2,    # Чуть сложнее балансировать
            }

            def adjust_score(row):
                score = row['Base_Score']
                title_lower = str(row['Title']).lower()
                
                for word, penalty in complexity_keywords.items():
                    if word in title_lower:
                        score += penalty
                
                return score

            df['Advanced_Score'] = df.apply(adjust_score, axis=1)

            scaler = MinMaxScaler()
            df['Level_Score'] = scaler.fit_transform(df[['Advanced_Score']])
            
            df['Desc'] = df['Desc'].fillna("")

            return df
        except FileNotFoundError:
            st.error(f"Ошибка: Файл не найден по пути: {_self.path}")
            return pd.DataFrame()