import pandas as pd
from Src.recommender import RecommenderSystem

class TemplateEngine:
    def __init__(self, df):
        self.df = df
        self.recommender = RecommenderSystem(df)

    def calculate_slots(self, duration_minutes, user_level_str):
        WARMUP_TIME = 15
        COOLDOWN_TIME = 10 if duration_minutes >= 90 else 0
        
        available_time = duration_minutes - WARMUP_TIME - COOLDOWN_TIME
        
        sets_map = {'Beginner': 3, 'Intermediate': 3, 'Expert': 4}
        n_sets = sets_map.get(user_level_str, 3)
        
        time_per_ex = (n_sets * 4) + 3
        n_slots = int(available_time // time_per_ex)
        
        # print(n_slots, available_time, time_per_ex)

        return max(1, min(n_slots, 15))

    def generate_workout(self, target_muscles, duration, user_level_val, user_level_str):
        # 1. Расчет слотов
        total_slots = self.calculate_slots(duration, user_level_str)

        if total_slots < len(target_muscles):
            return {
                "error": True, 
                "message": f"Время ({duration} мин) слишком короткое для {len(target_muscles)} групп мышц. Увеличьте время."
            }

        slots_per_muscle = total_slots // len(target_muscles)
        extra_slots = total_slots % len(target_muscles)
        
        used_ids = set()
        exercises_by_muscle = {muscle: [] for muscle in target_muscles}

        # 2. Генерация основного блока
        for i, muscle in enumerate(target_muscles):
            target_count = slots_per_muscle + (1 if i < extra_slots else 0)

            plan_compound = target_count // 2
            if plan_compound < 1 and target_count > 0: plan_compound = 1
            
            # --- База ---
            df_comp = self.df[(self.df['Is_Compound'] == 1) & (self.df['BodyPart'] == muscle)]
            found_compound_count = 0
            
            if not df_comp.empty:
                rec_sys_comp = RecommenderSystem(df_comp)
                recs_comp = rec_sys_comp.get_recommendations(muscle, user_level_val, top_k=plan_compound * 5)
                
                for _, row in recs_comp.iterrows():
                    if found_compound_count >= plan_compound: break
                    if row['Title'] not in used_ids:
                        row['Slot_Type'] = 'Базовое (Compound)'
                        row['Target_Muscle'] = muscle
                        exercises_by_muscle[muscle].append(row)
                        used_ids.add(row['Title'])
                        found_compound_count += 1

            # --- Изоляция ---
            n_isolation_needed = target_count - found_compound_count
            if n_isolation_needed > 0:
                df_iso = self.df[(self.df['Is_Compound'] == 0) & (self.df['BodyPart'] == muscle)]
                if not df_iso.empty:
                    rec_sys_iso = RecommenderSystem(df_iso)
                    recs_iso = rec_sys_iso.get_recommendations(muscle, user_level_val, top_k=n_isolation_needed * 5)
                    
                    found_iso_count = 0
                    for _, row in recs_iso.iterrows():
                        if found_iso_count >= n_isolation_needed: break
                        if row['Title'] not in used_ids:
                            row['Slot_Type'] = 'Изолирующее (Isolation)'
                            row['Target_Muscle'] = muscle
                            exercises_by_muscle[muscle].append(row)
                            used_ids.add(row['Title'])
                            found_iso_count += 1

        # 3. Чередование (Interleaving)
        final_workout_list = []
        max_len = max([len(exs) for exs in exercises_by_muscle.values()]) if exercises_by_muscle else 0
        for i in range(max_len):
            for muscle in target_muscles:
                ex_list = exercises_by_muscle[muscle]
                if i < len(ex_list):
                    final_workout_list.append(ex_list[i])
        
        # --- 4. Генерация ЗАМИНКИ (Stretching) ---
        cooldown_list = []
        # Мы генерируем растяжку всегда, а показывать её или нет — решит app.py в зависимости от времени
        for muscle in target_muscles:
            # Ищем упражнения типа Stretching для этой мышцы
            df_stretch = self.df[
                (self.df['Type'] == 'Stretching') & 
                (self.df['BodyPart'] == muscle)
            ]
            
            if not df_stretch.empty:
                # Используем рекомендер, чтобы подобрать растяжку под уровень пользователя
                rec_stretch = RecommenderSystem(df_stretch)
                # Берем ТОП-1 упражнение
                best_stretch = rec_stretch.get_recommendations(muscle, user_level_val, top_k=1)
                
                if not best_stretch.empty:
                    row = best_stretch.iloc[0].copy()
                    row['Slot_Type'] = 'Растяжка (Cool-down)'
                    cooldown_list.append(row)

        return {
            "error": False, 
            "plan": pd.DataFrame(final_workout_list),
            "cooldown": pd.DataFrame(cooldown_list) # <-- Возвращаем отдельный датафрейм
        }