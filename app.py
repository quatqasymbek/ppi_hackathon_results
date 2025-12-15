import json
import os
from datetime import datetime
from io import BytesIO
from math import pi
import textwrap

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt

st.set_page_config(page_title="Hackathon Results", layout="wide")

# ---------------- CONFIG ----------------
DEFAULT_TEAMS = [f"Team {i}" for i in range(1, 8)]
DEFAULT_CRITERIA = [f"Criterion {i}" for i in range(1, 6)]
MAX_PER_CRITERION = 2
DATA_FILE = "scores.json"

PIN = st.secrets.get("ADMIN_PIN", None)
PIN_REQUIRED = PIN is not None


# ---------------- SAFE HTML RENDER ----------------
def render_html(html: str):
    # remove indentation that causes markdown code blocks
    html = textwrap.dedent(html).strip()
    st.markdown(html, unsafe_allow_html=True)


# ---------------- GLOBAL STYLE ----------------
render_html("""
<style>
.block-container { padding-top: 2.4rem; padding-bottom: 2.2rem; max-width: 1400px; }
.small-muted { color: #8a8a8a; font-size: 0.92rem; }
.hr { height: 1px; background: rgba(255,255,255,0.10); border: none; margin: 1.2rem 0; }

/* Podium */
.podium { display: grid; grid-template-columns: 1fr 1.18fr 1fr; gap: 14px; margin-top: 12px; }
.pcard { border: 1px solid rgba(255,255,255,0.10); border-radius: 18px; padding: 14px 16px; background: rgba(255,255,255,0.03); }
.pcard.center { transform: translateY(-8px); box-shadow: 0 14px 30px rgba(0,0,0,0.20); background: rgba(255,255,255,0.04); }
.pcard .place { font-size: 0.95rem; color: #9aa0a6; margin-bottom: 6px; }
.pcard .team { font-size: 1.35rem; font-weight: 900; line-height: 1.1; }
.pcard .score { margin-top: 8px; font-size: 0.96rem; color: #9aa0a6; }
.pcard .emoji { font-size: 1.2rem; margin-right: 8px; }

/* Leaderboard list */
.lb { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.lbrow { display: grid; grid-template-columns: 64px 1fr 110px; align-items: center; gap: 12px; border: 1px solid rgba(255,255,255,0.10); border-radius: 16px; padding: 12px 14px; background: rgba(255,255,255,0.03); }
.lbrow .rank { font-weight: 950; font-size: 1.1rem; opacity: 0.95; }
.lbrow .team { font-weight: 850; font-size: 1.05rem; line-height: 1.15; }
.lbrow .score { text-align: right; font-weight: 950; font-size: 1.15rem; }
.lbrow.top1 { background: rgba(34,197,94,0.12); }
.lbrow.top2 { background: rgba(59,130,246,0.12); }
.lbrow.top3 { background: rgba(245,158,11,0.12); }
.badchip { display:inline-block; padding: 2px 10px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.04); font-size: 0.85rem; color: #9aa0a6; margin-left: 10px; }

canvas { border-radius: 14px; }
</style>
""")


# ---------------- BILINGUAL HELPERS ----------------
def bi_h1(kk: str, ru: str):
    render_html(f"""
<div style="line-height:1.1">
  <div style="font-size:2.1rem;font-weight:950;margin:0">{kk}</div>
  <div class="small-muted">{ru}</div>
</div>
""")

def bi_h2(kk: str, ru: str):
    render_html(f"""
<div style="line-height:1.15;margin-top:0.2rem">
  <div style="font-size:1.25rem;font-weight:900;margin:0">{kk}</div>
  <div class="small-muted">{ru}</div>
</div>
""")

def caption_bi(kk: str, ru: str):
    render_html(f"<div class='small-muted'>{kk} • {ru}</div>")


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

    # tie-break: Total desc -> last criterion desc -> Team name
    if len(criteria) >= 1 and criteria[-1] in df.columns:
        df = df.sort_values(["Total", criteria[-1], "Team"], ascending=[False, False, True])
    else:
        df = df.sort_values(["Total", "Team"], ascending=[False, True])

    df.reset_index(drop=True, inplace=True)
    return df

def criterion_averages(df: pd.DataFrame, criteria: list[str]) -> pd.DataFrame:
    out = pd.DataFrame({"Criterion": criteria, "Average": [float(df[c].mean()) for c in criteria]})
    return out.sort_values("Average", ascending=False).reset_index(drop=True)


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

    ax.plot(angles, avg, linewidth=2, linestyle="dashed", alpha=0.9, label="Орташа / Среднее")
    ax.fill(angles, avg, alpha=0.06)

    ax.plot(angles, team, linewidth=2.2, alpha=0.95, label="Команда / Команда")
    ax.fill(angles, team, alpha=0.12)

    ax.set_title(team_name, fontsize=12, fontweight="bold", pad=26)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=2, frameon=False, fontsize=9)
    fig.tight_layout()
    return fig


# ---------------- EXPORT ----------------
def to_excel_bytes(df_full: pd.DataFrame, updated_at: str) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_full.to_excel(writer, index=False, sheet_name="Results")
        pd.DataFrame({"updated_at": [updated_at]}).to_excel(writer, index=False, sheet_name="Meta")
    buf.seek(0)
    return buf.getvalue()


# ---------------- APP ----------------
state = load_state()

# Sidebar labels (as requested)
st.sidebar.markdown("### Режим / Режим")
mode = st.sidebar.radio(" ", ["Әділқазы / Жюри", "Экран / Экран"], index=0)

