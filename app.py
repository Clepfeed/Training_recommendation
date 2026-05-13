import streamlit as st
import pandas as pd

from Src.data_loader import DataLoader
from Src.filters import SafetyFilter
from Src.recommender import RecommenderSystem
from Src.template_engine import TemplateEngine
from Src.feedback import FeedbackManager

st.set_page_config(
    page_title="AI Fitness Trainer",
    layout="wide",
)

# --- ФУНКЦИЯ ПОИСКА ЗАМЕНЫ ---
def find_alternative(current_row, df_pool, user_level_val, blacklist):
    """
    Ищет замену упражнению, сохраняя тип (База/Изоляция) и Мышцу.
    """
    is_compound = 1 if "Базовое" in current_row['Slot_Type'] else 0
    target_muscle = current_row['Target_Muscle']
    
    # Фильтруем пул: Та же мышца + Тот же тип + Не в черном списке + Не само себя
    candidates = df_pool[
        (df_pool['BodyPart'] == target_muscle) &
        (df_pool['Is_Compound'] == is_compound) &
        (~df_pool['Title'].isin(blacklist)) & 
        (df_pool['Title'] != current_row['Title'])
    ]
    
    if candidates.empty:
        return None
    
    # Запускаем k-NN на кандидатах
    rec_sys = RecommenderSystem(candidates)
    
    # Ищем топ-1 самое похожее
    new_rec = rec_sys.get_recommendations(
        target_muscle=target_muscle,
        target_level=user_level_val,
        top_k=1
    )
    
    if new_rec.empty:
        return None
        
    # Возвращаем новую строку, сохраняя метаданные слота
    new_row = new_rec.iloc[0].copy()
    new_row['Slot_Type'] = current_row['Slot_Type']
    new_row['Target_Muscle'] = current_row['Target_Muscle']
    
    return new_row

