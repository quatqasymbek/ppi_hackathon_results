import json
import os
import random
import secrets
import time
import hashlib
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

# Бағыттар / Направления (fixed)
DIRECTIONS = [
    "Естественно-научная грамотность",
    "Математикалық сауаттылық",
    "Межкультурная грамотность",
    "Финансовая грамотность",
    "Цифровая грамотность",
    "Читательская грамотность",
    "Экологиялық сауаттылық",
]

# Bilingual criteria per direction (fixed) - each item: {"kk": ..., "ru": ...}
CRITERIA_BI = {
    "Естественно-научная грамотность": [
        {"kk": "Суды сүзудің тиімділігі", "ru": "Эффективность фильтрации воды"},
        {"kk": "Сүзгінің жұмысын ғылыми тұрғыда түсіндіру", "ru": "Научное объяснение работы фильтра"},
        {"kk": "Сүзгінің құрылымы және жинақталуы", "ru": "Конструкция и сборка фильтра"},
        {"kk": "Нәтижені талдау және қорытынды", "ru": "Анализ результата и выводы"},
        {"kk": "Презентация және командалық жұмыс", "ru": "Презентация и командная работа"},
    ],
    "Математикалық сауаттылық": [
        {"kk": "Жалпы ауданды табу", "ru": "Находит общую площадь"},
        {"kk": "Камераның бақылауына кірмейтін ауданның пайызын есептеу", "ru": "Вычисляет процент площади не попадающих под камеру"},
        {"kk": "Камераның бақылауына кіретін аудандарды салыстыру", "ru": "Сравнивает площади, попадающих под камеру"},
        {"kk": "Камералардың максималды санын есептеу", "ru": "Вычисляет максимальное количество камер"},
        {"kk": "Камералардың минималды санын есептеу", "ru": "Вычисляет минимальное количество камер"},
    ],
    "Межкультурная грамотность": [
        {"kk": "Дұрыс және проблемалы хабарламаларды анықтау", "ru": "Определение корректного и проблемных сообщений"},
        {"kk": "Мәдениетаралық тәуекелдерді талдау", "ru": "Аргументация и анализ межкультурных рисков"},
        {"kk": "Мәдениетаралық сауаттылық қағидаттарын түсіну", "ru": "Понимание принципов межкультурной грамотности"},
        {"kk": "Оқушыларға арналған практикалық ұсынымдар", "ru": "Практические рекомендации обучающимся"},
        {"kk": "Фестивальге арналған мини-нұсқаулық", "ru": "Мини-инструкция (памятка) для фестиваля"},
    ],
    "Финансовая грамотность": [
        {"kk": "Бюджетті жоспарлау және негіздеу", "ru": "Планирование и обоснование бюджета"},
        {"kk": "Ресурстарды ұтымды бөлу", "ru": "Логичное и рациональное распределение ресурсов"},
        {"kk": "Қаржылық тәуекелдерді бағалау", "ru": "Оценка финансовых рисков"},
        {"kk": "Командалық жұмыс және қорғау мәдениеті", "ru": "Командная работа и культура защиты"},
        {"kk": "Мектеп үшін білім беру әсері", "ru": "Образовательный эффект для школы"},
    ],
    "Цифровая грамотность": [
        {"kk": "Легитимді хатты анықтау", "ru": "Определение легитимного письма"},
        {"kk": "Цифрлық тәуекелдерді талдау және аргументация", "ru": "Анализ и аргументация цифровых рисков"},
        {"kk": "Цифрлық қауіпсіздік қағидаттарын түсіну", "ru": "Понимание принципов цифровой безопасности"},
        {"kk": "Күмәнді хат алған жағдайда әрекет ету алгоритмі", "ru": "Алгоритм действий при подозрительном письме"},
        {"kk": "Мектептің киберқауіпсіздігін қамтамасыз ету бойынша ұсыныстар", "ru": "Предложения по обеспечению кибербезопасности школы"},
    ],
    "Читательская грамотность": [
        {"kk": "Мәтінді түсіну және пайдалану", "ru": "Понимание и использование текста"},
        {"kk": "Шешімнің дәлелділігі мен логикасы", "ru": "Аргументация и логика решения"},
        {"kk": "Ұсынылған қадамдардың іске асырылу мүмкіндігі", "ru": "Реалистичность предложенных шагов"},
        {"kk": "Тапсырманың толық орындалуы", "ru": "Полнота выполнения задания"},
        {"kk": "Топтық жұмыстың үйлесімділігі және рәсімделуі", "ru": "Согласованность командной работы и оформление результата"},
    ],
    "Экологиялық сауаттылық": [
        {"kk": "Шешімнің Негізделуі", "ru": "Обоснованность Решения"},
        {"kk": "Этикалық Жетілу", "ru": "Этическая Зрелость"},
        {"kk": "Ымыраның Креативтілігі", "ru": "Креативность Компромисса"},
        {"kk": "Коммуникация Тиімділігі", "ru": "Эффективность Коммуникации"},
        {"kk": "Педагогикалық әлеует", "ru": "Педагогический потенциал"},
    ],
}

