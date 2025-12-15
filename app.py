import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import sys

# --- RESILIENT SECRETS LOADER ---
# Check for required sections and stop if secrets are malformed or missing
def load_config():
    try:
        config_data = {
            "gcp_info": st.secrets["gcp_service_account"],
            "sheet_name": st.secrets["app"]["sheet_name"],
            "worksheet_name": st.secrets["app"]["worksheet_name"]
        }
        # Check for the private key specifically to catch partial loads
        if not config_data["gcp_info"].get("private_key"):
            raise KeyError("Private key missing from gcp_service_account section.")
        return config_data
        
    except KeyError as e:
        st.error(f"❌ Configuration Error: Streamlit secrets not loaded correctly. Missing key: {e}")
        st.markdown("""
            **Troubleshooting Steps (Streamlit Cloud):**
            1. Go to App Settings -> Secrets.
            2. Ensure the sections `[gcp_service_account]` and `[app]` are present.
            3. Verify the key names like `private_key`, `sheet_name`, etc. are spelled exactly right.
        """)
        sys.exit()

# Load and validate configuration once
APP_CONFIG = load_config()

st.set_page_config(page_title="Hackathon Live Scores", layout="wide")
st.title("🏆 Hackathon Live Scoring Dashboard")

# ---- Auto refresh ----
auto = st.toggle("Auto-refresh (10s)", value=True)
if auto:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=10_000, key="refresh")

@st.cache_resource
def gsheet_client(gcp_service_account_info):
    """Initializes and caches the gspread client using the provided secrets."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    
    # FIX: Copy the info and strip the key to prevent binascii errors
    sa_info = dict(gcp_service_account_info)
    sa_info["private_key"] = sa_info["private_key"].strip()
    
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)

def load_raw():
    # Pass the secrets directly to the cached function
    gc = gsheet_client(APP_CONFIG["gcp_info"])
    
    sh = gc.open(APP_CONFIG["sheet_name"])
    ws = sh.worksheet(APP_CONFIG["worksheet_name"])
    return pd.DataFrame(ws.get_all_records())

def normalize_matrix(df: pd.DataFrame) -> pd.DataFrame:
    # ... (rest of the normalization function remains the same)
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
                v = r.get(col)
                if col not in df.columns or v in ("", None):
                    ok = False
                    break
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

# --- EXECUTION ---

df_raw = load_raw()
if df_raw.empty:
    st.info("No votes yet. Dataframe is empty.")
    st.stop()

df = normalize_matrix(df_raw)
if df.empty:
    st.error("Could not parse form columns. Show first rows for debugging:")
    st.dataframe(df_raw.head(), use_container_width=True)
    st.stop()

# ---- Aggregation and Display Logic (as before) ----
team = (df.groupby("team")
          .agg(
              votes=("total","count"), total_score=("total","sum"), avg_score=("total","mean"),
              c1=("c1","sum"), c2=("c2","sum"), c3=("c3","sum"), c4=("c4","sum"), c5=("c5","sum"),
          )
          .reset_index()
       )

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

with st.expander("Audit: normalized votes"):
    st.dataframe(df.sort_values(["team","timestamp"]), use_container_width=True)
