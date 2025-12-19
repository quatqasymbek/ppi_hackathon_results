import json
import os
import random
import secrets
import time
import hashlib
from datetime import datetime
from io import BytesIO
import textwrap
from math import pi

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Hackathon Results", layout="wide")


# ---------------- CONFIG ----------------
MAX_PER_CRITERION = 2
DATA_FILE = "scores.json"

PIN = st.secrets.get("ADMIN_PIN", None)
PIN_REQUIRED = PIN is not None

LOGO_CANDIDATES = [
    "event_logo.png",
    "Логотип-рус.png",
    "ChatGPT Image 19 дек. 2025 г., 19_51_39.png",
    "/mnt/data/Логотип-рус.png",
    "/mnt/data/ChatGPT Image 19 дек. 2025 г., 19_51_39.png",
]

DIRECTIONS = [
    "Жаратылыстану-ғылыми сауаттылық",
    "Математикалық сауаттылық",
    "Мәдениетаралық сауаттылық",
    "Қаржылық сауаттылық",
    "Цифрлық сауаттылық",
    "Оқу сауаттылығы",
    "Экологиялық сауаттылық",
]
DIRECTION_RU = {
    "Жаратылыстану-ғылыми сауаттылық": "Естественно-научная грамотность",
    "Математикалық сауаттылық": "Математическая грамотность",
    "Мәдениетаралық сауаттылық": "Межкультурная грамотность",
    "Қаржылық сауаттылық": "Финансовая грамотность",
    "Цифрлық сауаттылық": "Цифровая грамотность",
    "Оқу сауаттылығы": "Читательская грамотность",
    "Экологиялық сауаттылық": "Экологическая грамотность",
}

CRITERIA_BI = {
    "Жаратылыстану-ғылыми сауаттылық": [
        {"kk": "Суды сүзудің тиімділігі", "ru": "Эффективность фильтрации воды"},
        {"kk": "Сүзгінің жұмысын ғылыми тұрғыда түсіндіру", "ru": "Научное объяснение работы фильтра"},
        {"kk": "Сүзгінің құрылымы және жинақталуы", "ru": "Конструкция и сборка фильтра"},
        {"kk": "Нәтижені талдау және қорытынды", "ru": "Анализ результата и выводы"},
        {"kk": "Презентация және командалық жұмыс", "ru": "Презентация и командная работа"},
    ],
    "Математикалық сауаттылық": [
        {"kk": "Жалпы ауданды табу", "ru": "Находит общую площадь"},
        {"kk": "Камераның бақылауына кірмейтін ауданның пайызын есептеу",
         "ru": "Вычисляет процент площади не попадающих под камеру"},
        {"kk": "Камераның бақылауына кіретін аудандарды салыстыру",
         "ru": "Сравнивает площади, попадающих под камеру"},
        {"kk": "Камералардың максималды санын есептеу",
         "ru": "Вычисляет максимальное количество камер"},
        {"kk": "Камералардың минималды санын есептеу",
         "ru": "Вычисляет минимальное количество камер"},
    ],
    "Мәдениетаралық сауаттылық": [
        {"kk": "Дұрыс және проблемалы хабарламаларды анықтау",
         "ru": "Определение корректного и проблемных сообщений"},
        {"kk": "Мәдениетаралық тәуекелдерді талдау",
         "ru": "Аргументация и анализ межкультурных рисков"},
        {"kk": "Мәдениетаралық сауаттылық қағидаттарын түсіну",
         "ru": "Понимание принципов межкультурной грамотности"},
        {"kk": "Оқушыларға арналған практикалық ұсынымдар",
         "ru": "Практические рекомендации обучающимся"},
        {"kk": "Фестивальге арналған мини-нұсқаулық",
         "ru": "Мини-инструкция (памятка) для фестиваля"},
    ],
    "Қаржылық сауаттылық": [
        {"kk": "Бюджетті жоспарлау және негіздеу", "ru": "Планирование и обоснование бюджета"},
        {"kk": "Ресурстарды ұтымды бөлу", "ru": "Логичное и рациональное распределение ресурсов"},
        {"kk": "Қаржылық тәуекелдерді бағалау", "ru": "Оценка финансовых рисков"},
        {"kk": "Командалық жұмыс және қорғау мәдениеті", "ru": "Командная работа и культура защиты"},
        {"kk": "Мектеп үшін білім беру әсері", "ru": "Образовательный эффект для школы"},
    ],
    "Цифрлық сауаттылық": [
        {"kk": "Легитимді хатты анықтау", "ru": "Определение легитимного письма"},
        {"kk": "Цифрлық тәуекелдерді талдау және аргументация",
         "ru": "Анализ и аргументация цифровых рисков"},
        {"kk": "Цифрлық қауіпсіздік қағидаттарын түсіну",
         "ru": "Понимание принципов цифровой безопасности"},
        {"kk": "Күмәнді хат алған жағдайда әрекет ету алгоритмі",
         "ru": "Алгоритм действий при подозрительном письме"},
        {"kk": "Мектептің киберқауіпсіздігін қамтамасыз ету бойынша ұсыныстар",
         "ru": "Предложения по обеспечению кибербезопасности школы"},
    ],
    "Оқу сауаттылығы": [
        {"kk": "Мәтінді түсіну және пайдалану", "ru": "Понимание и использование текста"},
        {"kk": "Шешімнің дәлелділігі мен логикасы", "ru": "Аргументация и логика решения"},
        {"kk": "Ұсынылған қадамдардың іске асырылу мүмкіндігі", "ru": "Реалистичность предложенных шагов"},
        {"kk": "Тапсырманың толық орындалуы", "ru": "Полнота выполнения задания"},
        {"kk": "Топтық жұмыстың үйлесімділігі және рәсімделуі",
         "ru": "Согласованность командной работы и оформление результата"},
    ],
    "Экологиялық сауаттылық": [
        {"kk": "Шешімнің Негізделуі", "ru": "Обоснованность Решения"},
        {"kk": "Этикалық Жетілу", "ru": "Этическая Зрелость"},
        {"kk": "Ымыраның Креативтілігі", "ru": "Креативность Компромисса"},
        {"kk": "Коммуникация Тиімділігі", "ru": "Эффективность Коммуникации"},
        {"kk": "Педагогикалық әлеует", "ru": "Педагогический потенциал"},
    ],
}

