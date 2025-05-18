import streamlit as st
import random, math, time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets API 連携 ===
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)
client = gspread.authorize(creds)
sheet = client.open("ScoreBoard").sheet1  # スプレッドシート名を合わせる

# === 効果音 URL ===
NAME_URL    = "https://github.com/trpv1/square-root-app/raw/main/static/name.mp3"
START_URL   = "https://github.com/trpv1/square-root-app/raw/main/static/start.mp3"
CORRECT_URL = "https://github.com/trpv1/square-root-app/raw/main/static/correct.mp3"
WRONG_URL   = "https://github.com/trpv1/square-root-app/raw/main/static/wrong.mp3"

# === 効果音再生ヘルパ ===
def play_sound(url: str):
    st.markdown(
        f"<audio autoplay='true' style='display:none'><source src='{url}' type='audio/mpeg'></audio>",
        unsafe_allow_html=True,
    )

# === セッション初期化 ===
def init_state():
    defaults = dict(
        nickname="",
        started=False,
        start_time=None,
        score=0,
        total=0,
        current_problem=None,
        answered=False,
        is_correct=None,
        user_choice="",
        saved=False,
        played_name=False,
    )
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
init_state()

# === 問題生成 ===
def make_problem():
    while True:
        a = random.randint(2, 200)
        for i in range(int(math.sqrt(a)), 0, -1):
            if a % (i * i) == 0:
                outer, inner = i, a // (i * i)
                if inner == 1:
                    correct = str(outer)
                elif outer == 1:
                    correct = f"√{inner}"
                else:
                    correct = f"{outer}√{inner}"
                choices = {correct}
                while len(choices) < 4:
                    o = random.randint(1, 9)
                    inn = random.randint(1, 50)
                    fake = (str(o) if inn == 1 else
                           (f"√{inn}" if o == 1 else f"{o}√{inn}"))
                    choices.add(fake)
                return a, correct, random.sample(list(choices), k=4)

# === 保存/取得関数 ===
def save_score(name, score):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    records = sheet.get_all_records()
    for idx in reversed(range(len(records))):
        if records[idx]["name"] == name:
            sheet.delete_rows(idx + 2)
    sheet.append_row([name, score, timestamp])
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
    if st.button("▶ 決定") and nick.strip():
        st.session_state.nickname = nick.strip()
    st.stop()

# === スタート画面 ===
if not st.session_state.started:
    st.title(f"{st.session_state.nickname} さんの平方根クイズ")
    st.write("**ルール**: 制限時間1分、正解+1点、不正解-1点、4択で挑戦！")
    if st.button("▶ スタート！"):
        play_sound(START_URL)
        st.session_state.started = True
        st.session_state.start_time = time.time()
        st.session_state.current_problem = make_problem()
    st.stop()

# === タイマー & スコア ===
remaining = max(0, 60 - int(time.time() - st.session_state.start_time))
mm, ss = divmod(remaining, 60)
st.markdown(f"## ⏱️ {st.session_state.nickname} さんのタイムアタック！")
st.info(f"残り {mm}:{ss:02d} ｜ スコア {st.session_state.score} ｜ 挑戦 {st.session_state.total}")

# === タイムアップ ===
if remaining == 0:
    st.warning("⏰ タイムアップ！")
    st.write(f"最終スコア: {st.session_state.score}点 ({st.session_state.total}問)")
    if not st.session_state.saved:
        save_score(st.session_state.nickname, st.session_state.score)
        st.session_state.saved = True
    st.write("### 🏆 ランキング（上位3名）")
    for i, r in enumerate(top3(), 1):
        st.write(f"{i}. {r['name']} — {r['score']}点")
    if st.button("🔁 もう一度挑戦"):
        # ニックネーム保持, ほかリセット
        nickname = st.session_state.nickname
        played_name = st.session_state.played_name
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.session_state.nickname = nickname
        st.session_state.played_name = played_name
    st.stop()

# === 問題表示 ===
a, correct, choices = st.session_state.current_problem
st.subheader(f"√{a} を簡約すると？")

# === 回答入力 ===
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

# ------------------------------
# 1️⃣ 先に結果プレースホルダを用意
result_box = st.empty()

# ------------------------------
# 2️⃣ 結果描画
if st.session_state.answered:
    with result_box.container():
        msg = "🎉 正解！ +1点" if st.session_state.is_correct else f"😡 不正解！ 正解は {correct}"
        st.write(msg)

        # 3️⃣ 「次の問題へ」ボタン (callback)
        def next_q():
            # 3-1 即 HTML を消す
            result_box.empty()
            # 3-2 状態リセット
            st.session_state.current_problem = make_problem()
            st.session_state.answered = False
            st.session_state.is_correct = None
            st.session_state.user_choice = ""
            # 3-3 即 rerun
            st.rerun()

        st.button("次の問題へ", on_click=next_q, key="next_btn")

    # 4️⃣ 以下のコードは描画されない
    st.stop()


