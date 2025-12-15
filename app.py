import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import sys

# --- CONFIGURATION / SECRETS CHECK ---
try:
    # Safely retrieve secrets with a robust check
    SHEET_NAME = st.secrets["app"]["sheet_name"]
    WORKSHEET_NAME = st.secrets["app"]["worksheet_name"]
    GCP_SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
    
    # Check for a specific key existence to rule out general config failure
    if not st.secrets.get("gcp_service_account_check", {}).get("GCP_KEY_EXISTS"):
        raise KeyError("GCP_KEY_EXISTS check failed.")

except KeyError:
    st.error("❌ Configuration Error: Streamlit secrets not loaded correctly.")
    st.markdown("""
        **Troubleshooting Steps:**
        1.  Ensure you have a `.streamlit/secrets.toml` file (local) or your secrets are correctly configured in Streamlit Cloud.
        2.  Verify the keys `[gcp_service_account]`, `[app]`, and `[gcp_service_account_check]` exist and are spelled exactly as shown.
        3.  The app cannot proceed without these secrets.
    """)
    sys.exit() # Use sys.exit() instead of st.stop() for robustness if the error happens very early

st.set_page_config(page_title="Hackathon Live Scores", layout="wide")
st.title("🏆 Hackathon Live Scoring Dashboard")

# ---- Auto refresh ----
auto = st.toggle("Auto-refresh (10s)", value=True)
if auto:
    # Use the 'time' module to generate a unique key based on refresh interval
    st.autorefresh(interval=10_000, key="refresh")

@st.cache_resource
def gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    
    # FIX: Create a copy of the secrets dictionary to modify it, 
    # and use .strip() on the private_key to remove any hidden whitespace 
    # that caused the earlier binascii.Error.
    sa_info = GCP_SERVICE_ACCOUNT_INFO.copy()
    sa_info["private_key"] = sa_info["private_key"].strip() 
    
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)

def load_raw():
    # This function will only be called if the secrets check passed
    gc = gsheet_client()
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet(WORKSHEET_NAME)
    return pd.DataFrame(ws.get_all_records())

def normalize_matrix(df: pd.DataFrame) -> pd.DataFrame:
    # Detect team prefixes from columns like "Команда 1: Критерий 1"
    team_prefixes = sorted({
        c.split(":")[0].strip()
        for c in df.columns
        if ":" in c and "Команда" in c
    })

    rows = []
    for _, r in df.iterrows():
        ts = r.get("Timestamp") or r.get("Отметка времени")

        for tp in team_prefixes:
            vals = []
            ok = True
            for k in range(1, 6):
                col = f"{tp}: Критерий {k}"
                if col not in df.columns:
                    ok = False
                    break
                v = r.get(col)
                if v in ("", None):
                    ok = False
                    break
                # Ensure value is convertible to int before appending
                try:
                    vals.append(int(v))
                except (ValueError, TypeError):
                    ok = False
                    break
                    
            if ok:
                rows.append({
                    "timestamp": ts,
                    "team": tp,
                    "c1": vals[0], "c2": vals[1], "c3": vals[2], "c4": vals[3], "c5": vals[4],
                    "total": sum(vals)
                })
    return pd.DataFrame(rows)

# --- START APP LOGIC ---

df_raw = load_raw()
if df_raw.empty:
    st.info("No votes yet. Dataframe is empty.")
    st.stop()

df = normalize_matrix(df_raw)
if df.empty:
    st.error("Could not parse form columns. Show first rows for debugging:")
    st.dataframe(df_raw.head(), use_container_width=True)
    st.stop()

# ---- Aggregation ----
team = (df.groupby("team")
          .agg(
              votes=("total","count"),
              total_score=("total","sum"),
              avg_score=("total","mean"),
              c1=("c1","sum"), c2=("c2","sum"), c3=("c3","sum"), c4=("c4","sum"), c5=("c5","sum"),
          )
          .reset_index()
       )

# Ranking with tie-breakers
team = team.sort_values(by=["total_score", "avg_score", "c5"], ascending=[False, False, False]).reset_index(drop=True)
winner = team.iloc[0]["team"]

c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("📌 Leaderboard")
    st.dataframe(team[["team","votes","total_score","avg_score"]], use_container_width=True)

with c2:
    st.subheader("🥇 Winner")
    st.metric("Current winner", winner)
    st.caption("Tie-break: total_score → avg_score → criterion 5")

st.subheader("📊 Total score by team")
st.bar_chart(team.set_index("team")["total_score"])

st.subheader("📊 Criteria breakdown (sum)")
st.bar_chart(team.set_index("team")[["c1","c2","c3","c4","c5"]])

with st.expander("Audit: normalized votes"):
    st.dataframe(df.sort_values(["team","timestamp"]), use_container_width=True)