# ---------------- ADMIN ----------------
if mode.startswith("Әділқазы"):
    if PIN_REQUIRED:
        entered = st.sidebar.text_input("PIN (Әділқазы / Жюри)", type="password")
        if entered != PIN:
            st.warning("PIN енгізіңіз / Введите PIN")
            st.stop()

    bi_h1("Әділқазы панелі", "Панель жюри")
    caption_bi(f"Жаңартылды: {state.get('updated_at')}", f"Обновлено: {state.get('updated_at')}")
    render_html("<hr class='hr'>")

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

    render_html("<hr class='hr'>")
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
                    c, min_value=0, max_value=MAX_PER_CRITERION, step=1, value=default_val, key=input_key
                )
                state["scores"][t][c] = int(val)

    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("💾 Сақтау / Save"):
        save_state(state)
        st.success("Сақталды / Saved")
        st.rerun()

    if c2.button("👀 Экранды ашу / Open screen"):
        st.info("Сол жақтан Экран / Экран таңдаңыз • Выберите Экран / Экран слева")

# ---------------- PUBLIC / SCREEN ----------------
else:
    bi_h1("Хакатон нәтижелері", "Результаты хакатона")
    caption_bi(
        f"Соңғы жаңарту: {state.get('updated_at')}",
        f"Последнее обновление: {state.get('updated_at')}",
    )

    df = compute_table(state)
    criteria = state["criteria"]
    updated_at = state.get("updated_at") or ""

    # PODIUM (no cups in titles)
    render_html("<hr class='hr'>")
    bi_h2("Жеңімпаздар", "Победители")

    top3 = df.head(3)
    first = top3.iloc[0] if len(top3) > 0 else None
    second = top3.iloc[1] if len(top3) > 1 else None
    third = top3.iloc[2] if len(top3) > 2 else None

    podium_html = "<div class='podium'>"
    podium_html += (
        f"<div class='pcard'><div class='place'><span class='emoji'>🥈</span>2-орын / 2 место</div>"
        f"<div class='team'>{second['Team']}</div><div class='score'>Ұпай / Балл: <b>{int(second['Total'])}</b></div></div>"
        if second is not None
        else "<div class='pcard'><div class='place'>🥈 2-орын / 2 место</div><div class='team'>—</div></div>"
    )
    podium_html += (
        f"<div class='pcard center'><div class='place'><span class='emoji'>🥇</span>1-орын / 1 место</div>"
        f"<div class='team'>{first['Team']}</div><div class='score'>Ұпай / Балл: <b>{int(first['Total'])}</b> • Құттықтаймыз! / Поздравляем!</div></div>"
        if first is not None
        else "<div class='pcard center'><div class='place'>🥇 1-орын / 1 место</div><div class='team'>—</div></div>"
    )
    podium_html += (
        f"<div class='pcard'><div class='place'><span class='emoji'>🥉</span>3-орын / 3 место</div>"
        f"<div class='team'>{third['Team']}</div><div class='score'>Ұпай / Балл: <b>{int(third['Total'])}</b></div></div>"
        if third is not None
        else "<div class='pcard'><div class='place'>🥉 3-орын / 3 место</div><div class='team'>—</div></div>"
    )
    podium_html += "</div>"
    render_html(podium_html)

    # CRITERIA AVERAGES
    render_html("<hr class='hr'>")
    bi_h2(
        "Критерийлер бойынша орташа балл (барлық командалар)",
        "Средний балл по критериям (по всем командам)",
    )

    av = criterion_averages(df, criteria).copy()
    av["Average"] = av["Average"].round(2)

    chart = (
        alt.Chart(av)
        .mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10)
        .encode(
            x=alt.X("Criterion:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30)),
            y=alt.Y("Average:Q", title="Орташа / Среднее", scale=alt.Scale(domain=[0, MAX_PER_CRITERION])),
            color=alt.Color(
                "Average:Q",
                scale=alt.Scale(domain=[0, MAX_PER_CRITERION], range=["#F59E0B", "#22C55E"]),
                legend=None,
            ),
            tooltip=[alt.Tooltip("Criterion:N", title="Критерий"), alt.Tooltip("Average:Q", title="Орташа / Среднее")],
        )
        .properties(height=290)
    )
    st.altair_chart(chart, use_container_width=True)

    # RADAR
    render_html("<hr class='hr'>")
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

    # LEADERBOARD
    render_html("<hr class='hr'>")
    bi_h2("Жалпы ұпай (кему ретімен)", "Общий балл (по убыванию)")

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    rows_html = "<div class='lb'>"
    for i, row in df.reset_index(drop=True).iterrows():
        rank = i + 1
        team = row["Team"]
        total = int(row["Total"])
        badge = f"{rank}-орын / {rank} место"
        left = medals.get(rank, f"#{rank}")
        cls = "lbrow"
        if rank == 1: cls += " top1"
        elif rank == 2: cls += " top2"
        elif rank == 3: cls += " top3"
        rows_html += f"<div class='{cls}'><div class='rank'>{left}</div><div class='team'>{team}<span class='badchip'>{badge}</span></div><div class='score'>{total}</div></div>"
    rows_html += "</div>"
    render_html(rows_html)

    # DOWNLOAD EXCEL
    excel_bytes = to_excel_bytes(df.copy(), updated_at)
    filename = f"hackathon_results_{updated_at.replace(':','-').replace(' ','_') or 'export'}.xlsx"
    st.download_button(
        label="⬇️ Нәтижені Excel ретінде жүктеу / Скачать результаты в Excel",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
