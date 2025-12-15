import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Live Jury Scores", layout="wide")

# ---- CONFIG ----
DEFAULT_TEAMS = [f"Team {i}" for i in range(1, 8)]
DEFAULT_CRITERIA = [f"Criterion {i}" for i in range(1, 6)]
MAX_PER_CRITERION = 2
DATA_FILE = "scores.json"


def default_state():
    return {
        "teams": DEFAULT_TEAMS,
        "criteria": DEFAULT_CRITERIA,
        "scores": {t: {c: 0 for c in DEFAULT_CRITERIA} for t in DEFAULT_TEAMS},
        "updated_at": None,
    }


def load_state():
    if not os.path.exists(DATA_FILE):
        state = default_state()
        save_state(state)
        return state
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        state = default_state()
        save_state(state)
        return state


def save_state(state: dict):
    state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def compute_table(state: dict) -> pd.DataFrame:
    teams = state["teams"]
    criteria = state["criteria"]
    rows = []
    for t in teams:
        row = {"Team": t}
        total = 0
        for c in criteria:
            v = int(state["scores"][t].get(c, 0))
            row[c] = v
            total += v
        row["Total"] = total
        rows.append(row)

    df = pd.DataFrame(rows)

    # Tie-break: Total desc, then last criterion desc (if exists), then Team name
    if len(criteria) >= 1 and criteria[-1] in df.columns:
        df = df.sort_values(["Total", criteria[-1], "Team"], ascending=[False, False, True])
    else:
        df = df.sort_values(["Total", "Team"], ascending=[False, True])

    df.reset_index(drop=True, inplace=True)
    df.index = df.index + 1
    return df


# ---- APP ----
state = load_state()

st.sidebar.title("Mode")
mode = st.sidebar.radio("Select mode", ["Public Screen", "Admin (Jury)"], index=0)

PIN = st.secrets.get("ADMIN_PIN", None)
pin_required = PIN is not None

if mode == "Admin (Jury)":
    if pin_required:
        entered = st.sidebar.text_input("Admin PIN", type="password")
        if entered != PIN:
            st.warning("Enter the correct PIN to edit scores.")
            st.stop()

    st.title("🛠️ Admin — Enter scores")
    st.caption(f"Max per criterion: {MAX_PER_CRITERION} • Updated: {state.get('updated_at')}")

    teams = state["teams"]
    criteria = state["criteria"]

    st.subheader("Enter scores (0–2)")
    for t in teams:
        with st.container(border=True):
            cols = st.columns([2] + [1] * len(criteria))
            cols[0].markdown(f"### {t}")

            for i, c in enumerate(criteria):
                input_key = f"{t}__{c}"
                default_val = int(state["scores"][t].get(c, 0))

                val = cols[i + 1].number_input(
                    c,
                    min_value=0,
                    max_value=MAX_PER_CRITERION,
                    step=1,
                    value=default_val,
                    key=input_key,
                )
                state["scores"][t][c] = int(val)

    c1, c2, c3 = st.columns([1, 1, 2])

    if c1.button("💾 Save"):
        save_state(state)
        st.success("Saved.")
        st.rerun()

    if c2.button("↩ Reset all to 0"):
        state = default_state()
        save_state(state)
        st.success("Reset done.")
        st.rerun()

    st.divider()
    st.subheader("Preview (public view)")
    df = compute_table(state)
    st.dataframe(df, use_container_width=True)

else:
    st.title("🏆 Live Results")
    st.caption(f"Last update: {state.get('updated_at')}")

    refresh = st.sidebar.toggle("Auto-refresh (5s)", value=True)
    if refresh:
        st.markdown("<meta http-equiv='refresh' content='5'>", unsafe_allow_html=True)

    df = compute_table(state)

    winner = df.iloc[0]["Team"] if len(df) else "—"
    st.metric("Current winner", winner)

    st.subheader("Leaderboard")
    st.dataframe(df[["Team", "Total"]], use_container_width=True, height=350)

    st.subheader("Totals by team")
    st.bar_chart(df.set_index("Team")["Total"])

    st.subheader("Criteria breakdown")
    criteria_cols = [c for c in state["criteria"] if c in df.columns]
    st.bar_chart(df.set_index("Team")[criteria_cols])

    st.caption("Input is hidden on this screen. Only results are shown.")