# ---------------- SAFE HTML RENDER ----------------
def render_html(html: str):
    html = textwrap.dedent(html).strip()
    st.markdown(html, unsafe_allow_html=True)

# ---------------- GLOBAL STYLE ----------------
render_html("""
<style>
.block-container { padding-top: 2.2rem; padding-bottom: 2.0rem; max-width: 1400px; }
.small-muted { color: #8a8a8a; font-size: 0.92rem; }
.hr { height: 1px; background: rgba(255,255,255,0.10); border: none; margin: 1.2rem 0; }

.lb { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
.lbrow { display: grid; grid-template-columns: 64px 1fr 110px; align-items: center; gap: 12px; border: 1px solid rgba(255,255,255,0.10); border-radius: 16px; padding: 12px 14px; background: rgba(255,255,255,0.03); }
.lbrow .rank { font-weight: 950; font-size: 1.1rem; opacity: 0.95; }
.lbrow .team { font-weight: 850; font-size: 1.05rem; line-height: 1.15; }
.lbrow .score { text-align: right; font-weight: 950; font-size: 1.15rem; }
.lbrow.top1 { background: rgba(34,197,94,0.12); }
.lbrow.top2 { background: rgba(59,130,246,0.12); }
.lbrow.top3 { background: rgba(245,158,11,0.12); }
.badchip { display:inline-block; padding: 2px 10px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.04); font-size: 0.85rem; color: #9aa0a6; margin-left: 10px; }

.drawwrap { display:grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 10px; }
.drawcard { border: 1px solid rgba(255,255,255,0.10); border-radius: 18px; padding: 14px; background: rgba(255,255,255,0.03); }
.drawtitle { font-weight: 950; font-size: 1.05rem; margin-bottom: 8px; }
.drawitem { border: 1px solid rgba(255,255,255,0.10); border-radius: 14px; padding: 10px 12px; margin: 8px 0; background: rgba(255,255,255,0.02); }
.drawitem.hl { border-color: rgba(34,197,94,0.60); box-shadow: 0 0 0 3px rgba(34,197,94,0.20); background: rgba(34,197,94,0.08); }
.drawitem.picked { border-color: rgba(59,130,246,0.35); background: rgba(59,130,246,0.07); }
.drawbadge { display:inline-block; font-size: 0.82rem; color:#9aa0a6; border:1px solid rgba(255,255,255,0.10); padding:2px 10px; border-radius:999px; margin-left: 10px; }
.bigcenter { text-align:center; font-weight: 950; font-size: 1.2rem; margin-top: 6px; }
.commitbox { border:1px dashed rgba(255,255,255,0.18); border-radius: 16px; padding: 10px 12px; background: rgba(255,255,255,0.02); }
</style>
""")

# ---------------- BILINGUAL HELPERS ----------------
def bi_h1(kk: str, ru: str):
    render_html(f"""
<div style="line-height:1.1">
  <div style="font-size:2.05rem;font-weight:950;margin:0">{kk}</div>
  <div class="small-muted">{ru}</div>
</div>
""")

def bi_h2(kk: str, ru: str):
    render_html(f"""
<div style="line-height:1.15;margin-top:0.2rem">
  <div style="font-size:1.22rem;font-weight:900;margin:0">{kk}</div>
  <div class="small-muted">{ru}</div>
</div>
""")

def caption_bi(kk: str, ru: str):
    render_html(f"<div class='small-muted'>{kk} • {ru}</div>")

