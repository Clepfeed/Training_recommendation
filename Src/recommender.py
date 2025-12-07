import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class RecommenderSystem:
    def __init__(self, df):
        self.df = df.reset_index(drop=True)
        
        self.weights = {
            'body': 0.6,
            'equip': 0.3,
            'level': 0.4
        }

    def get_recommendations(self, target_muscle, target_level, top_k=5):
        feature_cols = [c for c in self.df.columns if c.startswith('Part_') or c.startswith('Equip_')]
        if 'Level_Score' in self.df.columns:
            feature_cols.append('Level_Score')

        if self.df.empty:
            return pd.DataFrame()

        query_vector = pd.DataFrame(0, index=[0], columns=feature_cols)

        target_part_col = f"Part_{target_muscle}"
        if target_part_col in query_vector.columns:
            query_vector[target_part_col] = 1 * self.weights['body']


        query_vector['Level_Score'] = target_level * self.weights['level']

        
        candidates_matrix = self.df[feature_cols].copy()

        for col in candidates_matrix.columns:
            if col.startswith('Part_'):
                candidates_matrix[col] *= self.weights['body']
            elif col.startswith('Equip_'):
                candidates_matrix[col] *= self.weights['equip']
            elif col == 'Level_Score':
                candidates_matrix[col] *= self.weights['level']

        sim_scores = cosine_similarity(query_vector, candidates_matrix)

        results = self.df.copy()
        results['Similarity'] = sim_scores[0]

        recommendations = results.sort_values(by='Similarity', ascending=False).head(top_k)

        return recommendations