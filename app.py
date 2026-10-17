import os
import json
import datetime
import time
import pandas as pd
import numpy as np
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
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stRadio>div, textarea { background-color: #1f2937 !important; color: #ffffff !important; border: 1px solid #374151 !important; border-radius: 6px !important; }
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


# Load Habit Configurations
habits_config_raw = load_json(HABITS_CONFIG_FILE, {})
habits_config = {
    "good_habits": habits_config_raw.get("good_habits", ["Daily LeetCode Problem", "Yamaha Keyboard Practice"]),
    "bad_habits": habits_config_raw.get("bad_habits", ["Doomscrolling on Phone", "Procrastinating on Studies"]),
    "alternate_habits": habits_config_raw.get("alternate_habits",
                                              ["Played Yamaha keyboard", "Did 3 Rubik's cube CFOP solves",
                                               "Stepped outside"]),
    "habit_stacks": habits_config_raw.get("habit_stacks", [])
}

goals_data = load_json(GOALS_FILE, {"monthly_goals": []})
bonus_log = load_json(BONUS_LOG_FILE, {"claimed_bonuses": []})
wallet_data = load_json(WALLET_DATA_FILE, {
    "spent_coins": 0,
    "rewards_menu": {},
    "redemption_history": []
})

# Train ML model & load logs
try:
    model = train_and_get_model()
except Exception:
    model = None

logs_df = pd.read_csv(USER_CSV) if os.path.exists(USER_CSV) else pd.DataFrame()
workouts_df = pd.read_csv(WORKOUT_CSV) if os.path.exists(WORKOUT_CSV) else pd.DataFrame(
    columns=["Date", "Split", "Total_Time_Mins", "Exercise", "Weight", "Sets", "Reps"])


# --- CALCULATE HABIT COINS ---
def calculate_habit_coins(df, bonuses, wallet):
    coins = 0
    if not df.empty:
        for _, row in df.iterrows():
            if row.get("Completed", 0) == 1: coins += 7

            bh_status = str(row.get("Bad_Habit_Status", ""))
            if "Relapsed (-5)" in bh_status: coins -= 5
            if "Skipped Bad Habit (-1)" in bh_status: coins -= 1
            if "Skipped Alternate (-2)" in bh_status: coins -= 2

            journal_note = str(row.get("Journal", ""))
            if journal_note.strip() and journal_note != "nan" and len(journal_note) > 2: coins += 3

            w = row.get("Water_Goal", "NaN")
            p = row.get("Protein_Goal", "NaN")
            o = row.get("Omega3_Goal", "NaN")

            if pd.notna(w) and w != "NaN":
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

# --- GYM SPLIT DEFINITIONS ---
WORKOUT_SPLITS = {
    0: {"name": "Push", "exercises": ["Incline Chest Press", "Chest Flies", "Tricep Press", "Dips", "Lateral Raises",
                                      "Shoulder Press"]},
    1: {"name": "Pull",
        "exercises": ["DB Curls", "Hammer Curls", "Shrugs", "Lat Pulldown", "Rows", "Rear Delt Exercise"]},
    2: {"name": "Legs",
        "exercises": ["Squats", "Leg Extension", "Hamstring Curls", "Hinges", "Calves Extension", "Ab Crunches"]},
    3: {"name": "Rest/Recovery", "exercises": ["Stretching / Light Cardio"]},
    4: {"name": "Push", "exercises": ["Incline Chest Press", "Chest Flies", "Tricep Press", "Dips", "Lateral Raises",
                                      "Shoulder Press"]},
    5: {"name": "Pull",
        "exercises": ["DB Curls", "Hammer Curls", "Shrugs", "Lat Pulldown", "Rows", "Rear Delt Exercise"]},
    6: {"name": "Legs",
        "exercises": ["Squats", "Leg Extension", "Hamstring Curls", "Hinges", "Calves Extension", "Ab Crunches"]},
}
today_weekday = datetime.datetime.today().weekday()
today_split = WORKOUT_SPLITS[today_weekday]

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation")
navigation_selection = st.sidebar.radio(
    "Select View",
    [
        "Daily Tracking",
        "Health Tracker",
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

new_good_habit = st.sidebar.text_input("Add Good Habit:")
if st.sidebar.button("Add Good Habit") and new_good_habit:
    if new_good_habit not in habits_config["good_habits"]:
        habits_config["good_habits"].append(new_good_habit)
        save_json(HABITS_CONFIG_FILE, habits_config)
        st.rerun()

for gh in list(habits_config["good_habits"]):
    col_s1, col_s2 = st.sidebar.columns([4, 1])
    col_s1.write(gh)
    if col_s2.button("Del", key=f"del_gh_{gh}"):
        habits_config["good_habits"].remove(gh)
        save_json(HABITS_CONFIG_FILE, habits_config)
        st.rerun()

st.sidebar.markdown("---")

new_bad_habit = st.sidebar.text_input("Add Bad Habit (To Quit):")
if st.sidebar.button("Add Bad Habit") and new_bad_habit:
    if new_bad_habit not in habits_config["bad_habits"]:
        habits_config["bad_habits"].append(new_bad_habit)
        save_json(HABITS_CONFIG_FILE, habits_config)
        st.rerun()

for bh in list(habits_config["bad_habits"]):
    col_s1, col_s2 = st.sidebar.columns([4, 1])
    col_s1.write(bh)
    if col_s2.button("Del", key=f"del_bh_{bh}"):
        habits_config["bad_habits"].remove(bh)
        save_json(HABITS_CONFIG_FILE, habits_config)
        st.rerun()

st.sidebar.markdown("---")

new_alt_habit = st.sidebar.text_input("Add Alternate Habit:")
if st.sidebar.button("Add Alternate Habit") and new_alt_habit:
    if new_alt_habit not in habits_config["alternate_habits"]:
        habits_config["alternate_habits"].append(new_alt_habit)
        save_json(HABITS_CONFIG_FILE, habits_config)
        st.rerun()

for alt in list(habits_config["alternate_habits"]):
    col_s1, col_s2 = st.sidebar.columns([4, 1])
    col_s1.write(alt)
    if col_s2.button("Del", key=f"del_alt_{alt}"):
        habits_config["alternate_habits"].remove(alt)
        save_json(HABITS_CONFIG_FILE, habits_config)
        st.rerun()

st.sidebar.divider()
st.sidebar.subheader("Advanced Data")
if st.sidebar.button("Refresh / Reset All App Data"):
    for f in [USER_CSV, WORKOUT_CSV, GOALS_FILE, BONUS_LOG_FILE, WALLET_DATA_FILE]:
        if os.path.exists(f): os.remove(f)
    st.rerun()

# --- CONTENT VIEWS ---
if navigation_selection == "Daily Tracking":
    st.title("Daily Habit Tracker")

    st.subheader("Habit Stacking Builder")
    st.caption("After [Current Habit], I will [New Habit].")

    active_stacks = habits_config.get("habit_stacks", [])
    if active_stacks:
        for idx, stack in enumerate(active_stacks):
            col_st1, col_st2 = st.columns([4, 1])
            col_st1.markdown(f"**After I** {stack['current']}, **I will** {stack['new']}.")
            if col_st2.button("Del", key=f"del_stack_{idx}"):
                habits_config["habit_stacks"].pop(idx)
                save_json(HABITS_CONFIG_FILE, habits_config)
                st.rerun()

    with st.expander("Build a New Stack"):
        current_habit = st.text_input("Current Established Habit (The Anchor):")
        new_habit = st.text_input("New Habit (The Action):")
        if st.button("Save Habit Stack"):
            if current_habit and new_habit:
                habits_config["habit_stacks"].append({"current": current_habit, "new": new_habit})
                save_json(HABITS_CONFIG_FILE, habits_config)
                st.rerun()

    st.divider()

    if already_logged_today:
        st.warning("Locked: Today's check-in is submitted. You can still use the Health Tracker.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Good Habit")
        active_good = st.selectbox("Select Good Habit to Track Today:",
                                   habits_config["good_habits"] if habits_config["good_habits"] else ["None"])
        good_habit_done = st.checkbox(f"Completed Good Habit Today? (+7 Coins)", disabled=already_logged_today)

        st.subheader("2. Bad Habit & Urges")
        active_bad = st.selectbox("Target Bad Habit to Watch Out For:",
                                  habits_config["bad_habits"] if habits_config["bad_habits"] else ["None"],
                                  disabled=already_logged_today)

        bad_habit_status = st.radio(
            "How did you handle your urge today?",
            [
                "No Urge / Not Applicable (0)",
                "Used Alternate Habit Stack Successfully (0)",
                "Skipped Alternate (-2)",
                "Skipped Bad Habit (-1)",
                "Relapsed (-5)"
            ],
            disabled=already_logged_today
        )

        alternate_used = st.selectbox(
            "Alternate Habit Used to Recover:",
            ["None"] + habits_config["alternate_habits"],
            disabled=already_logged_today
        )

    with col2:
        st.subheader("3. Daily Context")
        sleep = st.slider("Sleep Hours:", 4.0, 10.0, 7.0, 0.5, disabled=already_logged_today)
        stress = st.slider("Stress Level (1-10):", 1, 10, 4, disabled=already_logged_today)

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
                "Cue": "N/A", "Written_Cue": written_cue, "Routine_Split": "N/A",
                "Sleep_Hours": sleep, "Stress": stress,
                "Bad_Habit_Status": bad_habit_status,
                "Bad_Habit_Tracked": active_bad,
                "Alternate_Habit": alternate_used,
                "Target_Checkin": target_checkin_status, "Streak": 1, "Completed": int(good_habit_done),
                "Journal": journal_text, "Date": today_str
            }])
            new_row.to_csv(USER_CSV, mode="a", header=not os.path.exists(USER_CSV), index=False)
            st.success("Log saved successfully!")
            st.rerun()

