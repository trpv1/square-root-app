import streamlit as st
import random, math, time, json, os

SCORE_FILE = "scores.json"

# ── 初期化関数 ──
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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ── スコアファイル読み込み／書き込み ──
def load_scores():
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_score(nickname, score):
    scores = load_scores()
    scores.append({"name": nickname, "score": score, "time": time.time()})
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:3]
    with open(SCORE_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)
    return scores

# ── 問題生成 ──
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

# ── 「ニックネーム決定」＋「スタート前画面」 両方をまとめる ──
if st.session_state.nickname == "" or not st.session_state.started:
    # ニックネーム入力
    if st.session_state.nickname == "":
        st.title("📐 平方根 1分クイズ")
        st.write("まずはニックネームを入力してください")
        nick = st.text_input("ニックネーム", max_chars=12)
        if st.button("▶ 決定"):
            if nick.strip() == "":
                st.error("名前を入力してください。")
            else:
                st.session_state.nickname = nick.strip()
        st.stop()  # ← ここで終了。以降は実行しない

    # スタート前画面
    st.title(f"📐 {st.session_state.nickname} さんの平方根 1分クイズ")
    st.markdown("""
    **ルール：**
    - 制限時間 **1分**
    - 正解で **+1点**
    - 不正解で **−1点**
    - 4択から選んで挑戦！
    """)
    if st.button("▶ スタート！"):
        st.session_state.started    = True
        st.session_state.start_time = time.time()
        st.session_state.current_problem = generate_problem()
    st.stop()  # ← ここでも必ず終了させる


# ── ガード：start_time が None の場合もセット ──
if st.session_state.start_time is None:
    st.session_state.start_time = time.time()
    if st.session_state.current_problem is None:
        st.session_state.current_problem = generate_problem()

# ── タイマー ──
TIME_LIMIT = 60
elapsed = int(time.time() - st.session_state.start_time)
remaining = max(0, TIME_LIMIT - elapsed)
m, s = divmod(remaining, 60)

st.markdown(f"## ⏱️ {st.session_state.nickname} さんの 1分タイムアタック！")
st.markdown(f"""
<div style='background:#f0f2f6;padding:8px;border-radius:8px;'>
⏳ 残り時間：<b>{m}:{s:02d}</b>　
｜　🏆 スコア：<b>{st.session_state.score}</b> 点　
｜　🔢 挑戦：<b>{st.session_state.total}</b> 問
</div>
""", unsafe_allow_html=True)

# ── 時間切れ ──
if remaining == 0:
    st.markdown("---")
    st.header("🛎️ タイムアップ！")
    st.subheader(f"{st.session_state.nickname} さんの最終スコア：{st.session_state.score}点（{st.session_state.total}問）")
    top3 = save_score(st.session_state.nickname, st.session_state.score)
    st.markdown("### 🥇 歴代ランキング（上位3名）")
    for idx, entry in enumerate(top3, start=1):
        st.write(f"{idx}. {entry['name']} — {entry['score']}点")
    if st.button("🔁 もう一度挑戦"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.stop()
    st.stop()

# ── 問題表示 ──
a, correct, choices = st.session_state.current_problem
st.markdown(f"### √{a} を簡約すると？")

# ── 解答入力 ──
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

# ── 結果表示 ──
if st.session_state.answered:
    st.markdown("---")
    if st.session_state.is_correct:
        st.success("🟢 正解！ +1点")
    else:
        st.markdown(f"""
<div style='padding:12px;border-radius:8px;
            background:#ffdddd;color:#990000;animation: shake 0.5s;'>
  <h3>😡 不正解！</h3>
  <p>正解は <b>{correct}</b> でした。<br>あなたの答え：<b>{st.session_state.user_choice}</b></p>
  <p><b>−1点</b></p>
</div>
<style>
@keyframes shake {{
  0%   {{ transform: translate(1px, 1px) rotate(0); }}
  20%  {{ transform: translate(-1px, -2px) rotate(-1deg); }}
  40%  {{ transform: translate(-3px, 0) rotate(1deg); }}
  60%  {{ transform: translate(3px, 2px) rotate(0); }}
  80%  {{ transform: translate(1px, -1px) rotate(1deg); }}
  100% {{ transform: translate(-1px, 2px) rotate(-1deg); }}
}}
</style>
""", unsafe_allow_html=True)

    if st.button("次の問題へ"):
        st.session_state.current_problem = generate_problem()
        st.session_state.answered = False
        st.session_state.is_correct = None
        st.session_state.user_choice = ""
    st.stop()
