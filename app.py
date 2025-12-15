import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Jury Scores", layout="wide")

# ---------------- CONFIG ----------------
DEFAULT_TEAMS = [f"Team {i}" for i in range(1, 8)]
DEFAULT_CRITERIA = [f"Criterion {i}" for i in range(1, 6)]
MAX_PER_CRITERION = 2
DATA_FILE = "scores.json"

PIN = st.secrets.get("ADMIN_PIN", None)  # set in Streamlit Secrets
PIN_REQUIRED = PIN is not None


# ---------------- BILINGUAL UI HELPERS ----------------
def bi(kk: str, ru: str) -> str:
    # Kazakh first, Russian below (subtle)
    return f"<div style='line-height:1.2'><div><b>{kk}</b></div><div style='color:#8a8a8a'>{ru}</div></div>"


def bi_h1(kk: str, ru: str):
    st.markdown(f"<h2 style='margin-bottom:0.2rem'>{kk}</h2><div style='color:#8a8a8a'>{ru}</div>", unsafe_allow_html=True)


def bi_caption(kk: str, ru: str):
    st.markdown(f"<div style='color:#8a8a8a'>{kk} • {ru}</div>", unsafe_allow_html=True)


# ---------------- STORAGE ----------------
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


# ---------------- COMPUTATION ----------------
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

    # Tie-break: Total desc, then last criterion desc, then Team name
    if len(criteria) >= 1 and criteria[-1] in df.columns:
        df = df.sort_values(["Total", criteria[-1], "Team"], ascending=[False, False, True])
    else:
        df = df.sort_values(["Total", "Team"], ascending=[False, True])

    df.reset_index(drop=True, inplace=True)
    df.index = df.index + 1
    return df


def criterion_averages(df: pd.DataFrame, criteria: list[str]) -> pd.DataFrame:
    # Average score for each criterion across teams (trend view)
    av = {c: float(df[c].mean()) for c in criteria}
    out = pd.DataFrame({"Criterion": list(av.keys()), "Average": list(av.values())})
    out = out.sort_values("Average", ascending=False).reset_index(drop=True)
    return out


# ---------------- PLOTS ----------------
def plot_radar_for_team(team_name: str, values: list[int], criteria: list[str], max_val: int = 2):
    # Polar radar chart (matplotlib)
    n = len(criteria)
    angles = np.linspace(0, 2*np.pi, n, endpoint=False).tolist()
    values = values + values[:1]
    angles = angles + angles[:1]

    fig = plt.figure(figsize=(3.2, 3.2))
    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(criteria, fontsize=8)

    ax.set_ylim(0, max_val)
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["0", "1", "2"], fontsize=8)

    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.15)

    ax.set_title(team_name, fontsize=11, pad=12)
    fig.tight_layout()
    return fig


# ---------------- APP ----------------
state = load_state()

st.sidebar.markdown("### Mode / Режим")
# Default = Admin first
mode = st.sidebar.radio(
    " ",
    ["Admin (Jury) / Әділқазы", "Public Screen / Экран"],
    index=0
)