ALIASES = {
    "Естественно-научная грамотность": "Жаратылыстану-ғылыми сауаттылық",
    "Жаратылыстану-ғылыми сауаттылық": "Жаратылыстану-ғылыми сауаттылық",
    "Математическая грамотность": "Математикалық сауаттылық",
    "Математикалық сауаттылық": "Математикалық сауаттылық",
    "Межкультурная грамотность": "Мәдениетаралық сауаттылық",
    "Мәдениетаралық сауаттылық": "Мәдениетаралық сауаттылық",
    "Финансовая грамотность": "Қаржылық сауаттылық",
    "Қаржылық сауаттылық": "Қаржылық сауаттылық",
    "Цифровая грамотность": "Цифрлық сауаттылық",
    "Цифрлық сауаттылық": "Цифрлық сауаттылық",
    "Читательская грамотность": "Оқу сауаттылығы",
    "Оқырмандық сауаттылық": "Оқу сауаттылығы",
    "Оқу сауаттылығы": "Оқу сауаттылығы",
    "Экологическая грамотность": "Экологиялық сауаттылық",
    "Экологиялық сауаттылық": "Экологиялық сауаттылық",
}


# ---------------- Query params ----------------
def qp_get(key: str, default: str | None = None) -> str | None:
    v = st.query_params.get(key, default)
    if isinstance(v, list):
        return v[0] if v else default
    return v

def set_view(view: str | None, fs: bool):
    st.query_params.clear()
    if view is not None:
        st.query_params["view"] = view
        st.query_params["fs"] = "1" if fs else "0"

def clear_view():
    st.query_params.clear()


# ---------------- SAFE HTML RENDER ----------------
def render_html(html: str):
    html = textwrap.dedent(html).strip()
    st.markdown(html, unsafe_allow_html=True)


