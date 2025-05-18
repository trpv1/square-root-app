import streamlit as st
import random, math, time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components

# === Google Sheets API 連携 ===
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)
client = gspread.authorize(creds)
sheet = client.open("ScoreBoard").sheet1  # シート名を確認してください

# === セッション初期化 ===
def init_session_state():
    defaults = {
        "nickname": "",
        "started": False,
        "start_time": None,
        "score": 0,
        "total": 0,
        "current_problem": None,
        "answered": False,
        "is_correct": None,
        "user_choice": "",
        "saved": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
init_session_state()

# === 問題生成 ===
def generate_problem():
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
                choices = generate_choices(correct)
                random.shuffle(choices)
                return a, correct, choices

def generate_choices(correct):
    s = {correct}
    while len(s) < 4:
        outer = random.randint(1, 9)
        inner = random.randint(1, 50)
        if inner == 1:
            fake = str(outer)
        elif outer == 1:
            fake = f"√{inner}"
        else:
            fake = f"{outer}√{inner}"
        s.add(fake)
    return list(s)

# === スコア保存・読み込み ===
def save_score(nickname, score):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([nickname, score, timestamp])
def load_scores():
    records = sheet.get_all_records()
    sorted_records = sorted(records, key=lambda x: x["score"], reverse=True)
    return sorted_records[:3]

# === ニックネーム入力＆スタート前画面 ===
if st.session_state.nickname == "" or not st.session_state.started:
    # ニックネーム入力画面
    if st.session_state.nickname == "":
        st.title("平方根 1分クイズ")
        # start.wav 再生
        components.html(
            """
            <script>
              // アプリのstaticフォルダから音声ファイルを再生
              new Audio('static/start.mp3').play();
            </script>
            """,
            height=0,
        )
        nick = st.text_input("ニックネームを入力", max_chars=12)
        if st.button("▶ 決定"):
            if nick.strip() == "":
                st.error("名前を入力してください。")
            else:
                st.session_state.nickname = nick.strip()
        st.stop()

    # スタート前画面
    st.title(f"{st.session_state.nickname} さんの平方根クイズ")
    st.markdown("**ルール**: 制限時間1分、正解+1点、不正解-1点。4択で挑戦！")
    if st.button("▶ スタート！"):
        st.session_state.started = True
        st.session_state.start_time = time.time()
        st.session_state.current_problem = generate_problem()
    st.stop()

# === タイマー表示 ===
if st.session_state.start_time is None:
    st.session_state.start_time = time.time()
elapsed = int(time.time() - st.session_state.start_time)
remaining = max(0, 10 - elapsed)
m, s = divmod(remaining, 10)
st.markdown(f"## ⏱️ {st.session_state.nickname} さんの1分タイムアタック！")
st.markdown(
    f"<div style='background:#f0f2f6;padding:8px;border-radius:8px;'>残り時間：<b>{m}:{s:02d}</b> ｜ スコア：<b>{st.session_state.score}</b>点 ｜ 挑戦：<b>{st.session_state.total}</b>問</div>",
    unsafe_allow_html=True,
)

# === 時間切れ処理 ===
if remaining == 0:
    st.markdown("---")
    st.markdown("## ⏰ タイムアップ！")
    st.markdown(f"**最終スコア：{st.session_state.score}点（{st.session_state.total}問）**")
    if not st.session_state.saved:
        save_score(st.session_state.nickname, st.session_state.score)
        st.session_state.saved = True
    top3 = load_scores()
    st.markdown("### 🏆 歴代ランキング（上位3名）")
    for idx, entry in enumerate(top3, start=1):
        st.write(f"{idx}. {entry['name']} — {entry['score']}点")
    if st.button("🔁 もう一度挑戦"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.stop()
    st.stop()

# === 問題表示 ===
a, correct, choices = st.session_state.current_problem
st.markdown(f"### √{a} を簡約すると？")

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
        else:
            st.session_state.score -= 1
            st.session_state.is_correct = False

# === 結果表示 ===
if st.session_state.answered:
    st.markdown("---")
    if st.session_state.is_correct:
        st.success("正解！ +1点")
    else:
        st.error(f"不正解！ 正解は {correct} でした。−1点")
    if st.button("次の問題へ"):
        st.session_state.current_problem = generate_problem()
        st.session_state.answered = False
        st.session_state.is_correct = None
        st.session_state.user_choice = ""
    st.stop()
