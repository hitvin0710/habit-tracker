import pandas as pd
import numpy as np

np.random.seed(42)
n_samples = 1000

# Categorical Cues & Schedule Context
cues = ['Morning Supplements', 'After Dinner', 'Post-Lecture', 'Random Time']
splits = ['Push', 'Pull', 'Legs', 'Rest']

data = {
    'Trigger_Cue': np.random.choice(cues, n_samples, p=[0.35, 0.25, 0.25, 0.15]),
    'Routine_Day': np.random.choice(splits, n_samples, p=[0.25, 0.25, 0.25, 0.25]),
    'Sleep_Hours': np.round(np.random.normal(7.0, 1.2, n_samples).clip(4, 10), 1),
    'Energy_Level': np.random.randint(1, 11, n_samples),
    'Stress_Level': np.random.randint(1, 11, n_samples),
    'Previous_Streak': np.random.exponential(scale=4, size=n_samples).astype(int)
}

df = pd.DataFrame(data)

# Behavioral Score (Fogg's B=MAP: Motivation + Ability + Prompt)
cue_bonus = df['Trigger_Cue'].map({
    'Morning Supplements': 1.5,
    'After Dinner': 0.8,
    'Post-Lecture': 0.5,
    'Random Time': -1.2
})

logit = (
    -1.0
    + 0.35 * df['Energy_Level']
    - 0.30 * df['Stress_Level']
    + 0.25 * (df['Sleep_Hours'] - 6)
    + 0.10 * np.minimum(df['Previous_Streak'], 10)
    + cue_bonus
)

prob = 1 / (1 + np.exp(-logit))#sigmoid function
df['Good_Habit_Done'] = (np.random.rand(n_samples) < prob).astype(int)

# Bad habit avoidance is higher when stress is low or good habit was completed
urge_prob = 1 / (1 + np.exp(-(0.5 - 0.35 * df['Stress_Level'] + 1.2 * df['Good_Habit_Done'])))
df['Bad_Habit_Avoided'] = (np.random.rand(n_samples) < urge_prob).astype(int)

df.to_csv('base_habit_data.csv', index=False)
print(f"✅ Successfully generated base_habit_data.csv with {len(df)} rows!")