# ---------------- STYLES ----------------
def apply_base_css():
    render_html("""
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 2.0rem; max-width: 1400px; }
.small-muted { color: #8a8a8a; font-size: 0.92rem; }
.hr { height: 1px; background: rgba(0,0,0,0.08); border: none; margin: 1.2rem 0; }

.lb { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.lbrow { display: grid; grid-template-columns: 64px 1fr 110px; align-items: center; gap: 12px; border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 12px 14px; background: rgba(0,0,0,0.015); }
.lbrow .rank { font-weight: 950; font-size: 1.05rem; opacity: 0.95; }
.lbrow .team { line-height: 1.1; }
.lbrow .team .kk { font-weight: 900; font-size: 1.02rem; }
.lbrow .team .ru { color:#8a8a8a; font-size: 0.90rem; margin-top: 2px; }
.lbrow .score { text-align: right; font-weight: 950; font-size: 1.15rem; }
.badchip { display:inline-block; padding: 2px 10px; border-radius: 999px; border: 1px solid rgba(0,0,0,0.10); background: rgba(0,0,0,0.03); font-size: 0.85rem; color: #6f7680; margin-left: 10px; }

.drawwrap { display:grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 10px; }
.drawcard { border: 1px solid rgba(0,0,0,0.08); border-radius: 18px; padding: 14px; background: rgba(0,0,0,0.015); }
.drawtitle { font-weight: 950; font-size: 1.05rem; margin-bottom: 8px; }
.drawitem { border: 1px solid rgba(0,0,0,0.08); border-radius: 14px; padding: 10px 12px; margin: 8px 0; background: rgba(0,0,0,0.01); }
.drawitem.hl { border-color: rgba(34,197,94,0.50); box-shadow: 0 0 0 3px rgba(34,197,94,0.12); background: rgba(34,197,94,0.06); }
.drawitem.picked { border-color: rgba(59,130,246,0.30); background: rgba(59,130,246,0.05); }
.drawbadge { display:inline-block; font-size: 0.82rem; color:#6f7680; border:1px solid rgba(0,0,0,0.08); padding:2px 10px; border-radius:999px; margin-left: 10px; }
.commitbox { border:1px dashed rgba(0,0,0,0.12); border-radius: 16px; padding: 10px 12px; background: rgba(0,0,0,0.01); }

/* Make slider labels less tall */
div[data-testid="stSlider"] { padding-top: 0.15rem; padding-bottom: 0.05rem; }
</style>
""")

def apply_fullscreen_css():
    render_html("""
<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 0.8rem !important; max-width: 1600px !important; }
</style>
""")

def apply_normal_chrome_css_reset():
    render_html("""
<style>
#MainMenu { visibility: visible; }
footer { visibility: visible; }
header { visibility: visible; }
[data-testid="stToolbar"] { display: flex !important; }
[data-testid="stSidebar"] { display: block !important; }
[data-testid="stStatusWidget"] { display: block !important; }
[data-testid="stDecoration"] { display: block !important; }
</style>
""")


# ---------------- BILINGUAL HELPERS ----------------
def bi_h1(kk: str, ru: str):
    render_html(f"""
<div style="line-height:1.1">
  <div style="font-size:2.05rem;font-weight:950;margin:0;color:#111827">{kk}</div>
  <div class="small-muted">{ru}</div>
</div>
""")

def bi_h2(kk: str, ru: str):
    render_html(f"""
<div style="line-height:1.15;margin-top:0.2rem">
  <div style="font-size:1.22rem;font-weight:900;margin:0;color:#111827">{kk}</div>
  <div class="small-muted">{ru}</div>
</div>
""")

def caption_bi(kk: str, ru: str):
    render_html(f"<div class='small-muted'>{kk} • {ru}</div>")

def direction_bi_html(direction_kk: str) -> str:
    ru = DIRECTION_RU.get(direction_kk, "")
    return f"<div class='team'><div class='kk'>{direction_kk}</div><div class='ru'>{ru}</div></div>"


# ---------------- LOGO ----------------
def find_logo_path() -> str | None:
    for p in LOGO_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

def show_logo_sidebar_and_main(show_in_main: bool = True):
    p = find_logo_path()
    if not p:
        return
    st.sidebar.image(p, use_container_width=True)
    if show_in_main:
        st.image(p, use_container_width=True)


# ---------------- AUTH ----------------
def require_pin_if_needed():
    if not PIN_REQUIRED:
        return
    if st.session_state.get("pin_ok") is True:
        return

    st.sidebar.markdown(" ")
    st.sidebar.markdown("**PIN енгізіңіз**")
    st.sidebar.markdown("<div class='small-muted'>Введите PIN</div>", unsafe_allow_html=True)
    entered = st.sidebar.text_input("", type="password", key="pin_input")

    if entered != PIN:
        st.warning("PIN енгізіңіз / Введите PIN")
        st.stop()

    st.session_state["pin_ok"] = True