def main():
    st.title("AI Personal Trainer (Курсовой проект)")
    
    feedback_manager = FeedbackManager()

    data_path = "Data/Dataset_features.csv"
    loader = DataLoader(data_path)
    df = loader.load_data()

    if df.empty:
        st.error(f"Файл {data_path} не найден или пуст.")
        st.stop()

    # --- 1. SIDEBAR ---
    st.sidebar.header("Профиль пользователя")

    all_equipment = sorted(df['Equipment'].unique().tolist())
    if 'Body Only' in all_equipment:
        all_equipment.remove('Body Only')
        
    presets = {
            "Свой выбор": [],
            "Дома (Минимум)": ['Body Only', 'Bands', 'Foam Roll'],
            "Дома (Гантели)": ['Body Only', 'Bands', 'Dumbbell', 'Kettlebells', 'Foam Roll'],
            "Полный зал": all_equipment,
            "Улица (Воркаут)": ['Body Only', 'Bands']
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
        on_change=on_preset_change
    )

    user_equipment = st.sidebar.multiselect(
        "Ваше оборудование:",
        options=all_equipment,
        key="selected_equipment" 
    )
    
    st.sidebar.divider()
    injury_options = ['Knee (Колени)', 'Spine (Позвоночник)', 'Shoulder (Плечи)']
    user_injuries = st.sidebar.multiselect(
        "Ограничения по здоровью:",
        options=injury_options
    )

    # --- SAFETY LAYER ---
    safety = SafetyFilter(df)
    df_filtered = safety.filter_data(user_equipment, user_injuries)

    st.markdown("### Статистика фильтрации (Safety Layer)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Всего упражнений", len(df))
    col2.metric("Доступно (Safe)", len(df_filtered))
    col3.metric("Отфильтровано", len(df) - len(df_filtered), delta_color="inverse")

    if df_filtered.empty:
        st.error("Нет доступных упражнений после фильтрации. Добавьте оборудование.")
        st.stop()

    st.divider()

    # --- 2. RELEVANCE LAYER (SEARCH) ---
    st.markdown("### Точечный поиск (k-NN)")

    col_search1, col_search2, col_search3 = st.columns([2, 2, 1])
    
    with col_search1:
        available_muscles = sorted(df_filtered['BodyPart'].unique())
        target_muscle = st.selectbox("Целевая мышца:", available_muscles)

    with col_search2:
        level_opts = {'Beginner': 0.0, 'Intermediate': 0.5, 'Expert': 1.0}
        target_level_str = st.select_slider(
            "Уровень сложности:", 
            options=['Beginner', 'Intermediate', 'Expert'],
            value='Intermediate'
        )
        target_level_val = level_opts[target_level_str]

    with col_search3:
        st.write("")
        st.write("") 
        run_btn = st.button("Найти упражнения", type="secondary", use_container_width=True)

    if run_btn:
        recommender = RecommenderSystem(df_filtered)
        recs = recommender.get_recommendations(target_muscle, target_level_val, top_k=5)

        st.success(f"Топ-5 рекомендаций для: **{target_muscle}**")
        
        for i, row in recs.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                with c1:
                    st.subheader(f"{row['Title']}")
                    st.caption(f"{row['Equipment']} | {row['Type']}")
                    desc = str(row['Desc'])
                    if len(desc) > 5:
                        st.write(f"_{desc[:100]}..._")
                with c2:
                    st.metric("Score", f"{row['Similarity']:.2f}")
                with c3:
                    with st.popover("Оценить"):
                        st.write(row['Title'])
                        rate = st.slider("Оценка", 1, 10, 5, key=f"s_rate_{i}")
                        if st.button("Сохранить", key=f"s_save_{i}"):
                            feedback_manager.save_feedback(row['Title'], row['BodyPart'], rate, "Search")
                            st.toast("Сохранено!")

    st.divider()

    # --- 3. TEMPLATE ENGINE (GENERATOR) ---
    st.markdown("### Генератор тренировки (Template Engine)")

    # Инициализация состояния (чтобы план не исчезал при кликах)
    if 'workout_plan' not in st.session_state:
        st.session_state.workout_plan = None
    if 'cooldown_plan' not in st.session_state:
        st.session_state.cooldown_plan = None
    if 'blacklist' not in st.session_state:
        st.session_state.blacklist = set() # Список удаленных упражнений

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        target_muscles_gen = st.multiselect(
            "Выберите целевые мышцы (Сплит):", 
            options=available_muscles,
            default=available_muscles[:2] if len(available_muscles) > 1 else available_muscles[:1]
        )
    with col_t2:
        duration = st.select_slider(
            "Длительность тренировки (мин):", 
            options=[45, 60, 90, 120], 
            value=60
        )

    # Кнопка СГЕНЕРИРОВАТЬ
    if st.button("Сгенерировать новую программу", type="primary", use_container_width=True):
        if not target_muscles_gen:
            st.warning("Выберите хотя бы одну группу мышц!")
            st.stop()

        engine = TemplateEngine(df_filtered)
        
        with st.spinner("Генерация плана..."):
            result = engine.generate_workout(
                target_muscles=target_muscles_gen,
                duration=duration,
                user_level_val=target_level_val,
                user_level_str=target_level_str
            )

        if result['error']:
            st.error(result['message'])
        else:
            # СОХРАНЯЕМ В SESSION STATE
            st.session_state.workout_plan = result['plan'].reset_index(drop=True)
            st.session_state.cooldown_plan = result['cooldown'].reset_index(drop=True)
            st.session_state.blacklist = set() # Очищаем черный список
            st.rerun() # Перезагрузка страницы для отображения

    # --- ОТОБРАЖЕНИЕ ПЛАНА (ИЗ ПАМЯТИ) ---
    if st.session_state.workout_plan is not None:
        workout_plan = st.session_state.workout_plan
        cooldown_plan = st.session_state.cooldown_plan

        st.success(f"Тренировка активна! Упражнений: {len(workout_plan)}")
        
        with st.expander("Разминка (15 мин)", expanded=False):
            st.markdown("- 5 мин: Кардио\n- 5 мин: Суставная\n- 5 мин: Динамическая")

        st.markdown("#### План тренировки")
        
        # Цикл по упражнениям с логикой замены
        for i in range(len(workout_plan)):
            row = workout_plan.iloc[i]
            badge = "БАЗА" if "Базовое" in row['Slot_Type'] else "ИЗОЛЯЦИЯ"
            
            with st.container(border=True):
                # 4 колонки: Инфо, Метрика, Кнопка Скип, Кнопка Оценки
                c1, c2, c3, c4 = st.columns([0.5, 0.15, 0.15, 0.2])
                
                with c1:
                    st.markdown(f"**{i+1}. {row['Title']}**")
                    st.caption(f"{badge} • {row['Target_Muscle']}")
                    desc = str(row['Desc'])
                    if len(desc) > 10:
                        with st.popover("Техника"):
                            st.write(desc)
                
                with c2:
                    st.metric("Relevance", f"{row['Similarity']:.2f}")

                # КНОПКА ЗАМЕНЫ
                with c3:
                    st.write("") # Отступ вниз
                    if st.button("🔄 Скип", key=f"swap_{i}", help="Заменить упражнение"):
                        feedback_manager.log_skip(row['Title'], row['BodyPart'])
                        
                        # 1. Добавляем в черный список
                        st.session_state.blacklist.add(row['Title'])
                        # 2. Ищем замену
                        new_row = find_alternative(
                            current_row=row,
                            df_pool=df_filtered,
                            user_level_val=target_level_val,
                            blacklist=st.session_state.blacklist
                        )
                        # 3. Обновляем план
                        if new_row is not None:
                            st.session_state.workout_plan.iloc[i] = new_row
                            st.toast(f"Заменено на: {new_row['Title']}")
                            st.rerun()
                        else:
                            st.error("Нет замен!")

                with c4:
                    st.write("")
                    with st.popover("Оценить"):
                        st.write(f"**{row['Title']}**")
                        u_rate = st.slider("Польза", 1, 10, 5, key=f"gen_rate_{i}")
                        u_diff = st.radio("Сложность", ["Легко", "Норма", "Сложно"], index=1, key=f"gen_diff_{i}")
                        
                        if st.button("Отправить", key=f"gen_btn_{i}"):
                            feedback_manager.save_feedback(row['Title'], row['BodyPart'], u_rate, u_diff)
                            st.toast("Сохранено!")

        # Заминка
        if duration >= 90 and cooldown_plan is not None:
            with st.expander("Заминка (Cool-down) — 10 мин", expanded=True):
                if cooldown_plan.empty:
                    st.info(f"Просто потянитесь.")
                else:
                    for j, row in cooldown_plan.iterrows():
                        st.markdown(f"**{j+1}. {row['Title']}** ({row['BodyPart']})")
                        with st.popover(f"Техника"):
                             st.write(str(row['Desc']))

