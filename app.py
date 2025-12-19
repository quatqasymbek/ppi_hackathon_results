import json
import os
import random
import time
from datetime import datetime
from io import BytesIO
import textwrap

import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="Hackathon Results", layout="wide")

# ---------------- CONFIG ----------------
MAX_PER_CRITERION = 2
DATA_FILE = "scores.json"

PIN = st.secrets.get("ADMIN_PIN", None)
PIN_REQUIRED = PIN is not None

# Fixed directions (Бағыттар / Направления) and their own criteria lists
DIRECTIONS = [
    #"Естественно-научная грамотность",
    "Жаратылыстану ғылымдары сауаттылығы",
    "Математикалық сауаттылық",
    #"Межкультурная грамотность",
    "Мәдениетаралық сауаттылық",
    #"Финансовая грамотность",
    "Қаржылық сауаттылық",
    "Цифрлық сауаттылық",  
    # <-- (name was missing in your message)
    #"Читательская грамотность",
    "Оқу сауаттылығы",
    "Экологиялық сауаттылық",
]

CRITERIA_BY_DIRECTION = {
    "Жаратылыстану ғылымдары сауаттылығы": [
        "Суды сүзудің тиімділігі",
        "Сүзгінің жұмысын ғылыми тұрғыда түсіндіру",
        "Сүзгінің құрылымы және жинақталуы",
        "Нәтижені талдау және қорытынды",
        "Презентация және командалық жұмыс",
    ],
    "Математикалық сауаттылық": [
        "Жалпы ауданды табу",
        "Камераның бақылауына кірмейтін ауданның пайызын есептеу",
        "Камераның бақылауына кіретін аудандарды салыстыру",
        "Камералардың максималды санын есептеу",
        "Камералардың минималды санын есептеу",
    ],
    "Мәдениетаралық сауаттылық": [
        "Дұрыс және проблемалы хабарламаларды анықтау",
        "Мәдениетаралық тәуекелдерді талдау",
        "Мәдениетаралық сауаттылық қағидаттарын түсіну",
        "Оқушыларға арналған практикалық ұсынымдар",
        "Фестивальге арналған мини-нұсқаулық",
    ],
     "Қаржылық сауаттылық": [
        "Бюджетті жоспарлау және негіздеу",
        "Ресурстарды ұтымды бөлу",
        "Қаржылық тәуекелдерді бағалау",
        "Командалық жұмыс және қорғау мәдениеті",
        "Мектеп үшін білім беру әсері",
    ],
    "Цифрлық сауаттылық": [
        "Легитимді хатты анықтау",
        "Цифрлық тәуекелдерді талдау және аргументация",
        "Цифрлық қауіпсіздік қағидаттарын түсіну",
        "Күмәнді хат алған жағдайда әрекет ету алгоритмі",
        "Мектептің киберқауіпсіздігін қамтамасыз ету бойынша ұсыныстар",
    ],
    "Оқу сауаттылығы": [
        "Мәтінді түсіну және пайдалану",
        "Шешімнің дәлелділігі мен логикасы",
        "Ұсынылған қадамдардың іске асырылу мүмкіндігі",
        "Тапсырманың толық орындалуы",
        "Топтық жұмыстың үйлесімділігі және рәсімделуі",
    ],
    "Экологиялық сауаттылық": [
        "Шешімнің негізделуі",
        "Этикалық жетілу",
        "Ымыраның креативтілігі",
        "Коммуникация тиімділігі",
        "Педагогикалық әлеует",
    ],
}


# ---------------- SAFE HTML RENDER ----------------
def render_html(html: str):
    html = textwrap.dedent(html).strip()
    st.markdown(html, unsafe_allow_html=True)


