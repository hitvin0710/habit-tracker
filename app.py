import os
import json
import datetime
import pandas as pd
import streamlit as st
from ml_engine import train_and_get_model, USER_CSV

st.set_page_config(page_title="Atomic Habit & Goal Tracker", page_icon="⚡", layout="wide")

# --- CUSTOM NEON THEME CSS ---
st.markdown("""
    <style>
    /* Main Background & Font Color */
    .stApp {
        background-color: #0b0f19;
        color: #e5e7eb;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }

    /* Neon Glow Headers */
    h1, h2, h3 {
        color: #00ffcc !important;
        text-shadow: 0 0 10px rgba(0, 255, 204, 0.3);
    }

    /* Neon Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #00ffcc 0%, #0077ff 100%);
        color: #0b0f19;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        box-shadow: 0 0 15px rgba(0, 255, 204, 0.4);
        transition: 0.3s ease;
    }
    .stButton>button:hover {
        opacity: 0.85;
        box-shadow: 0 0 25px rgba(0, 255, 204, 0.8);
    }

    /* Metric Cards */
    [data-testid="stMetricValue"] {
        color: #00ffcc !important;
        text-shadow: 0 0 8px rgba(0, 255, 204, 0.4);
    }

    /* Input Fields / Containers */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, textarea {
        background-color: #1f2937 !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 6px !important;
    }
    </style>
""", unsafe_allow_html=True)

GOALS_FILE = "goals_config.json"
BONUS_LOG_FILE = "bonus_coins_log.json"
HABITS_CONFIG_FILE = "habits_config.json"


def load_habits_config():
    if os.path.exists(HABITS_CONFIG_FILE):
        with open(HABITS_CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "good_habits": ["Gym Workout (PPLR)", "Daily LeetCode Problem", "Yamaha Keyboard Practice"],
        "bad_habits": ["Doomscrolling on Phone", "Procrastinating on Studies"]
    }


