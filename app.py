import os
import json
import datetime
import pandas as pd
import streamlit as st
from ml_engine import train_and_get_model, get_dataset_comparison, USER_CSV

st.set_page_config(page_title="Advanced Atomic ML Tracker", page_icon="⚡", layout="wide")

CONFIG_FILE = "habits_config.json"


def load_habit_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "good_habits": ["Gym Workout (PPLR)", "Daily LeetCode Problem"],
        "bad_habits": ["Doomscrolling on Phone", "Procrastinating"]
    }


def save_habit_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


config = load_habit_config()

# Train/Load ML Model
model = train_and_get_model()

# Load Personal Logs
if os.path.exists(USER_CSV):
    logs_df = pd.read_csv(USER_CSV)
else:
    logs_df = pd.DataFrame()

# --- SIDEBAR: HABIT MANAGER (ADD & DELETE) ---
st.sidebar.title("⚙️ Habit Manager")
st.sidebar.caption("Add new habits or delete bad habits you've quit!")

st.sidebar.subheader("✨ Good Habits")
new_good = st.sidebar.text_input("Add new good habit:")
if st.sidebar.button("Add Good Habit") and new_good:
    if new_good not in config["good_habits"]:
        config["good_habits"].append(new_good)
        save_habit_config(config)
        st.sidebar.success(f"Added '{new_good}'!")
        st.rerun()

for gh in list(config["good_habits"]):
    col_g1, col_g2 = st.sidebar.columns([4, 1])
    col_g1.write(gh)
    if col_g2.button("🗑️", key=f"del_g_{gh}"):
        config["good_habits"].remove(gh)
        save_habit_config(config)
        st.rerun()

st.sidebar.divider()

st.sidebar.subheader("🛑 Bad Habits (Quit & Delete)")
new_bad = st.sidebar.text_input("Add bad habit to track/quit:")
if st.sidebar.button("Add Bad Habit") and new_bad:
    if new_bad not in config["bad_habits"]:
        config["bad_habits"].append(new_bad)
        save_habit_config(config)
        st.sidebar.success(f"Added '{new_bad}'!")
        st.rerun()

st.sidebar.caption("Click delete once you've successfully quit a bad habit permanently:")
for bh in list(config["bad_habits"]):
    col_b1, col_b2 = st.sidebar.columns([4, 1])
    col_b1.write(bh)
    if col_b2.button("🗑️ Quit/Delete", key=f"del_b_{bh}"):
        config["bad_habits"].remove(bh)
        save_habit_config(config)
        st.sidebar.success(f"congratulations on quitting '{bh}'!")
        st.rerun()

# --- TABS FOR NAVIGATION ---
tab_log, tab_report, tab_journal = st.tabs(
    ["🎯 Daily Tracker & Urges", "📊 ML Weekly Report & Benchmark", "📓 Journal Archive"])

with tab_log:
    st.title("⚡ Daily Habit & Relapse Tracker")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. Habit Execution")
        active_good = st.selectbox("Select Good Habit to Track Today:",
                                   config["good_habits"] if config["good_habits"] else ["No habits added"])
        good_done = st.checkbox(f"✅ Completed '{active_good}' Today?")

        active_bad = st.selectbox("Target Bad Habit to Watch Out For:",
                                  config["bad_habits"] if config["bad_habits"] else ["No bad habits"])
        relapsed = st.checkbox(f"❌ Relapsed on '{active_bad}' Today?")

        alternate_used = "None"
        if relapsed:
            alternate_used = st.selectbox(
                "3. Alternate Habit Used to Recover/Pivot:",
                ["None", "Played Yamaha keyboard for 10 mins", "Did 3 Rubik's cube solves",
                 "Stepped outside for a 5-min walk"]
            )

    with c2:
        st.subheader("2. Daily Context (ML Inputs)")
        sleep = st.slider("Sleep Hours:", 4.0, 10.0, 7.0, 0.5)
        energy = st.slider("Energy (1-10):", 1, 10, 7)
        stress = st.slider("Stress (1-10):", 1, 10, 4)

    st.subheader("5. Daily Journal")
    journal_text = st.text_area("How did today feel? What triggered urges or successes?",
                                placeholder="Write your thoughts here...")

    if st.button("💾 Save Today's Log", type="primary"):
        new_row = pd.DataFrame([{
            "Cue": f"Tracked: {active_good}",
            "Routine_Split": "General",
            "Sleep_Hours": sleep,
            "Energy": energy,
            "Stress": stress,
            "Streak": 1,
            "Completed": int(good_done),
            "Relapsed": int(relapsed),
            "Alternate_Habit": alternate_used,
            "Journal": journal_text,
            "Date": datetime.date.today().isoformat()
        }])

        if os.path.exists(USER_CSV):
            new_row.to_csv(USER_CSV, mode="a", header=False, index=False)
        else:
            new_row.to_csv(USER_CSV, index=False)

        st.balloons()
        st.success("Log saved successfully! Refresh to view updated reports.")

with tab_report:
    st.title("📊 ML Weekly Progress Report & Benchmarks")

    if logs_df.empty or "Relapsed" not in logs_df.columns:
        st.info("Log a few days of data in the first tab to generate your weekly ML report!")
    else:
        last_7_days = logs_df.tail(7)
        total_relapses_week = last_7_days["Relapsed"].sum()

        r1, r2, r3 = st.columns(3)
        r1.metric("Weekly Relapses (Last 7 Days)", f"{total_relapses_week} Times")
        r2.metric("Weekly Completion Rate", f"{(last_7_days['Completed'].mean() * 100):.1f}%")
        r3.metric("Total Days Logged", f"{len(logs_df)} Days")

        st.divider()

        st.subheader("🔍 Dataset Benchmark Comparison")
        st.caption("Comparing your personal habit success and stress levels against baseline research data.")

        success_comp, stress_comp = get_dataset_comparison()
        if success_comp:
            antecol1, antecol2 = st.columns(2)
            with antecol1:
                st.metric("Your Success Rate", f"{success_comp['user_success']:.1f}%",
                          f"{success_comp['user_success'] - success_comp['base_success']:.1f}% vs Baseline")
            with antecol2:
                st.metric("Your Avg Stress Level", f"{stress_comp['user_stress']:.1f}/10",
                          f"{stress_comp['user_stress'] - stress_comp['base_stress']:.1f} vs Baseline")

with tab_journal:
    st.title("📓 Journal Archive")
    if logs_df.empty or "Journal" not in logs_df.columns:
        st.info("No journal entries yet.")
    else:
        for idx, row in logs_df.iterrows():
            with st.expander(f"Entry on {row.get('Date', 'Unknown Date')} — Relapsed: {row.get('Relapsed', 0)}"):
                st.write(f"**Journal Note:** {row.get('Journal', 'No notes provided.')}")
                st.write(f"*Alternate Habit Used:* {row.get('Alternate_Habit', 'None')}")