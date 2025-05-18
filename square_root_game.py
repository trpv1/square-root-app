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

# === 効果音ヘルパ ===
NAME_URL   = "https://github.com/trpv1/square-root-app/raw/main/static/name.mp3"
START_URL  = "https://github.com/trpv1/square-root-app/raw/main/static/start.mp3"
CORRECT_URL = "https://github.com/trpv1/square-root-app/raw/main/static/correct.mp3"
WRONG_URL   = "https://github.com/trpv1/square-root-app/raw/main/static/wrong.mp3"

def play_sound(url: str):
    """autoplay 音声プレイヤーを埋め込む"""
    st.markdown(
        f"""
        <audio autoplay="true" style="display:none">
            <source src="{url}" type="audio/mpeg">
        </audio>
        """,
        unsafe_allow_html=True,
    )

# === セッション初期化 ===
def init_state():
    default = dict(
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
    )
    for k, v in default.items():
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
                    fake = str(o) if inn == 1 else (f"√{inn}" if o == 1 else f"{o}√{inn}")
                    choices.add(fake)
                return a, correct, random.sample(list(choices), k=4)

# === Sheets 保存/取得 ===

def save_score(name, score):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    records = sheet.get_all_records()
    # 同名を削除
    for idx in reversed(range(len(records))):
        if records[idx]["name"] == name:
            sheet.delete_row(idx + 2)
    sheet.append_row([name, score, timestamp])

def top3():
    rec = sheet.get_all_records()
    return sorted(rec, key=lambda x: x["score"], reverse=True)[:3]

# === ニックネーム入力 ===
if st.session_state.nickname == "":
    play_sound(NAME_URL)
    st.title("平方根 1分クイズ")
    nick = st.text_input("ニックネームを入力してください", max_chars=12)
    if st.button("▶ 決定"):
        if nick.strip():
            st.session_state.nickname = nick.strip()
        else:
            st.error("名前を入力してください。")
    st.stop()

# === スタート画面 ===
if not st.session_state.started:
    st.title(f"{st.session_state.nickname} さんの平方根クイズ")
    st.write("**ルール**: 制限時間1分、正解+1点、不正解-1点、4択で挑戦！")
    if st.button("▶ スタート！"):
        play_sound(START_URL)  # スタート時効果音
        st.session_state.started = True
        st.session_state.start_time = time.time()
        st.session_state.current_problem = make_problem()
    st.stop()

# === タイマー & スコア ===
if st.session_state.start_time is None:
    st.session_state.start_time = time.time()
remaining = max(0, 60 - int(time.time() - st.session_state.start_time))
mm, ss = divmod(remaining, 60)
st.markdown(f"## ⏱️ {st.session_state.nickname} さんの1分タイムアタック！")
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
        for k in list(st.session_state.keys()):
            del st.session_state[k]
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
            play_sound(CORRECT_URL)  # 正解音
        else:
            st.session_state.score -= 1
            st.session_state.is_correct = False
            play_sound(WRONG_URL)    # 不正解音

# === 結果表示 ===
if st.session_state.answered:
    if st.session_state.is_correct:
        st.success("🎉 正解！ +1点")
    else:
        st.markdown(f"""
        <div style='padding:16px;border-radius:10px;background:#ffcccc;color:#990000;font-size:20px;animation:shake 0.5s;'>😡 不正解！ 正解は <b>{correct}</b> でした —1点</div>
        <style>
        @keyframes shake {{
          0% {{ transform: translate(1px, 1px) rotate(0); }}
          20% {{ transform: translate(-1px, -2px) rotate(-1deg); }}
          40% {{ transform: translate(-3px, 0) rotate(1deg); }}
          60% {{ transform: translate(3px, 2px) rotate(0); }}
          80% {{ transform: translate(1px, -1px) rotate(1deg); }}
          100% {{ transform: translate(-1px, 2px) rotate(-1deg); }}
        }}
        </style>
        """, unsafe_allow_html=True)

    if st.button("次の問題へ"):
        st.session_state.current_problem = make_problem()
        st.session_state.answered = False
        st.session_state.is_correct = None
        st.session_state.user_choice = ""
    st.stop()
