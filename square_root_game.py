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
sheet = client.open("ScoreBoard").sheet1  # あなたのスプレッドシート名に変更！

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
        "saved": False,  # スコア保存済フラグ
        "spoken_nickname": False,  # 音声案内済フラグ
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# === 音声でニックネーム入力案内 ===
if not st.session_state.spoken_nickname and st.session_state.nickname == "":
    # JavaScriptによる音声案内
    components.html(f"""
<script>
  var msg = new SpeechSynthesisUtterance("ニックネームを入力してください");
  msg.lang = 'ja-JP'; msg.rate = 1.0; msg.pitch = 1.0;
  window.speechSynthesis.speak(msg);
</script>
""", height=0)
    st.session_state.spoken_nickname = True

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

# === スコア保存＆重複削除 ===
def save_score(nickname, score):
    # 同じニックネームがあれば削除（上書き）
    recs = sheet.get_all_records()
    for i in reversed(range(len(recs))):
        if recs[i]['name'] == nickname:
            sheet.delete_row(i+2)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([nickname, score, timestamp])

def load_scores():
    records = sheet.get_all_records()
    sorted_records = sorted(records, key=lambda x: x['score'], reverse=True)
    return sorted_records[:3]

# === ニックネーム＆スタート画面 ===
if st.session_state.nickname == "" or not st.session_state.started:
    if st.session_state.nickname == "":
        st.title("平方根 1分クイズ")
        nick = st.text_input("ニックネームを入力", max_chars=12)
        if st.button("▶ 決定"):
            if nick.strip() == "":
                st.error("名前を入力してください。")
            else:
                st.session_state.nickname = nick.strip()
        st.stop()

    st.title(f"{st.session_state.nickname} さんの平方根 1分クイズ")
    st.markdown("**ルール**：制限時間1分、正解で+1点、間違いで-1点、4択で挑戦！")
    if st.button("▶ スタート！"):
        st.session_state.started = True
        st.session_state.start_time = time.time()
        st.session_state.current_problem = generate_problem()
    st.stop()

# === タイマー表示 ===
if st.session_state.start_time is None:
    st.session_state.start_time = time.time()
elapsed = int(time.time() - st.session_state.start_time)
remaining = max(0, 60 - elapsed)
m, s = divmod(remaining, 60)

st.markdown(f"## ⏱️ {st.session_state.nickname} さんの1分タイムアタック！")
st.markdown(
    f"<div style='background:#f0f2f6;padding:8px;border-radius:8px;'>残り時間：<b>{m}:{s:02d}</b> ｜ スコア：<b>{st.session_state.score}</b> 点 ｜ 挑戦：<b>{st.session_state.total}</b> 問</div>",
    unsafe_allow_html=True
)

# === 時間切れ処理 ===
if remaining == 0:
    st.markdown("---")
    st.markdown(f"## ⏰ タイムアップ！ {st.session_state.nickname} さんの最終スコア：{st.session_state.score}点（{st.session_state.total}問）")
    if not st.session_state.saved:
        save_score(st.session_state.nickname, st.session_state.score)
        st.session_state.saved = True

    # ランキング表示
    top3 = load_scores()
    st.markdown("### 🏆 歴代ランキング（上位3名）")
    for idx, entry in enumerate(top3, start=1):
        st.write(f"{idx}. {entry['name']} — {entry['score']}点")

    # 音声で順位発表
    rank = None
    for idx, entry in enumerate(top3, start=1):
        if entry['name'] == st.session_state.nickname:
            rank = idx
            break
    if rank:
        msg = f"{st.session_state.nickname} さんの順位は {rank} 位です。おめでとうございます！"
        pitch = 1.2
    else:
        msg = f"{st.session_state.nickname} さんの順位はランキング外です。もっと勉強しなさい！"
        pitch = 0.8
    components.html(f"""
<script>
  var msg = new SpeechSynthesisUtterance("{msg}");
  msg.lang = 'ja-JP'; msg.rate = 1.0; msg.pitch = {pitch};
  window.speechSynthesis.speak(msg);
</script>
""", height=0)

    if st.button("🔁 もう一度挑戦"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.stop()
    st.stop()

# === 問題表示 ===
a, correct, choices = st.session_state.current_problem
st.markdown(f"### √{a} を簡約すると？")

# === 回答フェーズ ===
if not st.session_state.answered:
    user_choice = st.radio("選択肢を選んでください", choices)
    if st.button("解答する"):
        st.session_state.answered = True
        st.session_state.user_choice = user_choice
        st.session_state.total += 1
        if user_choice == correct:
            st.session_state.score += 1
            st.session_state.is_correct = True
            # 正解音
            components.html("""
<audio autoplay src='https://www.soundjay.com/buttons/sounds/button-09.mp3'></audio>
""", height=0)
        else:
            st.session_state.score -= 1
            st.session_state.is_correct = False
            # 不正解音
            components.html("""
<audio autoplay src='https://www.soundjay.com/misc/sounds/fail-buzzer-01.mp3'></audio>
""", height=0)

# === 結果表示フェーズ ===
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
