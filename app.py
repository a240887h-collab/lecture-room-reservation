# app.py : アプリの入口（ホーム画面）
import streamlit as st

st.set_page_config(page_title="講義室予約システム", page_icon="🏫")  # タブのタイトル

st.title("講義室予約システム")                 # アプリ名
st.write("学内の講義室を、時限（コマ）単位で予約するためのアプリです。")

st.subheader("困りごと")
st.write("空き講義室が分からず、予約の重複や口頭連絡のミスが起きていた。")

st.subheader("機能一覧（担当）")
st.markdown(
    "- 一覧表示：（担当者名）\n"
    "- 登録（予約）：（担当者名）\n"
    "- 検索・絞り込み：（担当者名）\n"
    "- 予約・空き管理：（担当者名）\n"
    "- 集計・グラフ：（担当者名）"
)

st.info("左のサイドバーから各機能を選んでください。")

st.subheader("登録（予約）")
if st.button("登録（予約）を開く"):
    st.switch_page("pages/kamoku_nakamura.py")
