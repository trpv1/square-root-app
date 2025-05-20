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

# === 問題生成（重み付き＋10択＋「√そのまま」必須） ===
def make_problem():
    # ① 出現確率を上げたい a 値
    fav = {12, 18, 20, 24, 28, 32, 40, 48, 50, 54, 56, 58}

    # ② 2～100 を重み付きでサンプリング
    population = list(range(2, 101))
    weights    = [10 if n in fav else 1 for n in population]
    a = random.choices(population, weights)[0]

    # ③ √a を簡約
    for i in range(int(math.sqrt(a)), 0, -1):
        if a % (i * i) == 0:
            outer, inner = i, a // (i * i)
            correct = (
                str(outer)
                if inner == 1
                else (f"√{inner}" if outer == 1 else f"{outer}√{inner}")
            )

            # ④ 「√そのまま」も必ず選択肢に入れる
            unsimpl = f"√{a}"

            # ⑤ 10択の生成（正解＋生ルート＋ニセ解答）
            choices_set = {correct, unsimpl}
            while len(choices_set) < 10:
                o   = random.randint(1, 9)
                inn = random.randint(1, 50)
                fake = (
                    str(o)
                    if inn == 1
                    else (f"√{inn}" if o == 1 else f"{o}√{inn}")
                )
                choices_set.add(fake)

            # ⑥ ランダムに並び替えて返却
            choices = random.sample(list(choices_set), k=10)
            return a, correct, choices

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

# --- クラス選択 ---
if "class_selected" not in st.session_state:
    st.title("ユーザーネームを選択してください")

    def select_class(cls):
        st.session_state.class_selected = cls

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.button("3R1", on_click=select_class, args=("3R1",))
    with c2:
        st.button("3R2", on_click=select_class, args=("3R2",))
    with c3:
        st.button("3R3", on_click=select_class, args=("3R3",))
    with c4:
        st.button("講師", on_click=select_class, args=("講師",))

    st.stop()

# --- パスワード認証 ---
if not st.session_state.get("password_ok", False):
    st.text_input("Password：作成者の担当クラスは？", type="password", key="pw_input")

    def check_password():
        if st.session_state.pw_input == "3R3":
            st.session_state.password_ok = True
        else:
            st.error("パスワードが違います")

    st.button("確認", on_click=check_password)
    st.stop()

# --- 注意書き ---
if st.session_state.get("password_ok", False) and not st.session_state.get("agreed", False):
    st.markdown("## ⚠️ 注意事項", unsafe_allow_html=True)
    st.write("""
- **個人情報**（本名・住所・電話番号など）の入力は禁止です。  
- **1日30分以上**の継続使用はお控えください（他の勉強時間を優先しましょう）。  
- 本アプリは**初めて作成したアプリ**のため、低クオリティです。すみません。  
- エラーメッセージが出ることがありますが、**ページを更新**すると改善される場合があります。  
- 上記ルールを遵守いただけない場合は、利用を中止いたします。  
    """)

    def agree_and_continue():
        st.session_state.agreed = True

    st.button("■ 同意して次へ", on_click=agree_and_continue)
    st.stop()


# === ニックネーム入力 ===
# ① nick_input をセッションに先に初期化
if "nick_input" not in st.session_state:
    st.session_state["nick_input"] = ""

# ② 初回のみ NAME_URL を再生
if not st.session_state.played_name:
    play_sound(NAME_URL)
    st.session_state.played_name = True

# ③ ニックネーム未設定なら入力画面
if st.session_state.nickname == "":
    st.title("平方根 1分クイズ")
    # テキスト入力（nick_input キーで保存）
    st.text_input("ニックネームを入力してください", key="nick_input", max_chars=12)
    # 決定ボタンは on_click コールバックで nickname をセット
    def set_nickname():
        val = st.session_state["nick_input"].strip()
        if val:
            st.session_state["nickname"] = val

    st.button("決定", on_click=set_nickname)
    st.stop()



# === スタート前画面 ===
if not st.session_state.started:
    st.title(f"{st.session_state.nickname} さんの平方根クイズ")
    st.write("**ルール**: 制限時間1分、正解+1点、不正解-1点、10択で挑戦！")

    # on_click 用コールバックを定義
    def start_quiz():
        play_sound(START_URL)
        st.session_state.started = True
        st.session_state.start_time = time.time()
        st.session_state.current_problem = make_problem()

    # ボタン押下時に start_quiz() が呼ばれる
    st.button("スタート！", on_click=start_quiz)
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
        # 1️⃣ フルネームを生成して保存
        full_name = f"{st.session_state.class_selected}_{st.session_state.nickname}"
        save_score(full_name, st.session_state.score)

        st.session_state.saved = True
        # 2️⃣ ランキング上位かどうか判定
        ranking = top3()
        names = [r["name"] for r in ranking]
        if full_name in names:
            play_sound(RESULT1_URL)
        else:
            play_sound(RESULT2_URL)
        st.balloons()
    st.write("### 🏆 歴代ランキング（上位3名）")
    for i, r in enumerate(top3(), 1):
        st.write(f"{i}. {r['name']} — {r['score']}点")
    def restart_all():
        # セッションを完全クリア
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        # スクリプトを最初から再実行
        st.rerun()

    st.button("🔁 もう一度挑戦", on_click=restart_all)
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
