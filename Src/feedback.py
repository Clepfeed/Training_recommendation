import pandas as pd
import os
from datetime import datetime

class FeedbackManager:
    def __init__(self, filepath="data/user_feedback.csv"):
        self.filepath = filepath
        self.columns = [
            "Timestamp", 
            "Exercise", 
            "BodyPart", 
            "User_Rating_1_10", 
            "Perceived_Difficulty", 
            "Comment"
        ]
        
        if not os.path.exists(self.filepath):
            try:
                df = pd.DataFrame(columns=self.columns)
                df.to_csv(self.filepath, index=False)
            except Exception as e:
                print(f"Error creating feedback file: {e}")

    def save_feedback(self, exercise_title, body_part, rating_score, difficulty_feedback, comment=""):
        try:
            new_row = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Exercise": exercise_title,
                "BodyPart": body_part,
                "User_Rating_1_10": rating_score,
                "Perceived_Difficulty": difficulty_feedback,
                "Comment": comment
            }
            df = pd.DataFrame([new_row])
            df.to_csv(self.filepath, mode='a', header=False, index=False)
            return True
        except Exception as e:
            print(f"Error saving feedback: {e}")
            return False

    def log_skip(self, exercise_title, body_part):
        """
        Специальный метод для регистрации пропуска упражнения (Implicit Feedback).
        Записывает рейтинг -1 и пометку 'SKIPPED'.
        """
        return self.save_feedback(
            exercise_title=exercise_title,
            body_part=body_part,
            rating_score=-1,       # Код для скипа
            difficulty_feedback="SKIPPED",
            comment="User pressed Swap button"
        )