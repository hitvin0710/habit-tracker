import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

BASE_CSV = "base_data.csv"
USER_CSV = "my_logs.csv"

FEATURES = ["Cue", "Routine_Split", "Sleep_Hours", "Energy", "Stress", "Streak"]
CATEGORICAL = ["Cue", "Routine_Split"]
TARGET = "Completed"


def create_base_dataset():
    """Generates 150 rows of baseline Atomic Habits data if it doesn't exist yet."""
    if os.path.exists(BASE_CSV):
        return

    np.random.seed(42)
    n = 150
    cues = ["Morning Supplements", "After Class", "After Dinner", "Random Time"]
    splits = ["Push", "Pull", "Legs", "Rest"]

    df = pd.DataFrame({
        "Cue": np.random.choice(cues, n),
        "Routine_Split": np.random.choice(splits, n),
        "Sleep_Hours": np.round(np.random.uniform(4.5, 9.5, n), 1),
        "Energy": np.random.randint(1, 11, n),
        "Stress": np.random.randint(1, 11, n),
        "Streak": np.random.randint(0, 15, n),
    })

    cue_score = df["Cue"].map({
        "Morning Supplements": 2.0,
        "After Class": 1.0,
        "After Dinner": 0.5,
        "Random Time": -2.0
    })

    score = (
            cue_score
            + (0.4 * df["Energy"])
            - (0.4 * df["Stress"])
            + (0.3 * (df["Sleep_Hours"] - 6))
            + (0.15 * df["Streak"])
    )

    prob = 1 / (1 + np.exp(-score))
    df["Completed"] = (np.random.rand(n) < prob).astype(int)
    df["Bad_Habit_Avoided"] = 1
    df.to_csv(BASE_CSV, index=False)


def train_and_get_model():
    """Combines base data + your personal logs (weighted 10x) and trains a Random Forest."""
    create_base_dataset()
    base_df = pd.read_csv(BASE_CSV)
    base_df["weight"] = 1.0  # Standard weight for research data

    if os.path.exists(USER_CSV):
        user_df = pd.read_csv(USER_CSV)
        user_df["weight"] = 10.0  # Your personal data counts 10x more!
        full_df = pd.concat([base_df, user_df], ignore_index=True)
    else:
        full_df = base_df

    X = full_df[FEATURES]
    y = full_df[TARGET]
    weights = full_df["weight"]

    preprocessor = ColumnTransformer(
        transformers=[("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
        remainder="passthrough"
    )

    model = Pipeline([
        ("prep", preprocessor),
        ("rf", RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42))
    ])

    model.fit(X, y, rf__sample_weight=weights)
    return model


def get_dataset_comparison():
    """Compares your personal log averages against the baseline research dataset."""
    if not os.path.exists(USER_CSV) or not os.path.exists(BASE_CSV):
        return None, None

    user_df = pd.read_csv(USER_CSV)
    base_df = pd.read_csv(BASE_CSV)

    user_success = user_df["Completed"].mean() * 100 if "Completed" in user_df.columns else 0
    base_success = base_df["Completed"].mean() * 100

    user_stress = user_df["Stress"].mean() if "Stress" in user_df.columns else 0
    base_stress = base_df["Stress"].mean()

    return {"user_success": user_success, "base_success": base_success}, {"user_stress": user_stress,
                                                                          "base_stress": base_stress}