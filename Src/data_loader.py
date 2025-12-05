import pandas as pd
import streamlit as st

class DataLoader:
    def __init__(self, path):
        self.path = path

    @st.cache_data
    def load_data(_self):
        try:
            df = pd.read_csv(_self.path)
            return df
        except FileNotFoundError:
            st.error(f"Ошибка: Файл не найден по пути: {_self.path}")
            return pd.DataFrame()