import os
import json
import datetime
import time
import pandas as pd
import streamlit as st
from ml_engine import train_and_get_model, USER_CSV

st.set_page_config(page_title="Atomic Habit & Goal Tracker", page_icon="⚡", layout="wide")

GOALS_FILE = "goals_config.json"


def load_goals():
    if os.path.exists(GOALS_FILE):
        with open(GOALS_FILE, "r") as f:
            return json.load(f)
    return {"monthly_goals": []}


def save_goals(data):
    with open(GOALS_FILE, "w") as f:
        json.dump(data, f, indent=2)


goals_data = load_goals()

# Train ML model & load logs
model = train_and_get_model()
logs_df = pd.read_csv(USER_CSV) if os.path.exists(USER_CSV) else pd.DataFrame()

# --- NAVIGATION TABS ---
tab_track, tab_goals, tab_report, tab_journal = st.tabs([
    "🎯 Daily Tracking",
    "⏳ Monthly Goals & Timers",
    "📊 ML Weekly Report",
    "📓 Journal Archive"
])

with tab_track:
    st.title("⚡ Daily Habit & Relapse Tracker")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Habit Execution")
        good_habit_done = st.checkbox("✅ Completed Good Habit Today?")
        relapsed = st.checkbox("❌ Relapsed on Bad Habit Today?")

        alternate_habit = "None"
        if relapsed:
            alternate_habit = st.selectbox(
                "Alternate Habit Used to Recover:",
                ["None", "Played Yamaha keyboard for 10 mins", "Did 3 Rubik's cube solves",
                 "Stepped outside for a walk"]
            )

    with col2:
        st.subheader("Daily Context (ML Inputs)")
        cue = st.selectbox("Trigger Cue:", ["Morning Routine", "After Class", "After Dinner", "Random Time"])
        split = st.selectbox("Routine Split:", ["Push", "Pull", "Legs", "Rest"])
        sleep = st.slider("Sleep Hours:", 4.0, 10.0, 7.0, 0.5)
        energy = st.slider("Energy (1-10):", 1, 10, 7)
        stress = st.slider("Stress (1-10):", 1, 10, 4)

    st.subheader("Daily Journal")
    journal_text = st.text_area("How did today feel? Note triggers or wins:", placeholder="Write your thoughts...")

    if st.button("💾 Save Today's Log", type="primary"):
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
            "Date": datetime.date.today().isoformat()
        }])

        if os.path.exists(USER_CSV):
            new_row.to_csv(USER_CSV, mode="a", header=False, index=False)
        else:
            new_row.to_csv(USER_CSV, index=False)

        st.balloons()
        st.success("Log saved successfully!")

with tab_goals:
    st.title("⏳ Monthly Goals & Live Countdowns")
    st.caption("Manage long-term challenges (e.g., 'No doomscrolling for 2 months') with active live countdown timers.")

    with st.form("add_goal_form"):
        st.subheader("Launch a New Multi-Month Challenge")
        new_goal_name = st.text_input("Goal / Challenge Name (e.g., No Doomscrolling):",
                                      placeholder="e.g. No Doomscroll")
        duration = st.number_input("Duration (in Months):", min_value=1, max_value=24, value=2)
        submit_goal = st.form_submit_button("🚀 Start Challenge & Timer")

        if submit_goal and new_goal_name:
            start_dt = datetime.datetime.now()
            # Calculate target timestamp by adding approximate months (30 days per month)
            target_dt = start_dt + datetime.timedelta(days=int(duration * 30))

            goals_data["monthly_goals"].append({
                "goal_name": new_goal_name,
                "duration_months": duration,
                "target_timestamp": target_dt.isoformat(),
                "status": "Active"
            })
            save_goals(goals_data)
            st.success(f"Successfully launched challenge: '{new_goal_name}'!")
            st.rerun()

    st.divider()
    st.subheader("Active Goal Timers")

    if not goals_data["monthly_goals"]:
        st.info("No active challenges running. Launch one above!")
    else:
        for idx, goal in enumerate(goals_data["monthly_goals"]):
            target_time = datetime.datetime.fromisoformat(goal["target_timestamp"])
            now = datetime.datetime.now()
            remaining = target_time - now

            col_g1, col_g2, col_g3 = st.columns([3, 2, 1])
            col_g1.markdown(f"### **🎯 {goal['goal_name']}**")
            col_g1.caption(f"Duration: {goal['duration_months']} Months | Target: {target_time.strftime('%b %d, %Y')}")

            if remaining.total_seconds() > 0:
                days = remaining.days
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                seconds = remaining.seconds % 60

                col_g2.metric("Timer Remaining", f"{days}d {hours}h {minutes}m {seconds}s")
            else:
                col_g2.success("🎉 Challenge Completed!")

            if col_g3.button("🗑️ Delete Goal", key=f"del_goal_{idx}"):
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
        r1.metric("Relapses (Last 7 Days)", f"{total_relapses} Times")
        r2.metric("Completion Rate (Last 7 Days)", f"{completion_rate:.1f}%")
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