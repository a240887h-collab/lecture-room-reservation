# pages/1_講義室_座席予約.py
# 最大3人まで同時に席を選べる講義室座席予約ページ
# データベースは使用しません。予約情報はStreamlitを終了すると消えます。

from __future__ import annotations

from datetime import date
import math
import uuid

import streamlit as st


st.set_page_config(
    page_title="講義室の席予約",
    page_icon="💺",
    layout="wide",
)

# 講義室名: (座席の合計数, 横1行に並べる席数)
ROOMS = {
    "3101": (120, 12),
    "3102": (63, 9),
    "3103": (63, 9),
    "3104": (63, 9),
    "3201": (63, 9),
    "3202": (63, 9),
    "3203": (63, 9),
    "3204": (63, 9),
}

PERIODS = {
    "1限": "08:50～10:30",
    "2限": "10:40～12:20",
    "3限": "13:10～14:50",
    "4限": "15:00～16:40",
    "5限": "16:50～18:30",
}


def create_seat_names(capacity: int, seats_per_row: int) -> list[list[str]]:
    """定員に応じて A1, A2, B1... の座席名を作る。"""
    row_count = math.ceil(capacity / seats_per_row)
    seat_rows: list[list[str]] = []
    created = 0

    for row_index in range(row_count):
        row_name = chr(ord("A") + row_index)
        row: list[str] = []

        for column_index in range(1, seats_per_row + 1):
            if created >= capacity:
                break

            row.append(f"{row_name}{column_index}")
            created += 1

        seat_rows.append(row)

    return seat_rows


def reservation_key(
    room_name: str,
    reservation_date: date,
    period_name: str,
    seat_name: str,
) -> str:
    """同じ講義室・日付・時限・席の重複予約を判定するキー。"""
    return (
        f"{room_name}|{reservation_date.isoformat()}|"
        f"{period_name}|{seat_name}"
    )


def seat_sort_key(seat_name: str) -> tuple[str, int]:
    """A1、A2、A10の順に並べるためのキー。"""
    row_name = "".join(c for c in seat_name if c.isalpha())
    column_text = "".join(c for c in seat_name if c.isdigit())
    return row_name, int(column_text)


# -----------------------------
# セッション内の一時データ
# -----------------------------
if "seat_reservations" not in st.session_state:
    st.session_state.seat_reservations = {}

if "selected_seats" not in st.session_state:
    st.session_state.selected_seats = []

if "last_condition" not in st.session_state:
    st.session_state.last_condition = None

if "flash_message" not in st.session_state:
    st.session_state.flash_message = None


st.title("💺 講義室の席予約")
st.caption("1人から最大3人まで、人数分の空席を選択して一度に予約できます。")

st.warning(
    "このページは画面だけで動作します。予約情報はブラウザを開いている間だけ保存され、"
    "Streamlitを終了すると消えます。"
)

if st.session_state.flash_message:
    st.success(st.session_state.flash_message)
    st.session_state.flash_message = None


# -----------------------------
# 1. 予約条件
# -----------------------------
st.subheader("1. 講義室・日付・時限・人数を選択")

col1, col2, col3, col4 = st.columns(4)

with col1:
    selected_room = st.selectbox("講義室", list(ROOMS.keys()))

with col2:
    selected_date = st.date_input(
        "予約日",
        value=date.today(),
        min_value=date.today(),
    )

with col3:
    selected_period = st.selectbox(
        "時限",
        list(PERIODS.keys()),
        format_func=lambda name: f"{name}（{PERIODS[name]}）",
    )

with col4:
    number_of_people = st.selectbox(
        "予約人数",
        options=[1, 2, 3],
        format_func=lambda number: f"{number}人",
    )

current_condition = (
    selected_room,
    selected_date.isoformat(),
    selected_period,
    number_of_people,
)

# 条件が変わったら選択中の席を解除
if st.session_state.last_condition != current_condition:
    st.session_state.selected_seats = []
    st.session_state.last_condition = current_condition


# -----------------------------
# 2. 座席表
# -----------------------------
capacity, seats_per_row = ROOMS[selected_room]
seat_rows = create_seat_names(capacity, seats_per_row)

st.subheader(f"2. 空いている席を{number_of_people}席選択")

st.markdown(
    """
    <div style="
        text-align:center;
        border:2px solid #888;
        border-radius:8px;
        padding:10px;
        margin:8px 0 20px 0;
        font-weight:bold;
    ">
        教卓・スクリーン
    </div>
    """,
    unsafe_allow_html=True,
)

legend1, legend2, legend3 = st.columns(3)
legend1.success("🟩 空席")
legend2.warning("🟨 選択中")
legend3.error("🟥 予約済み")

selected_count = len(st.session_state.selected_seats)
st.progress(
    selected_count / number_of_people,
    text=f"選択済み：{selected_count} / {number_of_people}席",
)

for row in seat_rows:
    columns = st.columns(len(row))

    for column, seat_name in zip(columns, row):
        key = reservation_key(
            selected_room,
            selected_date,
            selected_period,
            seat_name,
        )

        is_reserved = key in st.session_state.seat_reservations
        is_selected = seat_name in st.session_state.selected_seats

        if is_reserved:
            label = f"🟥 {seat_name}"
        elif is_selected:
            label = f"🟨 {seat_name}"
        else:
            label = f"🟩 {seat_name}"

        with column:
            if st.button(
                label,
                key=f"seat_button_{key}",
                disabled=is_reserved,
                use_container_width=True,
            ):
                if is_selected:
                    st.session_state.selected_seats.remove(seat_name)
                elif len(st.session_state.selected_seats) < number_of_people:
                    st.session_state.selected_seats.append(seat_name)
                else:
                    st.toast(
                        f"選択できるのは{number_of_people}席までです。",
                        icon="⚠️",
                    )

                st.rerun()

