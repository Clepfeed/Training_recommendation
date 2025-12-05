import streamlit as st
from Src.data_loader import DataLoader
from Src.filters import SafetyFilter

st.set_page_config(page_title="AI Fitness Trainer", layout="wide")

def main():
    st.title("AI Personal Trainer (Курсовой проект)")
    st.markdown("### Модуль 1: Safety Layer (Предварительная фильтрация)")

    data_path = "Data/Dataset_features.csv"
    loader = DataLoader(data_path)
    df = loader.load_data()

    if df.empty:
        st.stop()

    st.sidebar.header("Профиль пользователя")

    all_equipment = sorted(df['Equipment'].unique().tolist())
        
    presets = {
            "Свой выбор": [],
            "Дома (Минимум)": ['Body Only', 'Bands', 'Foam Roll'],
            "Дома (Гантели)": ['Body Only', 'Bands', 'Dumbbell', 'Kettlebells', 'Foam Roll'],
            "Полный зал": all_equipment,
            "Улица": ['Body Only', 'Bands']
        }

    if 'selected_equipment' not in st.session_state:
        st.session_state.selected_equipment = []

    def on_preset_change():
        preset_name = st.session_state.preset_selector
        if preset_name != "Свой выбор":
            valid_items = [item for item in presets[preset_name] if item in all_equipment]
            st.session_state.selected_equipment = valid_items

    st.sidebar.selectbox(
        "Готовые наборы:",
        options=list(presets.keys()),
        index=0,
        key="preset_selector",
        on_change=on_preset_change,
        help="Выберите шаблон, чтобы автоматически отметить нужное оборудование."
    )

    user_equipment = st.sidebar.multiselect(
        "Ваше оборудование:",
        options=all_equipment,
        default=['Dumbbell'],
        key="selected_equipment"
    )
    

    injury_options = ['Knee (Колени)', 'Spine (Позвоночник)', 'Shoulder (Плечи)']
    user_injuries = st.sidebar.multiselect(
        "Есть ли ограничения по здоровью?",
        options=injury_options
    )

    safety = SafetyFilter(df)
    df_filtered = safety.filter_data(user_equipment, user_injuries)



    col1, col2, col3 = st.columns(3)
    col1.metric("Всего упражнений", len(df))
    col2.metric("Доступно (Safe)", len(df_filtered))
    col3.metric("Отфильтровано", len(df) - len(df_filtered), delta_color="inverse")

    st.divider()

    st.subheader("Список доступных упражнений")
    
    if len(df_filtered) == 0:
        st.error("Нет упражнений, соответствующих фильтрам! Попробуйте добавить оборудование.")
    else:
        view_cols = ['Title', 'Type', 'BodyPart', 'Equipment', 'Level']
        st.dataframe(df_filtered[view_cols], use_container_width=True)

        with st.expander("Техническая информация (Debug)"):
            st.write("Проверка наличия опасных флагов в выборке (должны быть 0):")
            st.write(df_filtered[['Knee_Load', 'Spine_Load', 'Overhead_Mvmt']].sum())

if __name__ == "__main__":
    main()