def save_habits_config(data):
    with open(HABITS_CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_goals():
    if os.path.exists(GOALS_FILE):
        with open(GOALS_FILE, "r") as f:
            return json.load(f)
    return {"monthly_goals": []}


def save_goals(data):
    with open(GOALS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_bonus_log():
    if os.path.exists(BONUS_LOG_FILE):
        with open(BONUS_LOG_FILE, "r") as f:
            return json.load(f)
    return {"claimed_bonuses": []}


def save_bonus_log(data):
    with open(BONUS_LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)


habits_config = load_habits_config()
goals_data = load_goals()
bonus_log = load_bonus_log()

# Train ML model & load logs
model = train_and_get_model()
logs_df = pd.read_csv(USER_CSV) if os.path.exists(USER_CSV) else pd.DataFrame()


# --- CALCULATE HABIT COINS ---
def calculate_habit_coins(df, bonuses):
    coins = 0
    if not df.empty:
        for _, row in df.iterrows():
            if row.get("Completed", 0) == 1:
                coins += 5
            if row.get("Relapsed", 0) == 1:
                coins -= 3
            journal_note = str(row.get("Journal", ""))
            if journal_note.strip() and journal_note != "nan" and len(journal_note) > 2:
                coins += 2
    coins += len(bonuses.get("claimed_bonuses", [])) * 25
    return max(0, coins)


total_coins = calculate_habit_coins(logs_df, bonus_log)


# --- RANKED LEVEL SYSTEM ---
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
    else:
        return "Beginner", 0, 50


current_rank, rank_min, rank_max = get_user_rank(total_coins)

# Check if user already logged today
today_str = datetime.date.today().isoformat()
already_logged_today = False
if not logs_df.empty and "Date" in logs_df.columns:
    already_logged_today = today_str in logs_df["Date"].values

# --- SIDEBAR NAVIGATION & WALLET ---
st.sidebar.title("Navigation")
navigation_selection = st.sidebar.radio(
    "Select View",
    ["Daily Tracking & Check-In", "Monthly Goals & Timers", "Written Cue Analysis", "Weekly Report", "Journal Archive"]
)

st.sidebar.divider()
st.sidebar.title("Habit Wallet & Rank")
st.sidebar.metric("Habit Coins Balance", f"{total_coins} 🪙")
st.sidebar.markdown(f"**Current Rank:** `{current_rank}`")
if current_rank != "Legendary":
    st.sidebar.progress(min(1.0, (total_coins - rank_min) / (rank_max - rank_min)),
                        text=f"Next Rank at {rank_max} Coins")
else:
    st.sidebar.success("Max Rank Achieved!")

st.sidebar.caption("Earn: +5 Good Habit | Deduct: -3 Relapse | Earn: +2 Journal | Target Completed: +25")

st.sidebar.divider()
st.sidebar.subheader("Habit Manager")
st.sidebar.caption("Add or delete habits at any time!")

new_good_habit = st.sidebar.text_input("Add New Good Habit:")
if st.sidebar.button("Add Good Habit") and new_good_habit:
    if new_good_habit not in habits_config["good_habits"]:
        habits_config["good_habits"].append(new_good_habit)
        save_habits_config(habits_config)
        st.sidebar.success(f"Added '{new_good_habit}'!")
        st.rerun()

for gh in list(habits_config["good_habits"]):
    col_s1, col_s2 = st.sidebar.columns([4, 1])
    col_s1.write(gh)
    if col_s2.button("X", key=f"del_gh_{gh}"):
        habits_config["good_habits"].remove(gh)
        save_habits_config(habits_config)
        st.rerun()

# --- CONTENT AREA SWITCHED BY SIDEBAR RADIO ---
if navigation_selection == "Daily Tracking & Check-In":
    st.title("Daily Habit & Relapse Tracker")

    if already_logged_today:
        st.warning(
            "Today's check-in is locked! You have already submitted your daily log. "
            "However, you can still add new habits or manage goals anytime using the sidebar!"
        )

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
                ["None", "Played Yamaha keyboard for 10 mins", "Did 3 Rubik's cube solves",
                 "Stepped outside for a walk"],
                disabled=already_logged_today
            )

    with col2:
        st.subheader("Daily Context & Nutrition (Inputs)")
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
    written_cue = st.text_input(
        "Describe what happened right before your habit or urge (cues analysis):",
        placeholder="Write your specific trigger context...",
        disabled=already_logged_today
    )

    st.subheader("Active Monthly Challenge Daily Check-In")
    goal_checkins = {}

    if not goals_data["monthly_goals"]:
        st.info("No active monthly goals. Create one in the Monthly Goals tab!")
    else:
        for idx, goal in enumerate(goals_data["monthly_goals"]):
            if goal["status"] == "Active":
                passed_today = st.radio(
                    f"Did you uphold your target for '{goal['goal_name']}' today?",
                    ["Pass (Maintained / Kept clean)", "Fail (Relapsed / Broke target)"],
                    key=f"goal_check_{idx}",
                    disabled=already_logged_today
                )
                goal_checkins[goal["goal_name"]] = 1 if "Pass" in passed_today else 0

    st.subheader("Daily Journal (+2 Coins)")
    journal_text = st.text_area("Additional thoughts or reflections:", placeholder="Write your thoughts...",
                                disabled=already_logged_today)

    if not already_logged_today:
        if st.button("Save Today's Log & Claim Coins", type="primary"):
            if goals_data["monthly_goals"]:
                for goal in goals_data["monthly_goals"]:
                    if goal["goal_name"] in goal_checkins:
                        if "daily_scores" not in goal:
                            goal["daily_scores"] = []
                        goal["daily_scores"].append(goal_checkins[goal["goal_name"]])

                        total_days = len(goal["daily_scores"])
                        if total_days >= 5:
                            pass_ratio = sum(goal["daily_scores"]) / total_days
                            if pass_ratio >= 0.80:
                                goal["current_eval"] = "On Track to Pass (>= 80%)"
                            else:
                                goal["current_eval"] = "At Risk of Failing (< 80%)"
                save_goals(goals_data)

            new_row = pd.DataFrame([{
                "Cue": cue_category,
                "Written_Cue": written_cue,
                "Routine_Split": split,
                "Sleep_Hours": sleep,
                "Stress": stress,
                "Calorie_Intake": calorie_intake,
                "Water_Goal": water_goal,
                "Protein_Goal": protein_goal,
                "Omega3_Goal": omega3_goal,
                "Streak": 1,
                "Completed": int(good_habit_done),
                "Relapsed": int(relapsed),
                "Alternate_Habit": alternate_habit,
                "Journal": journal_text,
                "Date": today_str
            }])

            if os.path.exists(USER_CSV):
                new_row.to_csv(USER_CSV, mode="a", header=False, index=False)
            else:
                new_row.to_csv(USER_CSV, index=False)

            st.success("Log saved and coins calculated successfully!")
            st.rerun()
    else:
        st.info("Check-in complete for today. You can still add or delete habits anytime in the sidebar!")

elif navigation_selection == "Monthly Goals & Timers":
    st.title("Monthly Goals, Timers & Target Completion Bonus")
    st.caption(
        "Complete your multi-month challenges and maintain an 80% success rate to claim your +25 Habit Coins 🪙 bonus!")

    with st.form("add_goal_form"):
        st.subheader("Launch a New Multi-Month Challenge")
        new_goal_name = st.text_input("Goal / Challenge Name:", placeholder="e.g., No Doomscrolling")
        duration = st.number_input("Duration (in Months):", min_value=1, max_value=24, value=2)
        submit_goal = st.form_submit_button("Start Challenge")

        if submit_goal and new_goal_name:
            start_dt = datetime.datetime.now()
            target_dt = start_dt + datetime.timedelta(days=int(duration * 30))

            goals_data["monthly_goals"].append({
                "goal_name": new_goal_name,
                "duration_months": duration,
                "target_timestamp": target_dt.isoformat(),
                "status": "Active",
                "daily_scores": [],
                "current_eval": "Not enough data yet (< 5 days)"
            })
            save_goals(goals_data)
            st.success(f"Successfully launched challenge: '{new_goal_name}'!")
            st.rerun()

    st.divider()
    st.subheader("Active Challenges & Target Bonus Claims")

    if not goals_data["monthly_goals"]:
        st.info("No active challenges running.")
    else:
        for idx, goal in enumerate(goals_data["monthly_goals"]):
            target_time = datetime.datetime.fromisoformat(goal["target_timestamp"])
            scores = goal.get("daily_scores", [])
            ratio_str = f"{(sum(scores) / len(scores) * 100):.1f}% Success Rate" if scores else "No check-ins yet"

            col_g1, col_g2, col_g3 = st.columns([3, 2, 1])
            col_g1.markdown(f"### **{goal['goal_name']}**")
            col_g1.caption(f"Status Evaluation: **{goal.get('current_eval', 'Pending')}** ({ratio_str})")

            remaining = target_time - datetime.datetime.now()
            is_completed = remaining.total_seconds() <= 0 or goal.get("current_eval") == "On Track to Pass (>= 80%)"

            if remaining.total_seconds() > 0:
                col_g2.metric("Time Remaining", f"{remaining.days} Days Left")
            else:
                col_g2.success("Challenge Period Ended!")

            goal_key = goal["goal_name"]
            already_claimed = goal_key in bonus_log.get("claimed_bonuses", [])

            if is_completed and not already_claimed:
                if col_g3.button("Claim +25 🪙 Coins!", key=f"claim_{idx}"):
                    bonus_log["claimed_bonuses"].append(goal_key)
                    save_bonus_log(bonus_log)
                    st.success("+25 🪙 Coins added to your wallet!")
                    st.rerun()
            elif already_claimed:
                col_g3.success("+25 Claimed")
            else:
                if col_g3.button("Delete", key=f"del_goal_{idx}"):
                    goals_data["monthly_goals"].pop(idx)
                    save_goals(goals_data)
                    st.rerun()
            st.divider()

elif navigation_selection == "Written Cue Analysis":
    st.title("Written Cue & Health Factor Analysis")
    st.caption(
        "Analyzing your written triggers, sleep, stress, calories, and health goals (water, protein, omega-3) to uncover cues behind breaking or making habits.")

    if logs_df.empty or "Written_Cue" not in logs_df.columns:
        st.info(
            "Log a few days of data with health factors and written trigger descriptions in Daily Tracking to unlock analysis!")
    else:
        st.subheader("Your Written Trigger Logs & Health Factors")
        display_cols = [c for c in
                        ["Date", "Written_Cue", "Sleep_Hours", "Stress", "Calorie_Intake", "Water_Goal", "Protein_Goal",
                         "Omega3_Goal", "Completed", "Relapsed"] if c in logs_df.columns]
        display_df = logs_df[display_cols].copy()
        display_df["Status"] = display_df.apply(lambda r: "Success" if r.get("Completed", 0) == 1 else (
            "Relapsed" if r.get("Relapsed", 0) == 1 else "Neutral"), axis=1)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Feature Importance Analysis")
        st.caption(
            "Shows which health, nutrition goals, and trigger inputs carry the most predictive weight in your tracking model.")

        try:
            rf_model = model.named_steps["rf"]
            feature_names = model.named_steps["prep"].get_feature_names_out()
            importances = rf_model.feature_importances_

            feat_df = pd.DataFrame({
                "Feature": feature_names,
                "Importance": importances
            }).sort_values(by="Importance", ascending=False)

            st.bar_chart(feat_df.set_index("Feature"))
        except Exception as e:
            st.info("Complete a few more logs to generate the feature weights chart.")

elif navigation_selection == "Weekly Report":
    st.title("Weekly Progress Report")
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

elif navigation_selection == "Journal Archive":
    st.title("Journal Archive")
    if logs_df.empty or "Journal" not in logs_df.columns:
        st.info("No journal entries yet.")
    else:
        for idx, row in logs_df.iterrows():
            with st.expander(f"Entry on {row.get('Date', 'Unknown Date')} — Relapsed: {row.get('Relapsed', 0)}"):
                st.write(f"**Written Trigger Context:** {row.get('Written_Cue', 'None provided.')}")
                st.write(
                    f"**Health Log:** Sleep: {row.get('Sleep_Hours', 'N/A')}h | Stress: {row.get('Stress', 'N/A')}/10 | Calories: {row.get('Calorie_Intake', 'N/A')}kcal | Water Goal Met: {row.get('Water_Goal', 'N/A')} | Protein Goal Met: {row.get('Protein_Goal', 'N/A')} | Omega-3 Taken: {row.get('Omega3_Goal', 'N/A')}")
                st.write(f"**Journal Note:** {row.get('Journal', 'No notes provided.')}")
                st.write(f"*Alternate Habit Used:* {row.get('Alternate_Habit', 'None')}")