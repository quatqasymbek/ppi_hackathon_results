import json
import os
from datetime import datetime
from io import BytesIO
from math import pi

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt

st.set_page_config(page_title="Hackathon Scores", layout="wide")

# ---------------- CONFIG ----------------
DEFAULT_TEAMS = [f"Team {i}" for i in range(1, 8)]
DEFAULT_CRITERIA = [f"Criterion {i}" for i in range(1, 6)]
MAX_PER_CRITERION = 2
DATA_FILE = "scores.json"

PIN = st.secrets.get("ADMIN_PIN", None)
PIN_REQUIRED = PIN is not None


# ---------------- STYLE ----------------
st.markdown(
    """
<style>
.block-container { padding-top: 1.0rem; padding-bottom: 2.0rem; max-width: 1200px; }
h1, h2, h3 { margin-bottom: 0.35rem; }
.small-muted { color: #8a8a8a; font-size: 0.9rem; }
.hr { height: 1px; background: rgba(255,255,255,0.08); border: none; margin: 1rem 0; }

.card {
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.03);
}
.card-title { font-size: 0.95rem; color: #9aa0a6; margin-bottom: 4px; }
.card-value { font-size: 1.35rem; font-weight: 800; line-height: 1.1; }
.card-sub { margin-top: 6px; color: #9aa0a6; font-size: 0.95rem; }

/* Podium */
.podium {
  display: grid;
  grid-template-columns: 1fr 1.15fr 1fr;
  gap: 14px;
  margin-top: 10px;
  margin-bottom: 10px;
}
.pcard {
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.03);
}
.pcard .place { font-size: 0.95rem; color: #9aa0a6; margin-bottom: 6px; }
.pcard .team { font-size: 1.35rem; font-weight: 900; line-height: 1.1; }
.pcard .score { margin-top: 8px; font-size: 0.95rem; color: #9aa0a6; }
.pcard.center { transform: translateY(-10px); box-shadow: 0 10px 26px rgba(0,0,0,0.22); }
.pcard .emoji { font-size: 1.2rem; margin-right: 6px; }

/* Scoreboard table styling */
.dataframe-container { border-radius: 14px; overflow: hidden; border: 1px solid rgba(255,255,255,0.08); }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- BILINGUAL HELPERS ----------------
def bi_h1(kk: str, ru: str):
    st.markdown(
        f"<div style='line-height:1.1'>"
        f"<div style='font-size:2.05rem;font-weight:900'>{kk}</div>"
        f"<div class='small-muted'>{ru}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

def bi_h2(kk: str, ru: str):
    st.markdown(
        f"<div style='line-height:1.15;margin-top:0.3rem'>"
        f"<div style='font-size:1.25rem;font-weight:800'>{kk}</div>"
        f"<div class='small-muted'>{ru}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

def caption_bi(kk: str, ru: str):
    st.markdown(f"<div class='small-muted'>{kk} • {ru}</div>", unsafe_allow_html=True)

def card(title_kk: str, title_ru: str, value: str, sub: str = ""):
    st.markdown(
        f"<div class='card'>"
        f"<div class='card-title'>{title_kk} / {title_ru}</div>"
        f"<div class='card-value'>{value}</div>"
        f"{f"<div class='card-sub'>{sub}</div>" if sub else ""}"
        f"</div>",
        unsafe_allow_html=True,
    )

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
        s = default_state()
        save_state(s)
        return s
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        s = default_state()
        save_state(s)
        return s

def save_state(state: dict):
    state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

# ---------------- COMPUTE ----------------
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

    # Tie-break: Total desc -> last criterion desc -> Team name
    if len(criteria) >= 1 and criteria[-1] in df.columns:
        df = df.sort_values(["Total", criteria[-1], "Team"], ascending=[False, False, True])
    else:
        df = df.sort_values(["Total", "Team"], ascending=[False, True])

    df.reset_index(drop=True, inplace=True)
    return df

def criterion_averages(df: pd.DataFrame, criteria: list[str]) -> pd.DataFrame:
    out = pd.DataFrame(
        {"Criterion": criteria, "Average": [float(df[c].mean()) for c in criteria]}
    )
    return out.sort_values("Average", ascending=False).reset_index(drop=True)

def make_scoreboard(df: pd.DataFrame) -> pd.DataFrame:
    # Clean scoreboard: #, 🏅, Team, Total
    d = df[["Team", "Total"]].copy()
    d.insert(0, "#", range(1, len(d) + 1))
    medals = ["🥇", "🥈", "🥉"] + [""] * max(0, len(d) - 3)
    d.insert(1, "🏅", medals)
    return d

def style_scoreboard(d: pd.DataFrame) -> "pd.io.formats.style.Styler":
    def row_style(row):
        r = row["#"]
        if r == 1:
            return ["font-weight: 800;"] * len(row)
        if r == 2:
            return ["font-weight: 700;"] * len(row)
        if r == 3:
            return ["font-weight: 700;"] * len(row)
        return [""] * len(row)

    sty = d.style.apply(row_style, axis=1)

    # Soft highlight top 3
    def highlight_top3(row):
        r = row["#"]
        if r == 1:
            return ["background-color: rgba(34,197,94,0.10);"] * len(row)
        if r == 2:
            return ["background-color: rgba(59,130,246,0.10);"] * len(row)
        if r == 3:
            return ["background-color: rgba(245,158,11,0.10);"] * len(row)
        return [""] * len(row)

    sty = sty.apply(highlight_top3, axis=1)

    # Column formatting
    sty = sty.format({"Total": "{:.0f}"})
    return sty

# ---------------- RADAR ----------------
def plot_radar_team_vs_avg(team_name, team_vals, avg_vals, criteria, max_val=2):
    n = len(criteria)

    angles = [i / float(n) * 2 * pi for i in range(n)]
    angles += angles[:1]

    team = list(team_vals) + [team_vals[0]]
    avg = list(avg_vals) + [avg_vals[0]]

    fig, ax = plt.subplots(figsize=(3.6, 3.6), subplot_kw=dict(polar=True))

    ax.set_theta_offset(pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(criteria, fontsize=9)

    ax.set_ylim(0, max_val)
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["0", "1", "2"], fontsize=8)

    ax.grid(alpha=0.25)
    ax.spines["polar"].set_alpha(0.25)

    # Avg (dashed)
    ax.plot(angles, avg, linewidth=2, linestyle="dashed", alpha=0.9, label="Орташа / Среднее")
    ax.fill(angles, avg, alpha=0.06)

    # Team
    ax.plot(angles, team, linewidth=2.2, alpha=0.95, label="Команда / Команда")
    ax.fill(angles, team, alpha=0.12)

    ax.set_title(team_name, fontsize=12, fontweight="bold", pad=26)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.10),
        ncol=2,
        frameon=False,
        fontsize=9,
        title="0 — min • 2 — max",
        title_fontsize=9,
    )

    fig.tight_layout()
    return fig

# ---------------- EXPORT ----------------
def to_excel_bytes(df_full: pd.DataFrame, df_scoreboard: pd.DataFrame, updated_at: str) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_scoreboard.to_excel(writer, index=False, sheet_name="Scoreboard")
        df_full.to_excel(writer, index=False, sheet_name="Full Scores")
        meta = pd.DataFrame({"updated_at": [updated_at]})
        meta.to_excel(writer, index=False, sheet_name="Meta")
    buf.seek(0)
    return buf.getvalue()

# ---------------- APP ----------------
state = load_state()

st.sidebar.markdown("### Mode / Режим")
mode = st.sidebar.radio(
    " ",
    ["Admin (Jury) / Әділқазы", "Public Screen / Экран"],
    index=0,
)

# ---------------- ADMIN ----------------
if mode.startswith("Admin"):
    if PIN_REQUIRED:
        entered = st.sidebar.text_input("Admin PIN", type="password")
        if entered != PIN:
            st.warning("PIN енгізіңіз / Введите PIN")
            st.stop()

    bi_h1("Әділқазы панелі", "Панель жюри")
    caption_bi(f"Жаңартылды: {state.get('updated_at')}", f"Обновлено: {state.get('updated_at')}")

    st.markdown("<hr class='hr'>", unsafe_allow_html=True)

    bi_h2("Атауларды баптау", "Настройка названий")
    with st.expander("✏️ Командалар және критерийлер / Команды и критерии"):
        teams_text = st.text_area(
            "Командалар (әр жолға бір команда) / Команды (по одной в строке)",
            "\n".join(state["teams"]),
            height=160,
        )
        criteria_text = st.text_area(
            "Критерийлер (әр жолға бір критерий) / Критерии (по одному в строке)",
            "\n".join(state["criteria"]),
            height=160,
        )

        cA, cB = st.columns([1, 2])
        if cA.button("✅ Сақтау / Сохранить"):
            teams = [x.strip() for x in teams_text.splitlines() if x.strip()]
            criteria = [x.strip() for x in criteria_text.splitlines() if x.strip()]

            if len(teams) != 7:
                st.error("7 команда болуы керек / Должно быть 7 команд")
                st.stop()
            if len(criteria) != 5:
                st.error("5 критерий болуы керек / Должно быть 5 критериев")
                st.stop()

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

        if cB.button("↩ Барлығын 0-ге қайтару / Reset all to 0"):
            state = default_state()
            save_state(state)
            st.success("Қайтарылды / Reset done")
            st.rerun()

    st.markdown("<hr class='hr'>", unsafe_allow_html=True)
    bi_h2("Бағаларды енгізу (0–2)", "Ввод баллов (0–2)")

    teams = state["teams"]
    criteria = state["criteria"]

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

    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("💾 Сақтау / Save"):
        save_state(state)
        st.success("Сақталды / Saved")
        st.rerun()

    if c2.button("👀 Экранды ашу / Open public screen"):
        st.info("Сол жақтан Public Screen / Экран таңдаңыз • Выберите Public Screen / Экран слева")

    st.markdown("<hr class='hr'>", unsafe_allow_html=True)
    bi_h2("Алдын ала қарау", "Предпросмотр")
    df_admin = compute_table(state)
    st.dataframe(df_admin, use_container_width=True)

# ---------------- PUBLIC SCREEN ----------------
else:
    bi_h1("Хакатон нәтижелері", "Результаты хакатона")
    caption_bi(
        f"Соңғы жаңарту: {state.get('updated_at')}",
        f"Последнее обновление: {state.get('updated_at')}",
    )

    df = compute_table(state)
    criteria = state["criteria"]
    updated_at = state.get("updated_at") or ""

    # --- Podium (Top-3) ---
    st.markdown("<hr class='hr'>", unsafe_allow_html=True)
    bi_h2("Жеңімпаздар 🏆", "Победители 🏆")

    top3 = df.head(3)

    def _safe(i):
        return top3.iloc[i] if len(top3) > i else None

    first, second, third = _safe(0), _safe(1), _safe(2)

    podium_html = "<div class='podium'>"

    # 2nd
    if second is not None:
        podium_html += f"""
        <div class='pcard'>
          <div class='place'><span class='emoji'>🥈</span>2-орын / 2 место</div>
          <div class='team'>{second['Team']}</div>
          <div class='score'>Ұпай / Балл: <b>{int(second['Total'])}</b></div>
        </div>
        """
    else:
        podium_html += "<div class='pcard'><div class='place'>🥈 2-орын / 2 место</div><div class='team'>—</div></div>"

    # 1st
    if first is not None:
        podium_html += f"""
        <div class='pcard center'>
          <div class='place'><span class='emoji'>🥇</span>1-орын / 1 место</div>
          <div class='team'>{first['Team']}</div>
          <div class='score'>Ұпай / Балл: <b>{int(first['Total'])}</b> • Құттықтаймыз! / Поздравляем!</div>
        </div>
        """
    else:
        podium_html += "<div class='pcard center'><div class='place'>🥇 1-орын / 1 место</div><div class='team'>—</div></div>"

    # 3rd
    if third is not None:
        podium_html += f"""
        <div class='pcard'>
          <div class='place'><span class='emoji'>🥉</span>3-орын / 3 место</div>
          <div class='team'>{third['Team']}</div>
          <div class='score'>Ұпай / Балл: <b>{int(third['Total'])}</b></div>
        </div>
        """
    else:
        podium_html += "<div class='pcard'><div class='place'>🥉 3-орын / 3 место</div><div class='team'>—</div></div>"

    podium_html += "</div>"
    st.markdown(podium_html, unsafe_allow_html=True)

    # --- Criterion averages chart (gradient) ---
    st.markdown("<hr class='hr'>", unsafe_allow_html=True)
    bi_h2(
        "Критерийлер бойынша орташа балл (барлық командалар)",
        "Средний балл по критериям (по всем командам)",
    )

    av = criterion_averages(df, criteria).copy()
    av["Average"] = av["Average"].round(2)

    chart = (
        alt.Chart(av)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
        .encode(
            x=alt.X("Criterion:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30)),
            y=alt.Y(
                "Average:Q",
                title="Орташа / Среднее",
                scale=alt.Scale(domain=[0, MAX_PER_CRITERION]),
            ),
            color=alt.Color(
                "Average:Q",
                scale=alt.Scale(domain=[0, MAX_PER_CRITERION], range=["#F59E0B", "#22C55E"]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Criterion:N", title="Критерий"),
                alt.Tooltip("Average:Q", title="Орташа / Среднее"),
            ],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, use_container_width=True)

    # --- Radar plots ---
    st.markdown("<hr class='hr'>", unsafe_allow_html=True)
    bi_h2(
        "Командалардың профилі (радар диаграмма, шкала 0–2)",
        "Профиль команд (радар-диаграмма, шкала 0–2)",
    )

    avg_vals = [float(df[c].mean()) for c in criteria]
    teams_sorted = list(df["Team"].values)

    per_row = 3
    for start in range(0, len(teams_sorted), per_row):
        cols = st.columns(per_row)
        for j in range(per_row):
            idx = start + j
            if idx >= len(teams_sorted):
                break
            team = teams_sorted[idx]
            row = df.loc[df["Team"] == team].iloc[0]
            team_vals = [int(row[c]) for c in criteria]
            fig = plot_radar_team_vs_avg(team, team_vals, avg_vals, criteria, max_val=MAX_PER_CRITERION)
            cols[j].pyplot(fig, clear_figure=True)

    # --- Scoreboard (table only) + Excel download ---
    st.markdown("<hr class='hr'>", unsafe_allow_html=True)
    bi_h2("Жалпы ұпай (кему ретімен)", "Общий балл (по убыванию)")

    scoreboard = make_scoreboard(df)

    # Nice styled table
    styled = style_scoreboard(scoreboard)
    st.markdown("<div class='dataframe-container'>", unsafe_allow_html=True)
    st.dataframe(styled, use_container_width=True, height=360)
    st.markdown("</div>", unsafe_allow_html=True)

    # Excel export underneath
    full_scores = df.copy()
    excel_bytes = to_excel_bytes(full_scores, scoreboard, updated_at)
    filename = f"hackathon_results_{updated_at.replace(':','-').replace(' ','_') or 'export'}.xlsx"

    st.download_button(
        label="⬇️ Нәтижені Excel ретінде жүктеу / Скачать результаты в Excel",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.caption("Экранда тек нәтижелер көрсетіледі • На экране только результаты")