# ---------------- AUTH ----------------
def require_pin_if_needed():
    if not PIN_REQUIRED:
        return
    entered = st.sidebar.text_input("PIN (Әділқазы / Жюри)", type="password", key="pin_input")
    if entered != PIN:
        st.warning("PIN енгізіңіз / Введите PIN")
        st.stop()

# ---------------- STORAGE ----------------
def default_state():
    scores = {d: [0] * len(CRITERIA_BI[d]) for d in DIRECTIONS}
    return {
        "directions": list(DIRECTIONS),
        "scores": scores,
        "presentation_order": list(DIRECTIONS),
        "last_draw": None,   # {"commit":..., "seed":..., "method":..., "time":...}
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

    # If old format or broken structure -> reset
    if not isinstance(s, dict) or "scores" not in s:
        s = default_state()
        save_state(s)
        return s

    # Force fixed directions
    s["directions"] = list(DIRECTIONS)

    # Fix scores structure to {direction: [0..0] len=5}
    if not isinstance(s.get("scores"), dict):
        s["scores"] = {}

    for d in DIRECTIONS:
        want_len = len(CRITERIA_BI[d])
        cur = s["scores"].get(d)

        if not isinstance(cur, list) or len(cur) != want_len:
            # try to salvage from old dict-based scores if present
            if isinstance(cur, dict):
                # take values by index order if keys are 0.. etc, else zeros
                tmp = [0] * want_len
                for i in range(want_len):
                    tmp[i] = int(cur.get(str(i), cur.get(i, 0)) or 0)
                s["scores"][d] = tmp
            else:
                s["scores"][d] = [0] * want_len
        else:
            s["scores"][d] = [int(x) for x in cur]

    # Presentation order
    po = s.get("presentation_order")
    if not isinstance(po, list):
        s["presentation_order"] = list(DIRECTIONS)
    else:
        po = [x for x in po if x in DIRECTIONS]
        for d in DIRECTIONS:
            if d not in po:
                po.append(d)
        s["presentation_order"] = po

    # last_draw can be None or dict
    if s.get("last_draw") is not None and not isinstance(s["last_draw"], dict):
        s["last_draw"] = None

    return s

# ---------------- KEYS & SESSION SYNC ----------------
def score_key(direction: str, idx: int) -> str:
    h = hashlib.md5(f"{direction}|{idx}".encode("utf-8")).hexdigest()
    return f"score_{h}"

def sync_session_from_file_state(file_state: dict):
    """
    Sync inputs from file into session_state when file updated_at changes.
    Prevents the 'controls not changing' / 'resetting' behavior.
    """
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
        rows.append({"Бағыт / Направление": d, "Total": total})
    df = pd.DataFrame(rows).sort_values(["Total", "Бағыт / Направление"], ascending=[False, True]).reset_index(drop=True)
    return df

def details_df(state: dict) -> pd.DataFrame:
    rows = []
    for d in DIRECTIONS:
        for i, crit in enumerate(CRITERIA_BI[d], start=1):
            rows.append({
                "Бағыт / Направление": d,
                "№": i,
                "Criterion (KK)": crit["kk"],
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

# ---------------- RANDOMIZER (FAIR DRAW) ----------------
def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def draw_html(picked: list[str], remaining: list[str], highlight_idx: int | None):
    def item_html(name: str, cls: str, badge: str | None = None):
        b = f"<span class='drawbadge'>{badge}</span>" if badge else ""
        return f"<div class='drawitem {cls}'>{name}{b}</div>"

    left = "".join(item_html(n, "picked", f"#{i}") for i, n in enumerate(picked, start=1))
    if not left:
        left = "<div class='small-muted'>—</div>"

    right_parts = []
    for i, n in enumerate(remaining):
        cls = "hl" if (highlight_idx is not None and i == highlight_idx) else ""
        right_parts.append(item_html(n, cls, None))
    right = "".join(right_parts) if right_parts else "<div class='small-muted'>—</div>"

    return f"""
<div class="drawwrap">
  <div class="drawcard">
    <div class="drawtitle">✅ Таңдалған реттілік / Выбранный порядок</div>
    {left}
  </div>
  <div class="drawcard">
    <div class="drawtitle">🎯 Қалған бағыттар / Оставшиеся направления</div>
    {right}
  </div>
</div>
"""

def run_fair_draw_animation(directions: list[str]) -> tuple[list[str], dict]:
    """
    Commit-reveal:
      1) create seed (hidden), show commit hash
      2) compute final order using deterministic shuffle(seed)
      3) animate revealing picks
      4) reveal seed for verification
    """
    seed = secrets.token_hex(16)
    commit = sha256_hex(seed)
    method = "random.Random(int(seed,16)).shuffle()"

    # final order determined ONLY by seed
    rng = random.Random(int(seed, 16))
    final_order = list(directions)
    rng.shuffle(final_order)

    # animate reveal
    remaining = list(directions)
    picked: list[str] = []
    ph = st.empty()
    prog = st.progress(0.0)

    for k, chosen in enumerate(final_order, start=1):
        # random highlight flicker (visual only, does NOT affect outcome)
        for _ in range(22):
            hi = random.randrange(len(remaining))
            with ph:
                render_html(draw_html(picked, remaining, hi))
            time.sleep(0.05)

        # land on the chosen item clearly
        chosen_idx = remaining.index(chosen)
        for _ in range(6):
            with ph:
                render_html(draw_html(picked, remaining, chosen_idx))
            time.sleep(0.06)

        picked.append(chosen)
        remaining.remove(chosen)
        prog.progress(k / len(final_order))
        time.sleep(0.12)

        with ph:
            render_html(draw_html(picked, remaining, None))

    draw_meta = {
        "commit": commit,
        "seed": seed,
        "method": method,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return final_order, draw_meta

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

    bi_h2("Жеребе (рандомайзер) — әділ және көрнекі", "Жеребьёвка — честно и наглядно")

    last = state.get("last_draw") or {}
    if last:
        render_html(f"""
<div class="commitbox">
  <div><b>Соңғы жеребе / Последняя жеребьёвка:</b> {last.get("time","")}</div>
  <div class="small-muted">Commit: <code>{last.get("commit","")}</code></div>
  <div class="small-muted">Seed: <code>{last.get("seed","")}</code></div>
</div>
""")

    c1, c2, c3 = st.columns([1.3, 1.0, 2.7])
    if c1.button("🎲 Жеребе тарту / Провести жеребьёвку", key="draw_btn", use_container_width=True):
        render_html("<div class='bigcenter'>⏳ Жеребе өтіп жатыр... / Идёт жеребьёвка...</div>")
        render_html(f"""
<div class="commitbox">
  <div><b>Commit (алдын ала дәлел):</b></div>
  <div class="small-muted">
    Төменде анимация кезінде нәтиже өзгермейді. Соңында seed ашылады. <br/>
    Во время анимации результат не меняется. В конце seed будет показан.
  </div>
</div>
""")
        order, meta = run_fair_draw_animation(DIRECTIONS)
        state["presentation_order"] = order
        state["last_draw"] = meta
        save_state(state)

        st.success(f"Seed ашылды / Seed раскрыт: {meta['seed']}")
        st.info("Қаласаңыз тексеріңіз: бірдей seed болса — бірдей реттілік / Можно проверить: один seed — один порядок.")
        st.rerun()

    if c2.button("↩ Әдепкі рет / Сброс порядка", key="reset_order_btn", use_container_width=True):
        state["presentation_order"] = list(DIRECTIONS)
        state["last_draw"] = None
        save_state(state)
        st.success("Реттілік қалпына келтірілді / Порядок сброшен")
        st.rerun()

    render_html("<hr class='hr'>")
    bi_h2("Ағымдағы көрсету реті", "Текущий порядок выступления")
    order = state.get("presentation_order") or list(DIRECTIONS)
    rows = "<div class='lb'>"
    for i, name in enumerate(order, start=1):
        rows += f"<div class='lbrow'><div class='rank'>#{i}</div><div class='team'>{name}</div><div class='score'></div></div>"
    rows += "</div>"
    render_html(rows)

    render_html("<hr class='hr'>")
    bi_h2("Бағыттар мен критерийлер (бекітілген)", "Направления и критерии (фиксированные)")
    with st.expander("👀 Көру / Смотреть", expanded=False):
        for d in DIRECTIONS:
            st.markdown(f"### {d}")
            for i, crit in enumerate(CRITERIA_BI[d], start=1):
                st.write(f"{i}. {crit['kk']} — {crit['ru']}")
            st.write("")

# ---------------- JURY ----------------
elif mode.startswith("Әділқазы"):
    require_pin_if_needed()
    sync_session_from_file_state(state)

    bi_h1("Әділқазы панелі", "Панель жюри")
    caption_bi(f"Жаңартылды: {state.get('updated_at')}", f"Обновлено: {state.get('updated_at')}")
    render_html("<hr class='hr'>")

    bi_h2("Бағаларды енгізу (0–2)", "Ввод баллов (0–2)")
    caption_bi("Слайдер арқылы өзгертіңіз — сенімді жұмыс істейді", "Меняйте слайдером — работает стабильно")

    for d in DIRECTIONS:
        with st.container(border=True):
            # current total for this direction (from session_state)
            vals = [int(st.session_state.get(score_key(d, i), 0)) for i in range(len(CRITERIA_BI[d]))]
            st.markdown(f"### {d}  &nbsp; <span class='badchip'>Total: {sum(vals)}</span>", unsafe_allow_html=True)

            for i, crit in enumerate(CRITERIA_BI[d], start=1):
                k = score_key(d, i - 1)
                label = f"{i}. {crit['kk']}\n{crit['ru']}"
                st.slider(
                    label,
                    min_value=0,
                    max_value=MAX_PER_CRITERION,
                    value=int(st.session_state.get(k, 0)),
                    step=1,
                    key=k,
                )

    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("💾 Сақтау / Сохранить", key="save_scores_btn", use_container_width=True):
        # collect from session_state and save to file
        for d in DIRECTIONS:
            arr = []
            for i in range(len(CRITERIA_BI[d])):
                arr.append(int(st.session_state.get(score_key(d, i), 0)))
            state["scores"][d] = arr
        save_state(state)
        st.success("Сақталды / Сохранено")
        st.rerun()

    if c2.button("↩ Барлығын 0-ге қайтару / Сбросить всё в 0", key="reset_scores_btn", use_container_width=True):
        for d in DIRECTIONS:
            for i in range(len(CRITERIA_BI[d])):
                st.session_state[score_key(d, i)] = 0
            state["scores"][d] = [0] * len(CRITERIA_BI[d])
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

    rows = "<div class='lb'>"
    for i, name in enumerate(order, start=1):
        rows += f"<div class='lbrow'><div class='rank'>#{i}</div><div class='team'>{name}</div><div class='score'></div></div>"
    rows += "</div>"
    render_html(rows)

    # Leaderboard
    render_html("<hr class='hr'>")
    bi_h2("Жалпы ұпай (кему ретімен)", "Общий балл (по убыванию)")
    df_tot = totals_df(state)

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    rows_html = "<div class='lb'>"
    for i, row in df_tot.iterrows():
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

    # Per-direction criteria charts (bilingual labels)
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

            crits = CRITERIA_BI[d]
            scores = state["scores"][d]

            df_one = pd.DataFrame({
                "Label": [f"{i+1}. {crits[i]['kk']}\n{crits[i]['ru']}" for i in range(len(crits))],
                "Score": [int(x) for x in scores],
                "KK": [crits[i]["kk"] for i in range(len(crits))],
                "RU": [crits[i]["ru"] for i in range(len(crits))],
            })

            chart = (
                alt.Chart(df_one)
                .mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10)
                .encode(
                    x=alt.X("Label:N", sort=None, title=None, axis=alt.Axis(labelAngle=-20, labelLimit=240)),
                    y=alt.Y("Score:Q", title=None, scale=alt.Scale(domain=[0, MAX_PER_CRITERION])),
                    tooltip=[
                        alt.Tooltip("KK:N", title="Қаз / KK"),
                        alt.Tooltip("RU:N", title="Рус / RU"),
                        alt.Tooltip("Score:Q", title="Балл"),
                    ],
                )
                .properties(height=290, title=d)
            )
            cols[j].altair_chart(chart, use_container_width=True)

    # Export
    df_det = details_df(state)
    excel_bytes = to_excel_bytes(df_tot.copy(), df_det.copy(), updated_at)
    filename = f"hackathon_results_{updated_at.replace(':','-').replace(' ','_') or 'export'}.xlsx"
    st.download_button(
        label="⬇️ Нәтижені Excel ретінде жүктеу / Скачать результаты в Excel",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="download_excel_btn",
    )