# ---------------- STORAGE ----------------
def default_state():
    scores = {d: [0] * len(CRITERIA_BI[d]) for d in DIRECTIONS}
    return {
        "scores": scores,
        "presentation_order": list(DIRECTIONS),
        "last_draw": None,
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

    if not isinstance(s, dict) or "scores" not in s:
        s = default_state()
        save_state(s)
        return s

    scores_in = s.get("scores")
    if not isinstance(scores_in, dict):
        scores_in = {}

    scores_out = {d: [0] * len(CRITERIA_BI[d]) for d in DIRECTIONS}

    for k, v in scores_in.items():
        kk_name = ALIASES.get(k)
        if not kk_name or kk_name not in scores_out:
            continue
        want_len = len(CRITERIA_BI[kk_name])
        if isinstance(v, list) and len(v) == want_len:
            scores_out[kk_name] = [int(x) for x in v]
        elif isinstance(v, dict):
            tmp = [0] * want_len
            for i in range(want_len):
                tmp[i] = int(v.get(str(i), v.get(i, 0)) or 0)
            scores_out[kk_name] = tmp

    s["scores"] = scores_out

    po = s.get("presentation_order")
    if not isinstance(po, list):
        po = list(DIRECTIONS)
    else:
        mapped = []
        for x in po:
            kk = ALIASES.get(x)
            if kk and kk in DIRECTIONS and kk not in mapped:
                mapped.append(kk)
        for d in DIRECTIONS:
            if d not in mapped:
                mapped.append(d)
        po = mapped
    s["presentation_order"] = po

    if s.get("last_draw") is not None and not isinstance(s["last_draw"], dict):
        s["last_draw"] = None

    if "updated_at" not in s:
        s["updated_at"] = None

    return s


# ---------------- KEYS & SESSION SYNC ----------------
def score_key(direction: str, idx: int) -> str:
    h = hashlib.md5(f"{direction}|{idx}".encode("utf-8")).hexdigest()
    return f"score_{h}"

def sync_session_from_file_state(file_state: dict):
    file_stamp = file_state.get("updated_at")
    if st.session_state.get("_scores_loaded_at") == file_stamp:
        return
    for d in DIRECTIONS:
        arr = file_state["scores"].get(d, [0] * len(CRITERIA_BI[d]))
        for i in range(len(CRITERIA_BI[d])):
            st.session_state[score_key(d, i)] = int(arr[i])
    st.session_state["_scores_loaded_at"] = file_stamp


# ---------------- COMPUTE ----------------
def totals_df(state: dict) -> pd.DataFrame:
    rows = []
    for d in DIRECTIONS:
        total = sum(int(x) for x in state["scores"][d])
        rows.append({"Бағыт": d, "Total": total})
    df = pd.DataFrame(rows).sort_values(["Total", "Бағыт"], ascending=[False, True]).reset_index(drop=True)
    return df

def details_df(state: dict) -> pd.DataFrame:
    rows = []
    for d in DIRECTIONS:
        for i, crit in enumerate(CRITERIA_BI[d], start=1):
            rows.append({
                "Бағыт (KK)": d,
                "Направление (RU)": DIRECTION_RU.get(d, ""),
                "N": i,
                "Критерий (KK)": crit["kk"],
                "Критерий (RU)": crit["ru"],
                "Score": int(state["scores"][d][i - 1]),
            })
    return pd.DataFrame(rows)

def to_excel_bytes(df_totals: pd.DataFrame, df_details: pd.DataFrame, updated_at: str) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_totals.to_excel(writer, index=False, sheet_name="Totals")
        df_details.to_excel(writer, index=False, sheet_name="Details")
        pd.DataFrame({"updated_at": [updated_at]}).to_excel(writer, index=False, sheet_name="Meta")
    buf.seek(0)
    return buf.getvalue()


# ---------------- RANDOMIZER (LIST ONLY) ----------------
def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def draw_html(picked: list[str], remaining: list[str], highlight_idx: int | None):
    left = ""
    if picked:
        for i, name in enumerate(picked, start=1):
            left += f"<div class='drawitem picked'>{direction_bi_html(name)}<span class='drawbadge'>{i}</span></div>"
    else:
        left = "<div class='small-muted'>Әлі таңдалмаған • Пока не выбрано</div>"

    right = ""
    if remaining:
        for i, name in enumerate(remaining, start=1):
            cls = "hl" if (highlight_idx is not None and i - 1 == highlight_idx) else ""
            right += f"<div class='drawitem {cls}'>{direction_bi_html(name)}</div>"
    else:
        right = "<div class='small-muted'>Аяқталды • Завершено</div>"

    return f"""
<div class="drawwrap">
  <div class="drawcard">
    <div class="drawtitle">Таңдалған кезектілік <span class="small-muted">Выбранный порядок</span></div>
    {left}
  </div>
  <div class="drawcard">
    <div class="drawtitle">Қалған бағыттар <span class="small-muted">Оставшиеся направления</span></div>
    {right}
  </div>
</div>
"""

def run_fair_draw_animation_with_seed(seed: str, directions: list[str]) -> list[str]:
    rng = random.Random(int(seed, 16))
    final_order = list(directions)
    rng.shuffle(final_order)

    remaining = list(directions)
    picked: list[str] = []

    ph_list = st.empty()
    prog = st.progress(0.0)
    rng_visual = random.Random()

    for k, chosen in enumerate(final_order, start=1):
        chosen_idx = remaining.index(chosen)

        for _ in range(20):
            hi = rng_visual.randrange(len(remaining))
            with ph_list:
                render_html(draw_html(picked, remaining, hi))
            time.sleep(0.05)

        for _ in range(7):
            with ph_list:
                render_html(draw_html(picked, remaining, chosen_idx))
            time.sleep(0.06)

        picked.append(chosen)
        remaining.remove(chosen)
        prog.progress(k / len(final_order))

        with ph_list:
            render_html(draw_html(picked, remaining, None))

    return final_order


# ---------------- RADAR ----------------
def wrap_label(s: str, width: int = 22) -> str:
    return "\n".join(textwrap.wrap(s, width=width)) if len(s) > width else s

def plot_radar(direction_kk: str, values: list[int], max_val: int = 2):
    crits = CRITERIA_BI[direction_kk]
    labels = [
        f"{i+1}. {wrap_label(c['kk'], 22)}\n{wrap_label(c['ru'], 22)}"
        for i, c in enumerate(crits)
    ]
    n = len(labels)
    angles = [i / float(n) * 2 * pi for i in range(n)]
    angles += angles[:1]
    vals = list(values) + [values[0]]

    fig, ax = plt.subplots(figsize=(6.4, 6.4), subplot_kw=dict(polar=True))
    ax.set_theta_offset(pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.tick_params(axis="x", pad=34)

    ax.set_ylim(0, max_val)
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["0 ұпай\n0 балл", "1 ұпай\n1 балл", "2 ұпай\n2 балл"], fontsize=10)
    ax.set_rlabel_position(90)

    ax.grid(alpha=0.22)
    ax.yaxis.grid(alpha=0.30, linewidth=1.05)
    ax.spines["polar"].set_alpha(0.25)

    ax.plot(angles, vals, linewidth=2.8, alpha=0.95)
    ax.fill(angles, vals, alpha=0.12)

    ax.set_title(
        f"{direction_kk}\n{DIRECTION_RU.get(direction_kk, '')}",
        fontsize=13,
        fontweight="bold",
        pad=28,
    )
    fig.subplots_adjust(top=0.86, bottom=0.06, left=0.04, right=0.96)
    return fig


# ---------------- Render helpers ----------------
def render_order_list(state: dict, show_heading: bool = True):
    if show_heading:
        bi_h2(
            "Жеребе арқылы анықталған презентациялар кезектілігі:",
            "Очередность презентаций, определенная жеребьёвкой:",
        )
    order = state.get("presentation_order") or list(DIRECTIONS)
    rows = "<div class='lb'>"
    for i, name in enumerate(order, start=1):
        rows += f"<div class='lbrow'><div class='rank'>{i}</div><div>{direction_bi_html(name)}</div><div class='score'></div></div>"
    rows += "</div>"
    render_html(rows)

def render_leaderboard(state: dict, show_heading: bool = True):
    df_tot = totals_df(state)
    if show_heading:
        bi_h2("Жалпы ұпай (кему ретімен)", "Общий балл (по убыванию)")
    rows_html = "<div class='lb'>"
    for i, row in df_tot.reset_index(drop=True).iterrows():
        rank = i + 1
        name = row["Бағыт"]
        total = int(row["Total"])
        badge = f"{rank}-орын"
        rows_html += (
            f"<div class='lbrow'>"
            f"<div class='rank'>{rank}</div>"
            f"<div class='team'><div class='kk'>{name}<span class='badchip'>{badge}</span></div>"
            f"<div class='ru'>{DIRECTION_RU.get(name,'')}</div></div>"
            f"<div class='score'>{total}</div>"
            f"</div>"
        )
    rows_html += "</div>"
    render_html(rows_html)

def render_radars_normal(state: dict, order: list[str]):
    bi_h2("Бағыттардың профилі (радар диаграмма, шкала 0–2)", "Профиль направлений (радар-диаграмма, шкала 0–2)")
    per_row = 2
    for start in range(0, len(order), per_row):
        cols = st.columns(per_row)
        for j in range(per_row):
            idx = start + j
            if idx >= len(order):
                break
            d = order[idx]
            vals = [int(x) for x in state["scores"][d]]
            with cols[j]:
                with st.container(border=True):
                    fig = plot_radar(d, vals, MAX_PER_CRITERION)
                    st.pyplot(fig, clear_figure=True)


# ---------------- MAIN APP ----------------
apply_base_css()

view = qp_get("view", None)
fs = qp_get("fs", "0") == "1"

# Fullscreen view mode ONLY for: order + leaderboard
if view in {"order", "leaderboard"}:
    if fs:
        apply_fullscreen_css()

    state = load_state()

    if view == "order":
        bi_h1("Презентациялар кезектілігі", "Очередность презентаций")
        render_html("<hr class='hr'>")
        render_order_list(state, show_heading=True)

    elif view == "leaderboard":
        bi_h1("Нәтижелер", "Результаты")
        render_html("<hr class='hr'>")
        render_leaderboard(state, show_heading=True)

    # Bottom-right "Қайту" button (placed at the end, right aligned)
    render_html("<div style='height: 18px'></div>")
    c_sp, c_btn = st.columns([10, 2])
    with c_btn:
        if st.button("Қайту", use_container_width=True, key="exit_fullscreen"):
            clear_view()
            st.rerun()
        render_html("<div class='small-muted' style='text-align:right;margin-top:4px'>Назад</div>")

    st.stop()

# Normal app mode
apply_normal_chrome_css_reset()
show_logo_sidebar_and_main(show_in_main=True)

state = load_state()

st.sidebar.markdown("### Режим / Режим")
mode = st.sidebar.radio(
    " ",
    ["Презентациялар кезектілігі", "Бағалау", "Нәтижелер"],
    index=0,
    key="mode_radio",
)

# ---------------- SETTINGS ----------------
if mode == "Презентациялар кезектілігі":
    require_pin_if_needed()

    bi_h1("Презентациялар кезектілігін анықтау", "Определение очередности презентаций")
    caption_bi(f"Жаңартылды: {state.get('updated_at')}", f"Обновлено: {state.get('updated_at')}")
    render_html("<hr class='hr'>")

    last = state.get("last_draw") or {}
    if last:
        render_html(f"""
<div class="commitbox">
  <div><b>Соңғы жеребе</b> <span class="small-muted">Последняя жеребьёвка</span>: {last.get("time","")}</div>
  <div class="small-muted">Commit: <code>{last.get("commit","")}</code></div>
  <div class="small-muted">Seed: <code>{last.get("seed","")}</code></div>
</div>
""")

    c1, c2, _ = st.columns([1.2, 1.1, 2.7])

    do_draw = c1.button("Жеребе тарту", key="draw_btn", use_container_width=True)
    c1.caption("Провести жеребьёвку")

    do_reset = c2.button("Әдепкі рет", key="reset_order_btn", use_container_width=True)
    c2.caption("Сброс порядка")

    if do_draw:
        seed = secrets.token_hex(16)
        commit = sha256_hex(seed)
        render_html(f"""
<div class="commitbox">
  <div><b>Жеребе әділдігі</b> <span class="small-muted">Честность жеребьёвки</span></div>
  <div class="small-muted">Commit: <code>{commit}</code></div>
</div>
""")

        order = run_fair_draw_animation_with_seed(seed, DIRECTIONS)

        state["presentation_order"] = order
        state["last_draw"] = {
            "commit": commit,
            "seed": seed,
            "method": "random.Random(int(seed,16)).shuffle()",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_state(state)

        st.success("Жеребе аяқталды. Seed ашылды.")
        st.caption("Жеребьёвка завершена. Seed раскрыт.")
        st.info(f"Seed: {seed}")
        st.rerun()

    if do_reset:
        state["presentation_order"] = list(DIRECTIONS)
        state["last_draw"] = None
        save_state(state)
        st.success("Реттілік қалпына келтірілді.")
        st.caption("Порядок сброшен.")
        st.rerun()

    render_html("<hr class='hr'>")
    render_order_list(state, show_heading=True)

    cfs1, _ = st.columns([1, 5])
    if cfs1.button("Толық экран", use_container_width=True, key="fs_order"):
        set_view("order", True)
        st.rerun()

# ---------------- JURY ----------------
elif mode == "Бағалау":
    require_pin_if_needed()
    sync_session_from_file_state(state)

    bi_h1("Бағалау", "Оценивание")
    caption_bi(f"Жаңартылды: {state.get('updated_at')}", f"Обновлено: {state.get('updated_at')}")
    render_html("<hr class='hr'>")

    bi_h2("Бағаларды енгізу (0–2)", "Ввод баллов (0–2)")

    for d in DIRECTIONS:
        with st.container(border=True):
            current_vals = [int(st.session_state.get(score_key(d, i), 0)) for i in range(len(CRITERIA_BI[d]))]
            total = sum(current_vals)
            render_html(
                f"<div style='margin-bottom:8px'><b>{d}</b>"
                f"<div class='small-muted'>{DIRECTION_RU.get(d,'')}</div>"
                f"<div class='small-muted'>Жалпы ұпай: {total} • Общий балл: {total}</div></div>"
            )

            for i, crit in enumerate(CRITERIA_BI[d], start=1):
                render_html(f"<div><b>{i}. {crit['kk']}</b><div class='small-muted'>{crit['ru']}</div></div>")

                # SHORTER slider line: put slider in a narrower column
                s_col, _ = st.columns([1.2, 2.8])
                with s_col:
                    st.slider(
                        label=f"{d}-{i}",
                        min_value=0,
                        max_value=MAX_PER_CRITERION,
                        value=int(st.session_state.get(score_key(d, i - 1), 0)),
                        step=1,
                        key=score_key(d, i - 1),
                        label_visibility="collapsed",
                    )

    c1, c2, _ = st.columns([1, 1, 2])
    do_save = c1.button("Сақтау", key="save_scores_btn", use_container_width=True)
    c1.caption("Сохранить")
    do_reset = c2.button("Барлығын 0-ге қайтару", key="reset_scores_btn", use_container_width=True)
    c2.caption("Сбросить всё в 0")

    if do_save:
        for d in DIRECTIONS:
            arr = [int(st.session_state.get(score_key(d, i), 0)) for i in range(len(CRITERIA_BI[d]))]
            state["scores"][d] = arr
        save_state(state)
        st.success("Сақталды.")
        st.caption("Сохранено.")
        st.rerun()

    if do_reset:
        for d in DIRECTIONS:
            for i in range(len(CRITERIA_BI[d])):
                st.session_state[score_key(d, i)] = 0
            state["scores"][d] = [0] * len(CRITERIA_BI[d])
        save_state(state)
        st.success("Қайтарылды.")
        st.caption("Сброс выполнен.")
        st.rerun()

# ---------------- RESULTS ----------------
else:
    bi_h1("Нәтижелер", "Результаты")
    caption_bi(
        f"Соңғы жаңарту: {state.get('updated_at')}",
        f"Последнее обновление: {state.get('updated_at')}",
    )

    updated_at = state.get("updated_at") or ""
    order = state.get("presentation_order") or list(DIRECTIONS)

    render_html("<hr class='hr'>")
    # Fullscreen for radars removed (requested). Only show normal radars.
    render_radars_normal(state, order)

    render_html("<hr class='hr'>")
    render_leaderboard(state, show_heading=True)

    cfs3, _ = st.columns([1, 5])
    if cfs3.button("Толық экран", use_container_width=True, key="fs_leaderboard"):
        set_view("leaderboard", True)
        st.rerun()

    # Download at very bottom
    df_tot = totals_df(state)
    df_det = details_df(state)
    excel_bytes = to_excel_bytes(df_tot.copy(), df_det.copy(), updated_at)
    filename = f"hackathon_results_{updated_at.replace(':','-').replace(' ','_') or 'export'}.xlsx"

    render_html("<hr class='hr'>")
    st.download_button(
        label="Нәтижені Excel ретінде жүктеу",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="download_excel_btn",
    )
    st.caption("Скачать результаты в Excel")
