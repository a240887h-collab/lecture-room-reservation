import streamlit as st

st.set_page_config(page_title="履修授業と教室の確認", page_icon="🏫")

subject_rooms = [
    {"授業名": "プログラミング", "教室": "A101"},
    {"授業名": "データベース", "教室": "B203"},
    {"授業名": "ネットワーク", "教室": "C105"},
    {"授業名": "AI基礎", "教室": "D301"},
]

st.title("履修授業と教室の表示")
st.write("自分が履修している授業と、対応する教室を確認できます。")

st.subheader("履修授業一覧")
st.table(subject_rooms)

selected_subject = st.selectbox(
    "確認したい授業を選んでください",
    [item["授業名"] for item in subject_rooms],
)

selected_room = next(
    item["教室"] for item in subject_rooms if item["授業名"] == selected_subject
)

st.subheader("選択結果")
st.write(f"授業名: {selected_subject}")
st.write(f"教室: {selected_room}")
