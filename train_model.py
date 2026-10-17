import os
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

FEATURES = ['Trigger_Cue', 'Routine_Day', 'Sleep_Hours', 'Energy_Level', 'Stress_Level', 'Previous_Streak']
CAT_FEATURES = ['Trigger_Cue', 'Routine_Day']
TARGET = 'Good_Habit_Done'
MODEL_FILE = 'habit_model.cbm'

def train_base_model():
    if not os.path.exists('base_habit_data.csv'):
        print("❌ Run generate_base_data.py first!")
        return

    df = pd.read_csv('base_habit_data.csv')
    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = CatBoostClassifier(
        iterations=150,
        learning_rate=0.05,
        depth=4,
        cat_features=CAT_FEATURES,
        verbose=0,
        random_seed=42
    )

    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    print(f"✅ Base Model Trained! Test Accuracy: {accuracy_score(y_test, preds):.2%}")

    model.save_model(MODEL_FILE)
    print(f"✅ Saved model to {MODEL_FILE}")

def warm_start_personalize(personal_csv='personal_logs.csv'):
    """Fine-tunes the existing CatBoost model using your personal logs"""
    if not os.path.exists(personal_csv):
        return False, "No personal logs found yet."

    df_personal = pd.read_csv(personal_csv)
    if len(df_personal) < 7:
        return False, f"Need at least 7 logs to fine-tune (currently have {len(df_personal)})."

    if df_personal[TARGET].nunique() < 2:
        return False, "Need at least one completed (1) and one missed (0) day in your logs to fine-tune."

    X_p = df_personal[FEATURES]
    y_p = df_personal[TARGET]

    updated_model = CatBoostClassifier(
        iterations=20,
        learning_rate=0.03,
        depth=3,
        cat_features=CAT_FEATURES,
        verbose=0
    )

    updated_model.fit(X_p, y_p, init_model=MODEL_FILE)
    updated_model.save_model(MODEL_FILE)
    return True, f"✅ Model successfully personalized with {len(df_personal)} days of your data!"

if __name__ == '__main__':
    train_base_model()