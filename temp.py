import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

df = pd.read_csv('Data/Dataset_features.csv')

# print("=== Список всех мышечных групп в датасете ===")
# print(sorted(df['BodyPart'].unique()))

major_muscle_groups = [
    'Quadriceps', 'Hamstrings', 'Chest', 'Lats', 'Lower Back', 'Glutes', 
    'Middle Back', 'Shoulders', 'Traps'
]
compound_equipment = ['Barbell', 'Kettlebells', 'Dumbbell', 'Smith Machine']

def check_compound_v2(row):
    if row['Type'] in ['Powerlifting', 'Olympic Weightlifting', 'Plyometrics']:
        return 1
    
    if (row['Type'] == 'Strength') and \
       (row['Equipment'] in compound_equipment) and \
       (row['BodyPart'] in major_muscle_groups):
        return 1
    
    return 0

df['Is_Compound'] = df.apply(check_compound_v2, axis=1)

df.to_csv('Data/Dataset_features.csv', index=False)