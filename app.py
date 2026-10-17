import os
import json
import datetime
import time
import pandas as pd
import streamlit as st
from ml_engine import train_and_get_model, USER_CSV

st.set_page_config(page_title="Atomic Habit & Goal Tracker", page_icon="🪙", layout="wide")

# --- CUSTOM NEON THEME CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #e5e7eb; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1f2937; }
    h1, h2, h3 { color: #00ffcc !important; text-shadow: 0 0 10px rgba(0, 255, 204, 0.3); }
    .stButton>button { background: linear-gradient(90deg, #00ffcc 0%, #0077ff 100%); color: #0b0f19; font-weight: bold; border: none; border-radius: 8px; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); transition: 0.3s ease; }
    .stButton>button:hover { opacity: 0.85; box-shadow: 0 0 25px rgba(0, 255, 204, 0.8); }
    [data-testid="stMetricValue"] { color: #00ffcc !important; text-shadow: 0 0 8px rgba(0, 255, 204, 0.4); }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, textarea { background-color: #1f2937 !important; color: #ffffff !important; border: 1px solid #374151 !important; border-radius: 6px !important; }
    </style>
""", unsafe_allow_html=True)

# --- FILE PATHS & LOADERS ---
GOALS_FILE = "goals_config.json"
BONUS_LOG_FILE = "bonus_coins_log.json"
HABITS_CONFIG_FILE = "habits_config.json"
WALLET_DATA_FILE = "wallet_data.json"
WORKOUT_CSV = "workout_logs.csv"


def load_json(filepath, default_data):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return default_data


def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


habits_config = load_json(HABITS_CONFIG_FILE, {
    "good_habits": ["Daily LeetCode Problem", "Yamaha Keyboard Practice"],
    "bad_habits": ["Doomscrolling on Phone", "Procrastinating on Studies"]
})
goals_data = load_json(GOALS_FILE, {"monthly_goals": []})
bonus_log = load_json(BONUS_LOG_FILE, {"claimed_bonuses": []})

# Rewards menu starts completely empty now
wallet_data = load_json(WALLET_DATA_FILE, {
    "spent_coins": 0,
    "focus_coins_earned": 0,
    "rewards_menu": {},
    "redemption_history": []
})

# Train ML model & load logs
model = train_and_get_model()
logs_df = pd.read_csv(USER_CSV) if os.path.exists(USER_CSV) else pd.DataFrame()
workouts_df = pd.read_csv(WORKOUT_CSV) if os.path.exists(WORKOUT_CSV) else pd.DataFrame()


# --- CALCULATE HABIT COINS ---
def calculate_habit_coins(df, bonuses, wallet):
    coins = 0
    if not df.empty:
        for _, row in df.iterrows():
            if row.get("Completed", 0) == 1: coins += 7
            if row.get("Relapsed", 0) == 1: coins -= 3
            journal_note = str(row.get("Journal", ""))
            if journal_note.strip() and journal_note != "nan" and len(journal_note) > 2: coins += 3

            w = row.get("Water_Goal", "Yes")
            p = row.get("Protein_Goal", "Yes")
            o = row.get("Omega3_Goal", "Yes")
            if w == "Yes" and p == "Yes" and o == "Yes":
                coins += 2
            else:
                coins -= 1

            if "Fail" in str(row.get("Target_Checkin", "Pass")): coins -= 15

        try:
            df['ParsedDate'] = pd.to_datetime(df['Date'])
            start_date = df['ParsedDate'].min()
            all_days = pd.date_range(start=start_date, end=pd.Timestamp(datetime.date.today()))
            logged_days = set(df['ParsedDate'].dt.date)
            for day in all_days:
                if day.date() not in logged_days: coins -= 5
        except Exception:
            pass

    for goal in goals_data.get("monthly_goals", []):
        if goal["goal_name"] in bonuses.get("claimed_bonuses", []):
            coins += goal.get("duration_months", 1) * 25

    coins += wallet.get("focus_coins_earned", 0)
    coins -= wallet.get("spent_coins", 0)

    return max(0, coins)


total_coins = calculate_habit_coins(logs_df, bonus_log, wallet_data)


def get_user_rank(coins):
    if coins >= 1000:
        return "Legendary", 1000, 1000
    elif coins >= 600:
        return "Heroic", 600, 1000
    elif coins >= 300:
        return "Pro", 300, 600
    elif coins >= 150:
        return "Intermediate", 150, 300
    elif coins >= 50:
        return "Noob", 50, 150
    return "Beginner", 0, 50


current_rank, rank_min, rank_max = get_user_rank(total_coins)

today_str = datetime.date.today().isoformat()
already_logged_today = False
if not logs_df.empty and "Date" in logs_df.columns:
    already_logged_today = today_str in logs_df["Date"].values

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation")
navigation_selection = st.sidebar.radio(
    "Select View",
    [
        "Daily Tracking",
        "Workout Tracker",
        "Focus Room",
        "Rewards Vault",
        "Monthly Goals",
        "Analytics & Reports",
        "Journal Archive"
    ]
)

st.sidebar.divider()
st.sidebar.title("Habit Wallet & Rank")
st.sidebar.metric("Balance", f"{total_coins} 🪙")
st.sidebar.markdown(f"**Rank:** `{current_rank}`")
if current_rank != "Legendary":
    st.sidebar.progress(min(1.0, (total_coins - rank_min) / (rank_max - rank_min)), text=f"Next Rank at {rank_max} 🪙")

st.sidebar.divider()
st.sidebar.subheader("Habit Manager")
new_good_habit = st.sidebar.text_input("Add New Good Habit:")
if st.sidebar.button("Add Good Habit") and new_good_habit:
    if new_good_habit not in habits_config["good_habits"]:
        habits_config["good_habits"].append(new_good_habit)
        save_json(HABITS_CONFIG_FILE, habits_config)
        st.rerun()

for gh in list(habits_config["good_habits"]):
    col_s1, col_s2 = st.sidebar.columns([4, 1])
    col_s1.write(gh)
    if col_s2.button("X", key=f"del_gh_{gh}"):
        habits_config["good_habits"].remove(gh)
        save_json(HABITS_CONFIG_FILE, habits_config)
        st.rerun()

# --- CONTENT VIEWS ---
if navigation_selection == "Daily Tracking":
    st.title("Daily Habit & Relapse Tracker")

    if already_logged_today:
        st.warning(
            "Today's check-in is locked to prevent lagging past data. You can still use the Focus Room or Workout Tracker!")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Habit Execution")
        active_habit = st.selectbox("Select Good Habit to Track Today:",
                                    habits_config["good_habits"] if habits_config["good_habits"] else [
                                        "No habits configured"])
        good_habit_done = st.checkbox(f"Completed '{active_habit}' Today?", disabled=already_logged_today)
        relapsed = st.checkbox("Relapsed on Bad Habit Today?", disabled=already_logged_today)

        alternate_habit = "None"
        if relapsed:
            alternate_habit = st.selectbox(
                "Alternate Habit Used to Recover:",
                ["None", "Played Yamaha keyboard", "Did 3 Rubik's cube CFOP solves", "Stepped outside"],
                disabled=already_logged_today
            )

    with col2:
        st.subheader("Daily Context & Nutrition")
        cue_category = st.selectbox("Trigger Category:",
                                    ["Morning Routine", "After Class", "After Dinner", "Random Time"],
                                    disabled=already_logged_today)
        split = st.selectbox("Routine Split:", ["Push", "Pull", "Legs", "Rest"], disabled=already_logged_today)
        sleep = st.slider("Sleep Hours:", 4.0, 10.0, 7.0, 0.5, disabled=already_logged_today)
        stress = st.slider("Stress Level (1-10):", 1, 10, 4, disabled=already_logged_today)
        calorie_intake = st.slider("Calorie Intake (kcal):", 1200, 4500, 2500, 50, disabled=already_logged_today)
        water_goal = st.selectbox("Hit Water Goal?", ["Yes", "No"], disabled=already_logged_today)
        protein_goal = st.selectbox("Hit Protein Goal?", ["Yes", "No"], disabled=already_logged_today)
        omega3_goal = st.selectbox("Took Omega-3 Supplement?", ["Yes", "No"], disabled=already_logged_today)

    st.divider()
    st.subheader("What led to the habit breaking or making today?")
    written_cue = st.text_input("Describe your trigger context:", disabled=already_logged_today)

    st.subheader("Active Monthly Challenge Check-In")
    goal_checkins = {}
    target_checkin_status = "Pass"

    if not goals_data["monthly_goals"]:
        st.info("No active monthly goals.")
    else:
        for idx, goal in enumerate(goals_data["monthly_goals"]):
            if goal["status"] == "Active":
                passed_today = st.radio(f"Uphold target for '{goal['goal_name']}' today?", ["Pass", "Fail"],
                                        key=f"goal_check_{idx}", disabled=already_logged_today)
                status_val = 1 if "Pass" in passed_today else 0
                goal_checkins[goal["goal_name"]] = status_val
                if status_val == 0: target_checkin_status = "Fail (-15 Coins)"

    journal_text = st.text_area("Journal (+3 Coins):", disabled=already_logged_today)

    if not already_logged_today:
        if st.button("Save Today's Log & Claim Coins", type="primary"):
            for goal in goals_data.get("monthly_goals", []):
                if goal["goal_name"] in goal_checkins:
                    if "daily_scores" not in goal: goal["daily_scores"] = []
                    goal["daily_scores"].append(goal_checkins[goal["goal_name"]])
            save_json(GOALS_FILE, goals_data)

            new_row = pd.DataFrame([{
                "Cue": cue_category, "Written_Cue": written_cue, "Routine_Split": split,
                "Sleep_Hours": sleep, "Stress": stress, "Calorie_Intake": calorie_intake,
                "Water_Goal": water_goal, "Protein_Goal": protein_goal, "Omega3_Goal": omega3_goal,
                "Target_Checkin": target_checkin_status, "Streak": 1, "Completed": int(good_habit_done),
                "Relapsed": int(relapsed), "Alternate_Habit": alternate_habit, "Journal": journal_text,
                "Date": today_str
            }])
            new_row.to_csv(USER_CSV, mode="a", header=not os.path.exists(USER_CSV), index=False)
            st.success("Log saved successfully!")
            st.rerun()

elif navigation_selection == "Workout Tracker":
    st.title("Workout & Lifting Tracker")
    st.caption("Log your resistance training progression.")

    with st.form("workout_form"):
        col_w1, col_w2, col_w3 = st.columns(3)
        w_split = col_w1.selectbox("Split", ["Push", "Pull", "Legs"])
        w_exercise = col_w2.text_input("Exercise Name (e.g., Incline Bench, Squat)")
        w_weight = col_w3.number_input("Weight (kg or lbs)", min_value=0.0, step=2.5)

        col_w4, col_w5 = st.columns(2)
        w_sets = col_w4.number_input("Sets", min_value=1, max_value=10, value=3)
        w_reps = col_w5.text_input("Reps (e.g., 10,8,8 or 12)")

        if st.form_submit_button("Log Exercise"):
            if w_exercise:
                new_workout = pd.DataFrame([{
                    "Date": today_str,
                    "Split": w_split,
                    "Exercise": w_exercise,
                    "Weight": w_weight,
                    "Sets": w_sets,
                    "Reps": w_reps
                }])
                new_workout.to_csv(WORKOUT_CSV, mode="a", header=not os.path.exists(WORKOUT_CSV), index=False)
                st.success(f"Logged {w_sets} sets of {w_exercise}!")
                st.rerun()

    st.divider()
    st.subheader("Recent Workout History")
    if not workouts_df.empty:
        st.dataframe(workouts_df.tail(15).sort_index(ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No exercises logged yet.")

elif navigation_selection == "Focus Room":
    st.title("Deep Focus Room")
    st.caption("Lock in to an alternate habit. Complete the timer without leaving the app to earn bonus coins.")

    focus_task = st.selectbox("What are you focusing on?",
                              ["CFOP Rubik's Cube Algorithms", "Yamaha Keyboard Practice", "LeetCode Session",
                               "Custom Work"])
    focus_minutes = st.slider("Focus Duration (Minutes)", min_value=5, max_value=60, value=15, step=5)

    if st.button("Start Focus Session"):
        timer_placeholder = st.empty()
        total_seconds = focus_minutes * 60

        for i in range(total_seconds, -1, -1):
            mins, secs = divmod(i, 60)
            timer_placeholder.markdown(
                f"<h1 style='text-align: center; font-size: 80px; color: #00ffcc;'>{mins:02d}:{secs:02d}</h1>",
                unsafe_allow_html=True)
            time.sleep(1)

        wallet_data["focus_coins_earned"] += 5
        save_json(WALLET_DATA_FILE, wallet_data)
        st.success(f"Session Complete! +5 🪙 earned for focusing on {focus_task}.")

elif navigation_selection == "Rewards Vault":
    st.title("Rewards Vault (Cheat Days)")
    st.caption("Spend your hard-earned habit coins to unlock guilt-free rewards and cheat tasks.")

    st.subheader("Add a Custom Reward")
    with st.form("add_reward"):
        col_r1, col_r2 = st.columns([3, 1])
        r_name = col_r1.text_input("Reward Name (e.g., Order Biryani)")
        r_cost = col_r2.number_input("Coin Cost", min_value=10, max_value=2000, value=150, step=10)
        if st.form_submit_button("Add to Vault"):
            if r_name:
                wallet_data["rewards_menu"][r_name] = r_cost
                save_json(WALLET_DATA_FILE, wallet_data)
                st.rerun()

    st.divider()
    st.subheader("Available Rewards")

    if not wallet_data["rewards_menu"]:
        st.info("Your vault is empty. Add a custom reward above to start spending your coins!")

    for reward_name, cost in list(wallet_data["rewards_menu"].items()):
        col_m1, col_m2, col_m3, col_m4 = st.columns([3, 1, 1, 1])
        col_m1.markdown(f"**{reward_name}**")
        col_m2.markdown(f"`{cost} 🪙`")

        if total_coins >= cost:
            if col_m3.button("Redeem", key=f"red_{reward_name}"):
                wallet_data["spent_coins"] += cost
                wallet_data["redemption_history"].append({
                    "reward": reward_name,
                    "cost": cost,
                    "date": datetime.datetime.now().isoformat()
                })
                save_json(WALLET_DATA_FILE, wallet_data)
                st.success(f"Unlocked! Enjoy your cheat task: {reward_name}.")
                st.rerun()
        else:
            col_m3.button("Not Enough 🪙", key=f"lock_{reward_name}", disabled=True)

        if col_m4.button("Delete", key=f"del_rew_{reward_name}"):
            del wallet_data["rewards_menu"][reward_name]
            save_json(WALLET_DATA_FILE, wallet_data)
            st.rerun()

    if wallet_data.get("redemption_history"):
        with st.expander("Redemption History"):
            for h in reversed(wallet_data["redemption_history"]):
                dt_str = datetime.datetime.fromisoformat(h['date']).strftime("%b %d, %Y")
                st.write(f"- **{h['reward']}** (-{h['cost']} 🪙) on {dt_str}")

elif navigation_selection == "Monthly Goals":
    st.title("Monthly Goals & Target Bonuses")
    with st.form("add_goal_form"):
        new_goal_name = st.text_input("Goal / Challenge Name:", placeholder="e.g., No Doomscrolling")
        duration = st.number_input("Duration (in Months):", min_value=1, max_value=24, value=2)
        if st.form_submit_button("Start Challenge") and new_goal_name:
            target_dt = datetime.datetime.now() + datetime.timedelta(days=int(duration * 30))
            goals_data["monthly_goals"].append({
                "goal_name": new_goal_name, "duration_months": duration,
                "target_timestamp": target_dt.isoformat(), "status": "Active",
                "daily_scores": [], "current_eval": "Not enough data yet (< 5 days)"
            })
            save_json(GOALS_FILE, goals_data)
            st.rerun()

    for idx, goal in enumerate(goals_data.get("monthly_goals", [])):
        target_time = datetime.datetime.fromisoformat(goal["target_timestamp"])
        remaining = target_time - datetime.datetime.now()
        is_completed = remaining.total_seconds() <= 0 or goal.get("current_eval") == "On Track to Pass (>= 80%)"

        col_g1, col_g2, col_g3 = st.columns([3, 2, 1])
        col_g1.markdown(f"### **{goal['goal_name']}**")
        col_g1.caption(f"Status: **{goal.get('current_eval', 'Pending')}**")

        if remaining.total_seconds() > 0:
            col_g2.metric("Time Remaining", f"{remaining.days} Days Left")
        else:
            col_g2.success("Challenge Ended!")

        already_claimed = goal["goal_name"] in bonus_log.get("claimed_bonuses", [])
        bonus_amt = goal["duration_months"] * 25

        if is_completed and not already_claimed:
            if col_g3.button(f"Claim +{bonus_amt} 🪙!", key=f"claim_{idx}"):
                bonus_log["claimed_bonuses"].append(goal["goal_name"])
                save_json(BONUS_LOG_FILE, bonus_log)
                st.rerun()
        elif already_claimed:
            col_g3.success(f"+{bonus_amt} Claimed")
        else:
            if col_g3.button("Delete", key=f"del_goal_{idx}"):
                goals_data["monthly_goals"].pop(idx)
                save_json(GOALS_FILE, goals_data)
                st.rerun()
        st.divider()

elif navigation_selection == "Analytics & Reports":
    st.title("Analytics, Heatmap & Reports")

    st.subheader("Weekly Progress Report")
    if logs_df.empty or "Relapsed" not in logs_df.columns:
        st.info("Log a few days of data in Daily Tracking to generate your weekly report!")
    else:
        last_7_days = logs_df.tail(7)
        total_relapses = last_7_days["Relapsed"].sum()
        completion_rate = last_7_days["Completed"].mean() * 100

        r1, r2, r3 = st.columns(3)
        r1.metric("Weekly Relapses", f"{total_relapses} Times")
        r2.metric("Completion Rate", f"{completion_rate:.1f}%")
        r3.metric("Total Days Logged", f"{len(logs_df)} Days")

    st.divider()

    st.subheader("Consistency Heatmap")
    if logs_df.empty or "Date" not in logs_df.columns:
        st.info("Log some data to populate your heatmap!")
    else:
        logs_df['ParsedDate'] = pd.to_datetime(logs_df['Date']).dt.date
        full_year_df = pd.DataFrame({'Date': pd.date_range(start=datetime.date(datetime.date.today().year, 1, 1),
                                                           end=datetime.date(datetime.date.today().year, 12, 31)).date})
        full_year_df = full_year_df.merge(logs_df, on='Date', how='left')

        full_year_df['Score'] = full_year_df.apply(lambda r: 2 if r.get('Completed', 0) == 1 else (
            0 if pd.isna(r.get('Completed')) or r.get('Relapsed', 0) == 1 else 1), axis=1)
        st.line_chart(full_year_df.set_index('Date')['Score'])

    st.divider()

    st.subheader("Written Cue Analysis")
    if logs_df.empty or "Written_Cue" not in logs_df.columns:
        st.info("Log a few days of data to unlock analysis!")
    else:
        try:
            rf_model = model.named_steps["rf"]
            feat_names = model.named_steps["prep"].get_feature_names_out()
            st.bar_chart(
                pd.DataFrame({"Feature": feat_names, "Importance": rf_model.feature_importances_}).set_index("Feature"))
        except Exception:
            st.info("Complete more logs to generate feature weights.")

elif navigation_selection == "Journal Archive":
    st.title("Journal Archive")
    if logs_df.empty or "Journal" not in logs_df.columns:
        st.info("No journal entries yet.")
    else:
        for idx, row in logs_df.iterrows():
            with st.expander(f"Entry on {row.get('Date', 'Unknown Date')} - Relapsed: {row.get('Relapsed', 0)}"):
                st.write(f"**Written Trigger Context:** {row.get('Written_Cue', 'None provided.')}")
                st.write(
                    f"**Health Log:** Sleep: {row.get('Sleep_Hours', 'N/A')}h | Stress: {row.get('Stress', 'N/A')}/10 | Calories: {row.get('Calorie_Intake', 'N/A')}kcal | Water Goal Met: {row.get('Water_Goal', 'N/A')} | Protein Goal Met: {row.get('Protein_Goal', 'N/A')} | Omega-3 Taken: {row.get('Omega3_Goal', 'N/A')}")
                st.write(f"**Journal Note:** {row.get('Journal', 'No notes provided.')}")
                st.write(f"*Alternate Habit Used:* {row.get('Alternate_Habit', 'None')}")