elif navigation_selection == "Health Tracker":
    st.title("Health Tracker")
    st.caption(f"Today is {datetime.date.today().strftime('%A')}. Scheduled Split: {today_split['name']}.")

    st.subheader("Nutrition Check-In")
    with st.form("nutrition_form"):
        col_n1, col_n2 = st.columns(2)
        calorie_intake = col_n1.slider("Calorie Intake (kcal):", 1200, 4500, 2500, 50)
        water_goal = col_n1.selectbox("Hit Water Goal?", ["Yes", "No"])
        protein_goal = col_n2.selectbox("Hit Protein Goal?", ["Yes", "No"])
        omega3_goal = col_n2.selectbox("Took Omega-3 Supplement?", ["Yes", "No"])

        if st.form_submit_button("Save Nutrition Data"):
            if not logs_df.empty and already_logged_today:
                idx = logs_df[logs_df["Date"] == today_str].index[0]
                logs_df.loc[idx, ["Calorie_Intake", "Water_Goal", "Protein_Goal", "Omega3_Goal"]] = [calorie_intake,
                                                                                                     water_goal,
                                                                                                     protein_goal,
                                                                                                     omega3_goal]
                logs_df.to_csv(USER_CSV, index=False)
                st.success("Nutrition updated for today!")
            else:
                new_row = pd.DataFrame([{"Date": today_str, "Calorie_Intake": calorie_intake, "Water_Goal": water_goal,
                                         "Protein_Goal": protein_goal, "Omega3_Goal": omega3_goal}])
                new_row.to_csv(USER_CSV, mode="a", header=not os.path.exists(USER_CSV), index=False)
                st.success("Nutrition saved for today!")
            st.rerun()

    st.divider()
    st.subheader(f"Workout Logger ({today_split['name']})")

    with st.form("workout_form"):
        total_time = st.number_input("Total Time Spent in Gym (Minutes):", min_value=0, max_value=300, value=60)
        st.markdown("### Exercises")

        exercise_logs = []
        for ex in today_split["exercises"]:
            col_e1, col_e2, col_e3, col_e4 = st.columns([2, 1, 1, 2])
            col_e1.write(f"**{ex}**")
            w_weight = col_e2.number_input("Weight", min_value=0.0, step=2.5, key=f"w_{ex}")
            sets = col_e3.number_input("Sets", min_value=0, max_value=10, value=0, key=f"set_{ex}")
            reps = col_e4.text_input("Reps (e.g., 10,8,8)", key=f"rep_{ex}")
            exercise_logs.append({"Exercise": ex, "Weight": w_weight, "Sets": sets, "Reps": reps})

        if st.form_submit_button("Save / Update Gym Session"):
            active_exercises = [e for e in exercise_logs if e["Sets"] > 0]
            if active_exercises or total_time > 0:
                for ex in active_exercises:
                    existing_idx = workouts_df[
                        (workouts_df['Date'] == today_str) & (workouts_df['Exercise'] == ex["Exercise"])].index
                    if not existing_idx.empty:
                        workouts_df.loc[existing_idx[0], "Sets"] += ex["Sets"]
                        workouts_df.loc[existing_idx[0], "Reps"] = str(
                            workouts_df.loc[existing_idx[0], "Reps"]) + "," + str(ex["Reps"])
                        workouts_df.loc[existing_idx[0], "Weight"] = max(workouts_df.loc[existing_idx[0], "Weight"],
                                                                         ex["Weight"])
                        workouts_df.loc[existing_idx[0], "Total_Time_Mins"] = max(
                            workouts_df.loc[existing_idx[0], "Total_Time_Mins"], total_time)
                    else:
                        new_row = pd.DataFrame([{
                            "Date": today_str, "Split": today_split["name"], "Total_Time_Mins": total_time,
                            "Exercise": ex["Exercise"], "Weight": ex["Weight"], "Sets": ex["Sets"], "Reps": ex["Reps"]
                        }])
                        workouts_df = pd.concat([workouts_df, new_row], ignore_index=True)

                if not active_exercises and total_time > 0:
                    existing_idx = workouts_df[
                        (workouts_df['Date'] == today_str) & (workouts_df['Exercise'] == "General Time")].index
                    if not existing_idx.empty:
                        workouts_df.loc[existing_idx[0], "Total_Time_Mins"] = max(
                            workouts_df.loc[existing_idx[0], "Total_Time_Mins"], total_time)
                    else:
                        workouts_df = pd.concat([workouts_df, pd.DataFrame(
                            [{"Date": today_str, "Split": today_split["name"], "Total_Time_Mins": total_time,
                              "Exercise": "General Time", "Weight": 0.0, "Sets": 0, "Reps": ""}])], ignore_index=True)

                workouts_df.to_csv(WORKOUT_CSV, index=False)
                st.success("Gym session saved and updated successfully!")
                st.rerun()
            else:
                st.warning("Log at least 1 set or gym time to save.")

    st.divider()
    st.subheader("ML Online Baseline Workout Analysis")
    if not workouts_df.empty:
        workouts_df['Volume'] = workouts_df['Weight'] * workouts_df['Sets']
        user_vol = workouts_df.groupby('Split')['Volume'].mean().to_dict()

        baseline_vol = {"Push": 3000, "Pull": 2800, "Legs": 4200, "Rest/Recovery": 0}

        st.write(
            "Comparing your average lifting volume (Weight x Sets) to simulated global online baselines for your splits:")
        for sp, vol in user_vol.items():
            base = baseline_vol.get(sp, 1)
            if base > 0:
                diff = ((vol - base) / base) * 100
                status = "Overperforming" if diff > 0 else "Underperforming"
                st.metric(f"{sp} Split Avg Volume", f"{vol:.0f} kg", f"{diff:.1f}% vs Online Baseline ({status})")

    st.divider()
    st.subheader("Recent Workout History")
    if not workouts_df.empty:
        st.dataframe(workouts_df.tail(15).sort_index(ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No exercises logged yet.")

elif navigation_selection == "Rewards Vault":
    st.title("Rewards Vault (Cheat Days)")
    st.caption("Spend your habit coins to unlock guilt-free rewards.")

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
        st.info("Your vault is empty. Add a custom reward above!")

    for reward_name, cost in list(wallet_data["rewards_menu"].items()):
        col_m1, col_m2, col_m3, col_m4 = st.columns([3, 1, 1, 1])
        col_m1.markdown(f"**{reward_name}**")
        col_m2.markdown(f"`{cost} 🪙`")

        if total_coins >= cost:
            if col_m3.button("Redeem", key=f"red_{reward_name}"):
                wallet_data["spent_coins"] += cost
                wallet_data["redemption_history"].append({
                    "reward": reward_name, "cost": cost, "date": datetime.datetime.now().isoformat()
                })
                save_json(WALLET_DATA_FILE, wallet_data)
                st.success(f"Unlocked! Enjoy your cheat task: {reward_name}.")
                st.rerun()
        else:
            col_m3.button("Not Enough 🪙", key=f"lock_{reward_name}", disabled=True)

        if col_m4.button("Del", key=f"del_rew_{reward_name}"):
            del wallet_data["rewards_menu"][reward_name]
            save_json(WALLET_DATA_FILE, wallet_data)
            st.rerun()

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

    st.subheader("Gym Average Time Analysis")
    if workouts_df.empty or "Total_Time_Mins" not in workouts_df.columns:
        st.info("Log your gym sessions in the Health Tracker to see average times!")
    else:
        gym_days = workouts_df.drop_duplicates(subset=['Date']).copy()
        avg_gym_time = gym_days["Total_Time_Mins"].mean()

        col_t1, col_t2 = st.columns(2)
        col_t1.metric("Average Gym Duration", f"{avg_gym_time:.1f} Mins")
        col_t2.metric("Total Gym Days Logged", f"{len(gym_days)} Days")

        st.line_chart(gym_days.set_index("Date")["Total_Time_Mins"])

    st.divider()
    st.subheader("Weekly Progress Report")
    if logs_df.empty:
        st.info("Log a few days of data in Daily Tracking to generate your weekly report!")
    else:
        last_7_days = logs_df.tail(7)
        completion_rate = last_7_days["Completed"].mean() * 100

        r1, r2 = st.columns(2)
        r1.metric("Completion Rate", f"{completion_rate:.1f}%")
        r2.metric("Total Days Logged", f"{len(logs_df)} Days")

    st.divider()
    st.subheader("Consistency Heatmap")
    if logs_df.empty or "Date" not in logs_df.columns:
        st.info("Log some data to populate your heatmap!")
    else:
        logs_df['ParsedDate'] = pd.to_datetime(logs_df['Date']).dt.date
        full_year_df = pd.DataFrame({'Date': pd.date_range(start=datetime.date(datetime.date.today().year, 1, 1),
                                                           end=datetime.date(datetime.date.today().year, 12, 31)).date})
        full_year_df = full_year_df.merge(logs_df, on='Date', how='left')

        full_year_df['Score'] = full_year_df.apply(
            lambda r: 2 if r.get('Completed', 0) == 1 else (0 if pd.isna(r.get('Completed')) else 1), axis=1)
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
            with st.expander(f"Entry on {row.get('Date', 'Unknown Date')} - {row.get('Bad_Habit_Status', '')}"):
                st.write(f"**Written Trigger Context:** {row.get('Written_Cue', 'None provided.')}")
                st.write(
                    f"**Health Log:** Sleep: {row.get('Sleep_Hours', 'N/A')}h | Stress: {row.get('Stress', 'N/A')}/10 | Calories: {row.get('Calorie_Intake', 'N/A')}kcal | Water Goal Met: {row.get('Water_Goal', 'N/A')} | Protein Goal Met: {row.get('Protein_Goal', 'N/A')} | Omega-3 Taken: {row.get('Omega3_Goal', 'N/A')}")
                st.write(f"**Journal Note:** {row.get('Journal', 'No notes provided.')}")