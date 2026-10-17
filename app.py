import os
import json
import datetime
import pandas as pd
import streamlit as st
from ml_engine import train_and_get_model, USER_CSV

st.set_page_config(page_title="Atomic Habit & Goal Tracker", page_icon="⚡", layout="wide")

GOALS_FILE = "goals_config.json"
BONUS_LOG_FILE = "bonus_coins_log.json"


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


goals_data = load_goals()
bonus_log = load_bonus_log()

# Train ML model & load logs
model = train_and_get_model()
logs_df = pd.read_csv(USER_CSV) if os.path.exists(USER_CSV) else pd.DataFrame()


# --- CALCULATE HABIT COINS (Clamped at a minimum of 0) ---
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

    # Add +25 coins for each completed goal bonus claimed
    coins += len(bonuses.get("claimed_bonuses", [])) * 25

    # Ensure coins never drop below 0
    return max(0, coins)


total_coins = calculate_habit_coins(logs_df, bonus_log)

# Check if user already logged today (Locking Mechanism)
today_str = datetime.date.today().isoformat()
already_logged_today = False
if not logs_df.empty and "Date" in logs_df.columns:
    already_logged_today = today_str in logs_df["Date"].values

# --- SIDEBAR: HABIT COINS WALLET ---
st.sidebar.title("🪙 Habit Wallet")
st.sidebar.metric("Habit Coins Balance", f"{total_coins} Coins")
st.sidebar.caption(
    "Earn: +5 Good Habit | Deduct: -3 Relapse | Earn: +2 Journal | 🎯 **+25 Target Completed!** (Minimum: 0)")

# --- NAVIGATION TABS ---
tab_track, tab_goals, tab_report, tab_journal = st.tabs([
    "🎯 Daily Tracking & Check-In",
    "⏳ Monthly Goals & Timers",
    "📊 ML Weekly Report",
    "📓 Journal Archive"
])

with tab_track:
    st.title("⚡ Daily Habit & Relapse Tracker")

    if already_logged_today:
        st.warning(
            "🔒 **Today's check-in is locked!** You have already submitted your data for today. "
            "To prevent cheating or editing past logs ('lagging'), daily entries can only be submitted once per day."
        )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Habit Execution")
        good_habit_done = st.checkbox("✅ Completed Good Habit Today?", disabled=already_logged_today)
        relapsed = st.checkbox("❌ Relapsed on Bad Habit Today?", disabled=already_logged_today)

        alternate_habit = "None"
        if relapsed:
            alternate_habit = st.selectbox(
                "Alternate Habit Used to Recover:",
                ["None", "Played Yamaha keyboard for 10 mins", "Did 3 Rubik's cube solves",
                 "Stepped outside for a walk"],
                disabled=already_logged_today
            )

    with col2:
        st.subheader("Daily Context (ML Inputs)")
        cue = st.selectbox("Trigger Cue:", ["Morning Routine", "After Class", "After Dinner", "Random Time"],
                           disabled=already_logged_today)
        split = st.selectbox("Routine Split:", ["Push", "Pull", "Legs", "Rest"], disabled=already_logged_today)
        sleep = st.slider("Sleep Hours:", 4.0, 10.0, 7.0, 0.5, disabled=already_logged_today)
        energy = st.slider("Energy (1-10):", 1, 10, 7, disabled=already_logged_today)
        stress = st.slider("Stress (1-10):", 1, 10, 4, disabled=already_logged_today)

    # Active Monthly Challenge Check-In
    st.divider()
    st.subheader("🎯 Active Monthly Challenge Daily Check-In")
    goal_checkins = {}

    if not goals_data["monthly_goals"]:
        st.info("No active monthly goals. Create one in the 'Monthly Goals' tab!")
    else:
        for idx, goal in enumerate(goals_data["monthly_goals"]):
            if goal["status"] == "Active":
                passed_today = st.radio(
                    f"Did you uphold your target for **'{goal['goal_name']}'** today?",
                    ["Pass (Maintained / Kept clean)", "Fail (Relapsed / Broke target)"],
                    key=f"goal_check_{idx}",
                    disabled=already_logged_today
                )
                goal_checkins[goal["goal_name"]] = 1 if "Pass" in passed_today else 0

    st.subheader("Daily Journal (+2 Coins)")
    journal_text = st.text_area("How did today feel? Note triggers or wins:", placeholder="Write your thoughts...",
                                disabled=already_logged_today)

    if not already_logged_today:
        if st.button("💾 Save Today's Log & Claim Coins", type="primary"):
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
                "Cue": cue,
                "Routine_Split": split,
                "Sleep_Hours": sleep,
                "Energy": energy,
                "Stress": stress,
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

            st.balloons()
            st.success("Log saved and coins calculated successfully!")
            st.rerun()
    else:
        st.info("Check-in complete for today. Come back tomorrow!")

with tab_goals:
    st.title("⏳ Monthly Goals, Timers & Target Completion Bonus")
    st.caption(
        "Complete your multi-month challenges and maintain an 80% success rate to claim your +25 Habit Coins bonus!")

    with st.form("add_goal_form"):
        st.subheader("Launch a New Multi-Month Challenge")
        new_goal_name = st.text_input("Goal / Challenge Name:", placeholder="e.g., No Doomscrolling")
        duration = st.number_input("Duration (in Months):", min_value=1, max_value=24, value=2)
        submit_goal = st.form_submit_button("🚀 Start Challenge")

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
            col_g1.markdown(f"### **🎯 {goal['goal_name']}**")
            col_g1.caption(f"Status Evaluation: **{goal.get('current_eval', 'Pending')}** ({ratio_str})")

            remaining = target_time - datetime.datetime.now()
            is_completed = remaining.total_seconds() <= 0 or goal.get("current_eval") == "On Track to Pass (>= 80%)"

            if remaining.total_seconds() > 0:
                col_g2.metric("Time Remaining", f"{remaining.days} Days Left")
            else:
                col_g2.success("🎉 Challenge Period Ended!")

            goal_key = goal["goal_name"]
            already_claimed = goal_key in bonus_log.get("claimed_bonuses", [])

            if is_completed and not already_claimed:
                if col_g3.button("🎁 Claim +25 Coins!", key=f"claim_{idx}"):
                    bonus_log["claimed_bonuses"].append(goal_key)
                    save_bonus_log(bonus_log)
                    st.balloons()
                    st.success("🎉 +25 Coins added to your wallet!")
                    st.rerun()
            elif already_claimed:
                col_g3.success("✅ +25 Claimed")
            else:
                if col_g3.button("🗑️ Delete", key=f"del_goal_{idx}"):
                    goals_data["monthly_goals"].pop(idx)
                    save_goals(goals_data)
                    st.rerun()
            st.divider()

with tab_report:
    st.title("📊 ML Weekly Progress Report")
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

with tab_journal:
    st.title("📓 Journal Archive")
    if logs_df.empty or "Journal" not in logs_df.columns:
        st.info("No journal entries yet.")
    else:
        for idx, row in logs_df.iterrows():
            with st.expander(f"Entry on {row.get('Date', 'Unknown Date')} — Relapsed: {row.get('Relapsed', 0)}"):
                st.write(f"**Journal Note:** {row.get('Journal', 'No notes provided.')}")
                st.write(f"*Alternate Habit Used:* {row.get('Alternate_Habit', 'None')}")