# if __name__ == "__main__":
#     main()

    # ... (код main заканчивается)

# --- БЛОК АНАЛИТИКИ ДЛЯ ПРЕЗЕНТАЦИИ ---
def show_analytics():
    st.title("📊 Аналитическая панель (Admin Dashboard)")
    
    try:
        # Загружаем лог фидбека
        fb_df = pd.read_csv("data/user_feedback.csv")
        fb_df = fb_df.sort_values(by='Timestamp', ascending=False)
        if fb_df.empty:
            st.warning("Нет данных для анализа.")
            return
    except FileNotFoundError:
        st.error("Файл фидбека не найден.")
        return

    # 1. Метрики (KPI)
    st.markdown("### 1. Общие показатели")
    col1, col2, col3 = st.columns(3)
    
    total_actions = len(fb_df)
    # Скипы - это там, где рейтинг -1
    total_skips = len(fb_df[fb_df['User_Rating_1_10'] == -1])
    # Средний рейтинг (считаем только для реальных оценок > 0)
    real_ratings = fb_df[fb_df['User_Rating_1_10'] > 0]
    avg_rating = real_ratings['User_Rating_1_10'].mean() if not real_ratings.empty else 0

    col1.metric("Всего взаимодействий", total_actions)
    col2.metric("Количество замен (Skips)", total_skips, delta_color="inverse")
    col3.metric("Средняя оценка (CSAT)", f"{avg_rating:.1f}/10")

    st.divider()

    # 2. Графики
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Распределение оценок")
        # Гистограмма оценок (исключая скипы)
        if not real_ratings.empty:
            st.bar_chart(real_ratings['User_Rating_1_10'].value_counts().sort_index())
            st.caption("Показывает удовлетворенность пользователей (без учета скипов).")
        else:
            st.info("Нет оценок.")

    with c2:
        st.subheader("Валидация сложности")
        # Анализ колонки Perceived_Difficulty
        # Исключаем 'SKIPPED'
        diff_data = fb_df[fb_df['Perceived_Difficulty'] != 'SKIPPED']
        if not diff_data.empty:
            df_counts = diff_data['Perceived_Difficulty'].value_counts()
            st.bar_chart(df_counts, color="#ffaa00") # Оранжевый цвет
            st.caption("Расхождение между датасетом и реальностью. Столбцы 'Легче/Сложнее' указывают на ошибки разметки.")
        else:
            st.info("Нет данных о сложности.")

    # 3. Топ проблемных упражнений
    st.subheader("🚨 Топ-5 упражнений, которые чаще всего пропускают")
    if total_skips > 0:
        skips_df = fb_df[fb_df['User_Rating_1_10'] == -1]
        top_skips = skips_df['Exercise'].value_counts().head(5)
        st.bar_chart(top_skips, horizontal=True, color="#ff4b4b") # Красный цвет
        st.caption("Эти упражнения — кандидаты на понижение в ранжировании.")
    else:
        st.write("Пока никто ничего не скипнул.")

    # Показать сырые данные
    with st.expander("Просмотр сырых данных (Log)"):
        st.dataframe(fb_df)

# Модификация запуска (Добавь это ВМЕСТО старого if __name__ == "__main__": main())
if __name__ == "__main__":
    # Добавляем переключатель в сайдбар
    mode = st.sidebar.radio("Режим:", ["Пользователь", "Администратор (Аналитика)"])
    
    if mode == "Пользователь":
        main()
    else:
        show_analytics()