# ---------------- GLOBAL STYLE ----------------
render_html("""
<style>
.block-container { padding-top: 2.4rem; padding-bottom: 2.2rem; max-width: 1400px; }
.small-muted { color: #8a8a8a; font-size: 0.92rem; }
.hr { height: 1px; background: rgba(255,255,255,0.10); border: none; margin: 1.2rem 0; }

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
    scores = {}
    for d in DIRECTIONS:
        scores[d] = {c: 0 for c in CRITERIA_BY_DIRECTION[d]}
    return {
        "directions": DIRECTIONS,
        "criteria_by_direction": CRITERIA_BY_DIRECTION,
        "scores": scores,
        "presentation_order": list(DIRECTIONS),
        "updated_at": None,
    }

def save_state(state: dict):
    state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def load_state():
    if not os.path.exists(DATA_FILE):
        s = default_state()
        save_state(s)
        return s

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            s = json.load(f)
    except Exception:
        s = default_state()
        save_state(s)
        return s

    # If old format or mismatched structure -> reset to fixed config
    if "directions" not in s or "criteria_by_direction" not in s or "scores" not in s:
        s = default_state()
        save_state(s)
        return s

    # Force fixed config (in case someone edited the JSON)
    s["directions"] = list(DIRECTIONS)
    s["criteria_by_direction"] = CRITERIA_BY_DIRECTION

    # Ensure scores contain all directions + criteria
    if "scores" not in s or not isinstance(s["scores"], dict):
        s["scores"] = {}

    for d in DIRECTIONS:
        if d not in s["scores"] or not isinstance(s["scores"][d], dict):
            s["scores"][d] = {}
        for c in CRITERIA_BY_DIRECTION[d]:
            s["scores"][d][c] = int(s["scores"][d].get(c, 0))

        # Remove any extra criteria keys
        for extra in list(s["scores"][d].keys()):
            if extra not in CRITERIA_BY_DIRECTION[d]:
                del s["scores"][d][extra]

    # Presentation order
    if "presentation_order" not in s or not isinstance(s["presentation_order"], list):
        s["presentation_order"] = list(DIRECTIONS)
    else:
        # Keep only valid directions, append missing ones
        s["presentation_order"] = [x for x in s["presentation_order"] if x in DIRECTIONS]
        for d in DIRECTIONS:
            if d not in s["presentation_order"]:
                s["presentation_order"].append(d)

    return s


# ---------------- COMPUTE ----------------
def totals_df(state: dict) -> pd.DataFrame:
    rows = []
    for d in state["directions"]:
        total = sum(int(state["scores"][d].get(c, 0)) for c in state["criteria_by_direction"][d])
        rows.append({"Бағыт / Направление": d, "Total": total})
    df = pd.DataFrame(rows).sort_values(["Total", "Бағыт / Направление"], ascending=[False, True]).reset_index(drop=True)
    return df

def details_long_df(state: dict) -> pd.DataFrame:
    rows = []
    for d in state["directions"]:
        for i, c in enumerate(state["criteria_by_direction"][d], start=1):
            rows.append({
                "Бағыт / Направление": d,
                "№": i,
                "Criterion / Критерий": c,
                "Score": int(state["scores"][d].get(c, 0)),
            })
    return pd.DataFrame(rows)

def reset_scores_only(state: dict):
    for d in state["directions"]:
        for c in state["criteria_by_direction"][d]:
            state["scores"][d][c] = 0

def to_excel_bytes(df_totals: pd.DataFrame, df_details: pd.DataFrame, updated_at: str) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_totals.to_excel(writer, index=False, sheet_name="Totals")
        df_details.to_excel(writer, index=False, sheet_name="Details")
        pd.DataFrame({"updated_at": [updated_at]}).to_excel(writer, index=False, sheet_name="Meta")
    buf.seek(0)
    return buf.getvalue()


# ---------------- AUTH ----------------
def require_pin_if_needed():
    if not PIN_REQUIRED:
        return
    entered = st.sidebar.text_input("PIN (Әділқазы / Жюри)", type="password", key="pin_input")
    if entered != PIN:
        st.warning("PIN енгізіңіз / Введите PIN")
        st.stop()


# ---------------- APP ----------------
state = load_state()

st.sidebar.markdown("### Режим / Режим")
mode = st.sidebar.radio(
    " ",
    ["Баптау / Настройки", "Әділқазы / Жюри", "Экран / Экран"],
    index=0,
    key="mode_radio",
)

# ---------------- SETTINGS ----------------
if mode.startswith("Баптау"):
    require_pin_if_needed()

    bi_h1("Баптау", "Настройки")
    caption_bi(f"Жаңартылды: {state.get('updated_at')}", f"Обновлено: {state.get('updated_at')}")
    render_html("<hr class='hr'>")

    bi_h2("Көрсету реті (рандомайзер)", "Порядок выступления (рандомайзер)")

    # show current order
    def order_html(order_list: list[str]) -> str:
        s = "<div class='lb'>"
        for i, name in enumerate(order_list, start=1):
            s += f"<div class='lbrow'><div class='rank'>#{i}</div><div class='team'>{name}</div><div class='score'> </div></div>"
        s += "</div>"
        return s

    render_html(order_html(state["presentation_order"]))

    c1, c2, c3 = st.columns([1, 1, 2])
    placeholder = st.empty()

    if c1.button("🎲 Араластыру / Перемешать", key="shuffle_btn"):
        order = list(state["presentation_order"])
        # small visual shuffle animation
        for _ in range(10):
            random.shuffle(order)
            with placeholder:
                render_html(order_html(order))
            time.sleep(0.10)

        state["presentation_order"] = order
        save_state(state)
        st.success("Жаңа реттілік сақталды / Новый порядок сохранён")
        st.rerun()

    if c2.button("↩ Қалпына келтіру / Сброс", key="reset_order_btn"):
        state["presentation_order"] = list(DIRECTIONS)
        save_state(state)
        st.success("Әдепкі реттілік / Порядок по умолчанию")
        st.rerun()

    render_html("<hr class='hr'>")
    bi_h2("Бағыттар мен критерийлер (бекітілген)", "Направления и критерии (фиксированные)")
    with st.expander("👀 Көру / Смотреть"):
        for d in DIRECTIONS:
            st.markdown(f"**{d}**")
            for i, c in enumerate(CRITERIA_BY_DIRECTION[d], start=1):
                st.write(f"{i}. {c}")
            st.write("")

# ---------------- JURY ----------------
elif mode.startswith("Әділқазы"):
    require_pin_if_needed()

    bi_h1("Әділқазы панелі", "Панель жюри")
    caption_bi(f"Жаңартылды: {state.get('updated_at')}", f"Обновлено: {state.get('updated_at')}")
    render_html("<hr class='hr'>")

    bi_h2("Бағаларды енгізу (0–2)", "Ввод баллов (0–2)")

    for d in state["directions"]:
        with st.container(border=True):
            st.markdown(f"### {d}")
            for c in state["criteria_by_direction"][d]:
                key = f"{d}__{c}"
                default_val = int(state["scores"][d].get(c, 0))
                v = st.number_input(
                    c,
                    min_value=0,
                    max_value=MAX_PER_CRITERION,
                    step=1,
                    value=default_val,
                    key=key,
                )
                state["scores"][d][c] = int(v)

    c1, c2, _ = st.columns([1, 1, 2])

    if c1.button("💾 Сақтау / Сохранить", key="save_scores_btn"):
        save_state(state)
        st.success("Сақталды / Сохранено")
        st.rerun()

    if c2.button("↩ Барлығын 0-ге қайтару / Сбросить всё в 0", key="reset_scores_btn"):
        reset_scores_only(state)
        save_state(state)
        st.success("Қайтарылды / Сброс выполнен")
        st.rerun()

# ---------------- SCREEN ----------------
else:
    bi_h1("Хакатон нәтижелері", "Результаты хакатона")
    caption_bi(
        f"Соңғы жаңарту: {state.get('updated_at')}",
        f"Последнее обновление: {state.get('updated_at')}",
    )

    updated_at = state.get("updated_at") or ""

    # Presentation order
    render_html("<hr class='hr'>")
    bi_h2("Көрсету реті (жеребе)", "Порядок выступления (жеребьёвка)")
    order = state.get("presentation_order") or list(DIRECTIONS)

    order_rows = "<div class='lb'>"
    for i, name in enumerate(order, start=1):
        order_rows += f"<div class='lbrow'><div class='rank'>#{i}</div><div class='team'>{name}</div><div class='score'></div></div>"
    order_rows += "</div>"
    render_html(order_rows)

    # Leaderboard
    render_html("<hr class='hr'>")
    bi_h2("Жалпы ұпай (кему ретімен)", "Общий балл (по убыванию)")
    df_tot = totals_df(state)

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    rows_html = "<div class='lb'>"
    for i, row in df_tot.reset_index(drop=True).iterrows():
        rank = i + 1
        name = row["Бағыт / Направление"]
        total = int(row["Total"])
        badge = f"{rank}-орын / {rank} место"
        left = medals.get(rank, f"#{rank}")
        cls = "lbrow"
        if rank == 1: cls += " top1"
        elif rank == 2: cls += " top2"
        elif rank == 3: cls += " top3"
        rows_html += (
            f"<div class='{cls}'>"
            f"<div class='rank'>{left}</div>"
            f"<div class='team'>{name}<span class='badchip'>{badge}</span></div>"
            f"<div class='score'>{total}</div>"
            f"</div>"
        )
    rows_html += "</div>"
    render_html(rows_html)

    # Per-direction criteria charts
    render_html("<hr class='hr'>")
    bi_h2("Әр бағыт бойынша критерий ұпайлары", "Баллы по критериям для каждого направления")

    per_row = 2
    for start in range(0, len(order), per_row):
        cols = st.columns(per_row)
        for j in range(per_row):
            idx = start + j
            if idx >= len(order):
                break
            d = order[idx]
            crits = state["criteria_by_direction"][d]
            scores = [int(state["scores"][d].get(c, 0)) for c in crits]
            df_one = pd.DataFrame({"Criterion": crits, "Score": scores})

            chart = (
                alt.Chart(df_one)
                .mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10)
                .encode(
                    x=alt.X("Criterion:N", sort=None, title=None, axis=alt.Axis(labelAngle=-25)),
                    y=alt.Y("Score:Q", title=None, scale=alt.Scale(domain=[0, MAX_PER_CRITERION])),
                    tooltip=[alt.Tooltip("Criterion:N", title="Критерий"), alt.Tooltip("Score:Q", title="Балл")],
                )
                .properties(height=260, title=d)
            )
            cols[j].altair_chart(chart, use_container_width=True)

    # Export
    df_details = details_long_df(state)
    excel_bytes = to_excel_bytes(df_tot.copy(), df_details.copy(), updated_at)
    filename = f"hackathon_results_{updated_at.replace(':','-').replace(' ','_') or 'export'}.xlsx"
    st.download_button(
        label="⬇️ Нәтижені Excel ретінде жүктеу / Скачать результаты в Excel",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="download_excel_btn",
    )