if mode.startswith("Admin"):
    if PIN_REQUIRED:
        entered = st.sidebar.text_input("PIN", type="password")
        if entered != PIN:
            st.warning("PIN енгізіңіз / Введите PIN")
            st.stop()

    bi_h1("Әділқазы панелі", "Панель жюри")
    bi_caption(
        f"Жаңартылды: {state.get('updated_at')}",
        f"Обновлено: {state.get('updated_at')}"
    )

    # Settings: editable teams & criteria
    st.markdown("---")
    st.markdown(bi("Атауларды баптау", "Настройка названий"), unsafe_allow_html=True)

    with st.expander("✏️ " + "Командалар және критерийлер / Команды и критерии"):
        teams_text = st.text_area(
            "Командалар (әр жолға бір команда) / Команды (по одной в строке)",
            "\n".join(state["teams"]),
            height=160
        )
        criteria_text = st.text_area(
            "Критерийлер (әр жолға бір критерий) / Критерии (по одному в строке)",
            "\n".join(state["criteria"]),
            height=160
        )

        if st.button("✅ Сақтау / Сохранить"):
            teams = [x.strip() for x in teams_text.splitlines() if x.strip()]
            criteria = [x.strip() for x in criteria_text.splitlines() if x.strip()]

            if len(teams) != 7:
                st.error("7 команда болуы керек / Должно быть 7 команд")
                st.stop()
            if len(criteria) != 5:
                st.error("5 критерий болуы керек / Должно быть 5 критериев")
                st.stop()

            # preserve where possible
            new_scores = {t: {c: 0 for c in criteria} for t in teams}
            for t in teams:
                for c in criteria:
                    if t in state["scores"] and c in state["scores"][t]:
                        new_scores[t][c] = int(state["scores"][t][c])

            state["teams"] = teams
            state["criteria"] = criteria
            state["scores"] = new_scores
            save_state(state)
            st.success("Сақталды / Сохранено")
            st.rerun()

    st.markdown("---")
    st.markdown(bi("Бағаларды енгізу (0–2)", "Ввод баллов (0–2)"), unsafe_allow_html=True)

    teams = state["teams"]
    criteria = state["criteria"]

    # Score input grid: team rows
    for t in teams:
        with st.container(border=True):
            cols = st.columns([2] + [1]*len(criteria))
            cols[0].markdown(f"### {t}")

            for i, c in enumerate(criteria):
                input_key = f"{t}__{c}"
                default_val = int(state["scores"][t].get(c, 0))
                val = cols[i+1].number_input(
                    c,
                    min_value=0,
                    max_value=MAX_PER_CRITERION,
                    step=1,
                    value=default_val,
                    key=input_key
                )
                state["scores"][t][c] = int(val)

    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("💾 Сақтау / Save"):
        save_state(state)
        st.success("Сақталды / Saved")
        st.rerun()

    if c2.button("↩ 0-ге қайтару / Reset to 0"):
        state = default_state()
        save_state(state)
        st.success("Қайтарылды / Reset done")
        st.rerun()

    st.markdown("---")
    st.markdown(bi("Алдын ала қарау (экрандағы көрініс)", "Предпросмотр (как на экране)"), unsafe_allow_html=True)
    df = compute_table(state)
    st.dataframe(df, use_container_width=True)

else:
    bi_h1("Нәтижелер (тікелей)", "Результаты (live)")
    bi_caption(
        f"Соңғы жаңарту: {state.get('updated_at')}",
        f"Последнее обновление: {state.get('updated_at')}"
    )

    df = compute_table(state)
    criteria = state["criteria"]

    # 1) Criterion averages across teams
    st.markdown("---")
    st.markdown(bi(
        "Критерийлер бойынша орташа балл (барлық командалар)",
        "Средний балл по критериям (по всем командам)"
    ), unsafe_allow_html=True)

    av = criterion_averages(df, criteria)
    av_chart = av.set_index("Criterion")[["Average"]]
    st.bar_chart(av_chart)

    # 2) Radar plots side by side
    st.markdown("---")
    st.markdown(bi(
        "Командалардың профилі (радар диаграмма, шкала 0–2)",
        "Профиль команд (радар-диаграмма, шкала 0–2)"
    ), unsafe_allow_html=True)

    teams = list(df["Team"].values)
    # show 3 per row
    per_row = 3
    for start in range(0, len(teams), per_row):
        cols = st.columns(per_row)
        for j in range(per_row):
            idx = start + j
            if idx >= len(teams):
                break
            team = teams[idx]
            vals = [int(df.loc[df["Team"] == team, c].values[0]) for c in criteria]
            fig = plot_radar_for_team(team, vals, criteria, max_val=MAX_PER_CRITERION)
            cols[j].pyplot(fig, clear_figure=True)

    # 3) Total points descending
    st.markdown("---")
    st.markdown(bi(
        "Жалпы ұпай (кему ретімен)",
        "Общий балл (по убыванию)"
    ), unsafe_allow_html=True)

    st.dataframe(df[["Team", "Total"]], use_container_width=True, height=320)
    st.bar_chart(df.set_index("Team")["Total"])

    # 4) Top-3 winners + congratulations
    st.markdown("---")
    st.markdown(bi(
        "Жеңімпаздар 🏆",
        "Победители 🏆"
    ), unsafe_allow_html=True)

    top3 = df.head(3)
    if len(top3) >= 1:
        st.success(f"🥇 1-орын / 1 место: **{top3.iloc[0]['Team']}** — Құттықтаймыз! / Поздравляем!")
    if len(top3) >= 2:
        st.info(f"🥈 2-орын / 2 место: **{top3.iloc[1]['Team']}** — Құттықтаймыз! / Поздравляем!")
    if len(top3) >= 3:
        st.warning(f"🥉 3-орын / 3 место: **{top3.iloc[2]['Team']}** — Құттықтаймыз! / Поздравляем!")

    st.caption("Экранда тек нәтиже көрсетіледі • На экране только результаты")