selected_seats = sorted(
    st.session_state.selected_seats,
    key=seat_sort_key,
)

seat_info_col, clear_col = st.columns([4, 1])

with seat_info_col:
    if selected_seats:
        st.info("選択中の席：" + "、".join(selected_seats))
    else:
        st.info("まだ席を選択していません。")

with clear_col:
    if st.button(
        "選択を解除",
        disabled=not selected_seats,
        use_container_width=True,
    ):
        st.session_state.selected_seats = []
        st.rerun()


# -----------------------------
# 3. 代表者情報
# -----------------------------
st.subheader("3. 代表者情報を入力")

form_col1, form_col2 = st.columns(2)

with form_col1:
    reserver_name = st.text_input(
        "代表者氏名",
        placeholder="例：山田 太郎",
    )

    student_number = st.text_input(
        "代表者の学籍番号",
        placeholder="例：A1234567",
    )

with form_col2:
    purpose = st.text_area(
        "利用目的",
        placeholder="例：講義の受講、ゼミ、勉強会",
        height=110,
    )


# -----------------------------
# 4. 予約確認
# -----------------------------
st.subheader("4. 予約内容を確認")

st.write(f"**講義室：** {selected_room}")
st.write(f"**予約日：** {selected_date.strftime('%Y年%m月%d日')}")
st.write(f"**時限：** {selected_period}（{PERIODS[selected_period]}）")
st.write(f"**人数：** {number_of_people}人")
st.write(
    "**座席：** "
    + ("、".join(selected_seats) if selected_seats else "未選択")
)

correct_seat_count = len(selected_seats) == number_of_people
required_fields_entered = all(
    [
        reserver_name.strip(),
        student_number.strip(),
        purpose.strip(),
    ]
)
can_reserve = correct_seat_count and required_fields_entered

if not correct_seat_count:
    st.info(f"{number_of_people}人分の席を選択してください。")

if not required_fields_entered:
    st.info("代表者氏名・学籍番号・利用目的をすべて入力してください。")

if st.button(
    f"{number_of_people}人分を予約する",
    type="primary",
    disabled=not can_reserve,
    use_container_width=True,
):
    seat_keys = [
        reservation_key(
            selected_room,
            selected_date,
            selected_period,
            seat_name,
        )
        for seat_name in selected_seats
    ]

    duplicate_seats = [
        seat_name
        for key, seat_name in zip(seat_keys, selected_seats)
        if key in st.session_state.seat_reservations
    ]

    if duplicate_seats:
        st.error(
            "次の席はすでに予約されています："
            + "、".join(duplicate_seats)
        )
    else:
        group_id = str(uuid.uuid4())

        for key, seat_name in zip(seat_keys, selected_seats):
            st.session_state.seat_reservations[key] = {
                "group_id": group_id,
                "room": selected_room,
                "date": selected_date.isoformat(),
                "period": selected_period,
                "period_time": PERIODS[selected_period],
                "seat": seat_name,
                "number_of_people": number_of_people,
                "reserver_name": reserver_name.strip(),
                "student_number": student_number.strip(),
                "purpose": purpose.strip(),
            }

        reserved_seat_text = "、".join(selected_seats)
        st.session_state.selected_seats = []
        st.session_state.flash_message = (
            f"{selected_room}教室の{reserved_seat_text}を予約しました。"
        )
        st.rerun()


# -----------------------------
# 5. 現在の予約一覧
# -----------------------------
st.divider()
st.subheader("5. 現在の講義室・日付・時限の予約一覧")

matching_reservations = [
    reservation
    for reservation in st.session_state.seat_reservations.values()
    if reservation["room"] == selected_room
    and reservation["date"] == selected_date.isoformat()
    and reservation["period"] == selected_period
]

if not matching_reservations:
    st.info("現在、この条件で登録されている予約はありません。")
else:
    # 同時予約をグループ単位にまとめる
    grouped: dict[str, list[dict]] = {}

    for reservation in matching_reservations:
        grouped.setdefault(reservation["group_id"], []).append(reservation)

    for group_id, reservations in grouped.items():
        reservations.sort(key=lambda item: seat_sort_key(item["seat"]))
        first = reservations[0]
        seats_text = "、".join(item["seat"] for item in reservations)

        info_col, cancel_col = st.columns([5, 1])

        with info_col:
            st.write(
                f"**{seats_text}**　"
                f"{first['reserver_name']}（{first['student_number']}）　"
                f"{len(reservations)}人　"
                f"目的：{first['purpose']}"
            )

        with cancel_col:
            if st.button(
                "まとめて取消",
                key=f"cancel_group_{group_id}",
                use_container_width=True,
            ):
                delete_keys = [
                    key
                    for key, reservation
                    in st.session_state.seat_reservations.items()
                    if reservation["group_id"] == group_id
                ]

                for key in delete_keys:
                    del st.session_state.seat_reservations[key]

                st.rerun()
