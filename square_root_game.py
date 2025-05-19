import streamlit as st
import random, math, time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets 連携 ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open("ScoreBoard").sheet1

# === 効果音 URL ===
NAME_URL    = "https://github.com/trpv1/square-root-app/raw/main/static/name.mp3"
START_URL   = "https://github.com/trpv1/square-root-app/raw/main/static/start.mp3"
CORRECT_URL = "https://github.com/trpv1/square-root-app/raw/main/static/correct.mp3"
WRONG_URL   = "https://github.com/trpv1/square-root-app/raw/main/static/wrong.mp3"
RESULT1_URL = "https://github.com/trpv1/square-root-app/raw/main/static/result_1.mp3"
RESULT2_URL = "https://github.com/trpv1/square-root-app/raw/main/static/result_2.mp3"

def play_sound(url: str):
    st.markdown(
        f"<audio autoplay style='display:none'><source src='{url}' type='audio/mpeg'></audio>",
        unsafe_allow_html=True,
    )

# === セッション初期化 ===
def init_state():
    defaults = dict(
        nickname="", started=False, start_time=None,
        score=0, total=0, current_problem=None,
        answered=False, is_correct=None, user_choice="",
        saved=False, played_name=False,
    )
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
init_state()

# === 問題生成 ===
def make_problem():
    a = random.randint(2, 200)
    for i in range(int(math.sqrt(a)), 0, -1):
        if a % (i * i) == 0:
            outer, inner = i, a // (i * i)
            correct = str(outer) if inner == 1 else (f"√{inner}" if outer == 1 else f"{outer}√{inner}")
            return a, correct, generate_choices(correct)

# 10択の選択肢生成
def generate_choices(correct):
    s = {correct}
    while len(s) < 10:
        o = random.randint(1, 9)
        inn = random.randint(1, 50)
        fake = str(o) if inn == 1 else (f"√{inn}" if o == 1 else f"{o}√{inn}")
        s.add(fake)
    return list(s)

# === スコア保存／取得 ===
def save_score(name, score):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([name, score, ts])
def top3():
    rec = sheet.get_all_records()
    return sorted(rec, key=lambda x: x["score"], reverse=True)[:3]

# === ニックネーム入力 ===
if not st.session_state.played_name:
    play_sound(NAME_URL)
    st.session_state.played_name = True
if st.session_state.nickname == "":
    st.title("平方根 1分クイズ")
    nick = st.text_input("ニックネームを入力してください", max_chars=12)
    if st.button("決定") and nick.strip():
        st.session_state.nickname = nick.strip()
    st.stop()

# === スタート前画面 ===
if not st.session_state.started:
    st.title(f"{st.session_state.nickname} さんの平方根クイズ")
    st.write("**ルール**: 制限時間1分、正解+1点、不正解-1点、10択で挑戦！")
    if st.button("スタート！"):
        play_sound(START_URL)
        st.session_state.started = True
        st.session_state.start_time = time.time()
        st.session_state.current_problem = make_problem()
    st.stop()

# === タイマー表示 ===
remaining = max(0, 60 - int(time.time() - st.session_state.start_time))
mm, ss = divmod(remaining, 60)
st.markdown(f"## ⏱️ {st.session_state.nickname} さんのタイムアタック！")
st.info(f"残り {mm}:{ss:02d} ｜ スコア {st.session_state.score} ｜ 挑戦 {st.session_state.total}")

# === タイムアップ＆ランキング ===
if remaining == 0:
    st.warning("⏰ タイムアップ！")
    st.write(f"最終スコア: {st.session_state.score}点 ({st.session_state.total}問)")
    if not st.session_state.saved:
        save_score(st.session_state.nickname, st.session_state.score)
        st.session_state.saved = True
        ranking = top3()
        names = [r['name'] for r in ranking]
        play_sound(RESULT1_URL if st.session_state.nickname in names else RESULT2_URL)
        st.balloons()
    st.write("### 🏆 歴代ランキング（上位3名）")
    for i, r in enumerate(top3(), 1):
        st.write(f"{i}. {r['name']} — {r['score']}点")
    if st.button("🔁 もう一度挑戦"):
        for k in list(st.session_state.keys()): del st.session_state[k]
    st.stop()

# === 問題表示 ===
a, correct, choices = st.session_state.current_problem
st.subheader(f"√{a} を簡約すると？")

# === 解答フェーズ ===
if not st.session_state.answered:
    user_choice = st.radio("選択肢を選んでください", choices)
    if st.button("解答する"):
        st.session_state.answered = True
        st.session_state.user_choice = user_choice
        st.session_state.total += 1
        if user_choice == correct:
            st.session_state.score += 1
            st.session_state.is_correct = True
            play_sound(CORRECT_URL)
        else:
            st.session_state.score -= 1
            st.session_state.is_correct = False
            play_sound(WRONG_URL)

# === 結果表示 ===
result_box = st.empty()
if st.session_state.answered:
    with result_box.container():
        if st.session_state.is_correct:
            st.success("🎉 正解！ +1点")
        else:
            st.error(f"😡 不正解！ 正解は {correct} でした —1点")
        def next_q():
            result_box.empty()
            st.session_state.current_problem = make_problem()
            st.session_state.answered = False
            st.session_state.is_correct = None
            st.session_state.user_choice = ""
        st.button("次の問題へ", on_click=next_q)
    st.stop()
