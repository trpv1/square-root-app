import streamlit as st
import random, math, time

# ── 問題生成 ──
def generate_problem():
    while True:
        a = random.randint(2, 200)
        for i in range(int(math.sqrt(a)), 0, -1):
            if a % (i*i) == 0:
                outer, inner = i, a//(i*i)
                # 表示ルール：inner==1→「outer」、outer==1→「√inner」
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
        outer = random.randint(1,9); inner = random.randint(1,50)
        if inner == 1:
            fake = str(outer)
        elif outer == 1:
            fake = f"√{inner}"
        else:
            fake = f"{outer}√{inner}"
        s.add(fake)
    return list(s)


# ── セッション初期化 ──
if "start_time" not in st.session_state:
    st.session_state.start_time   = time.time()
    st.session_state.score        = 0
    st.session_state.current_problem = generate_problem()
    st.session_state.answered     = False
    st.session_state.is_correct   = None

# ── タイマー ──
TIME_LIMIT = 60
elapsed   = int(time.time() - st.session_state.start_time)
remaining = max(0, TIME_LIMIT - elapsed)
m, s = divmod(remaining, 60)

st.title("⏱️ 1分タイムアタック！平方根4択クイズ")
st.write(f"残り時間：**{m}:{s:02d}**　｜　スコア：**{st.session_state.score}**")

# ── 時間切れ ──
if remaining == 0:
    st.header("🛎️ タイムアップ！")
    st.subheader(f"最終スコア：{st.session_state.score}ポイント")
    if st.button("🔁 もう一度挑戦"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()
    st.stop()

# ── 現在の問題 ──
a, correct, choices = st.session_state.current_problem
st.markdown(f"## √{a} を簡約すると？")

# ── 回答フェーズ ──
if not st.session_state.answered:
    user_choice = st.radio("選択肢から選んでください", choices)
    if st.button("解答する"):
        st.session_state.answered = True
        if user_choice == correct:
            st.session_state.score += 1
            st.session_state.is_correct = True
        else:
            st.session_state.score -= 1
            st.session_state.is_correct = False

# ── 結果表示フェーズ ──
if st.session_state.answered:
    if st.session_state.is_correct:
        st.success("🟢 正解！＋1ポイント")
        # 正解時は控えめ演出なのでエフェクト省略
    else:
        st.error(f"🔴 不正解…正解は **{correct}** でした。−1ポイント")
        st.snow()  # 大演出

    # 「次の問題へ」ボタンを押すと即リセット
    if st.button("次の問題へ"):
        st.session_state.current_problem = generate_problem()
        st.session_state.answered = False
        st.session_state.is_correct = None
