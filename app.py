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

# ---- Storage helpers ----
def _default_state():
    return {
        "teams": DEFAULT_TEAMS,
        "criteria": DEFAULT_CRITERIA,
        "scores": {t: {c: 0 for c in DEFAULT_CRITERIA} for t in DEFAULT_TEAMS},
        "updated_at": None,
    }

def load_state():
    if not os.path.exists(DATA_FILE):
        state = _default_state()
        save_state(state)
        return state
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        state = _default_state()
        save_state(state)
        return state

def save_state(state: dict):
    state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

# ---- UI helpers ----
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
    # Tie-breakers: Total desc, then Criterion 5 desc (if exists), then alphabetical
    if len(criteria) >= 5 and criteria[4] in df.columns:
        df = df.sort_values(["Total", criteria[4], "Team"], ascending=[False, False, True])
    else:
        df = df.sort_values(["Total", "Team"], ascending=[False, True])
    df.reset_index(drop=True, inplace=True)
    df.index = df.index + 1
    return df

# ---- App ----
state = load_state()

st.sidebar.title("Mode")

mode = st.sidebar.radio("Select mode", ["Public Screen", "Admin (Jury)"], index=0)

admin_pin_required = True
PIN = st.secrets.get("ADMIN_PIN", None)
if PIN is None:
    admin_pin_required = False  # if you don't set PIN, admin is open

if mode == "Admin (Jury)":
    if admin_pin_required:
        entered = st.sidebar.text_input("Admin PIN", type="password")
        if entered != PIN:
            st.warning("Enter the correct PIN to edit scores.")
            st.stop()

    st.title("🛠️ Admin — Enter scores")

    with st.expander("Settings (optional)"):
        teams_text = st.text_area("Teams (one per line)", "\n".join(state["teams"]))
        criteria_text = st.text_area("Criteria (one per line)", "\n".join(state["criteria"]))

        if st.button("Apply team/criteria changes"):
            teams = [x.strip() for x in teams_text.splitlines() if x.strip()]
            criteria = [x.strip() for x in criteria_text.splitlines() if x.strip()]
            if len(teams) == 0 or len(criteria) == 0:
                st.error("Teams and criteria cannot be empty.")
            else:
                # rebuild scores preserving intersection where possible
                new_scores = {t: {c: 0 for c in criteria} for t in teams}
                for t in teams:
                    for c in criteria:
                        if t in state["scores"] and c in state["scores"][t]:
                            new_scores[t][c] = int(state["scores"][t][c])
                state["teams"] = teams
                state["criteria"] = criteria
                state["scores"] = new_scores
                save_state(state)
                st.success("Updated configuration.")
                st.rerun()

    st.caption(f"Max per criterion: {MAX_PER_CRITERION} • Updated: {state.get('updated_at')}")

    teams = state["teams"]
    criteria = state["criteria"]

    st.subheader("Enter scores (0–2)")
    # One team per row, 5 criteria as number inputs
    for t in teams:
        with st.container(border=True):
            cols = st.columns([2] + [1]*len(criteria))
            cols[0].markdown(f"### {t}")
            for i, c in enumerate(criteria):
                key =
