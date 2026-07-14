# -*- coding: utf-8 -*-
# ============================================================
# カテゴリH：予約と空き状況の管理
# ・日付ごとの講義室の空き状況を確認
# ・空いている講義室・時限を予約
# ・予約一覧の確認
# ・予約のキャンセル
# ============================================================

import datetime
import pandas as pd
import streamlit as st

from db import get_connection


st.set_page_config(
    page_title="予約と空き状況の管理",
    page_icon="📅",
    layout="wide"
)

st.title("📅 予約と空き状況の管理")
st.write("講義室の空き状況を確認し、空いている時間を予約できます。")


# ============================================================
# 共通関数
# ============================================================

def fetch_all(query, params=None):
    """SELECT結果をDataFrameで返す"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        return pd.DataFrame(rows)
    finally:
        cursor.close()
        conn.close()


def get_status_id(status_name):
    """ステータス名からstatus_idを取得する"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT status_id
            FROM reservation_statuses
            WHERE status_name = %s
            """,
            (status_name,)
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return row[0]

    finally:
        cursor.close()
        conn.close()


# ============================================================
# 日付選択
# ============================================================

selected_date = st.date_input(
    "確認する日付を選択してください",
    value=datetime.date.today()
)

st.divider()


# ============================================================
# ① 空き状況
# ============================================================

st.header("① 講義室の空き状況")

rooms_df = fetch_all(
    """
    SELECT
        room_id,
        room_name,
        building,
        floor,
        capacity
    FROM rooms
    ORDER BY building, floor, room_name
    """
)

periods_df = fetch_all(
    """
    SELECT
        period_id,
        period_name,
        start_time,
        end_time
    FROM periods
    ORDER BY period_id
    """
)

reserved_df = fetch_all(
    """
    SELECT
        r.room_id,
        rp.period_id,
        rs.status_name
    FROM reservations r
    JOIN reservation_periods rp
        ON r.reservation_id = rp.reservation_id
    JOIN reservation_statuses rs
        ON r.status_id = rs.status_id
    WHERE r.reserved_date = %s
      AND rs.status_name <> 'キャンセル'
    """,
    (selected_date,)
)


if rooms_df.empty or periods_df.empty:
    st.warning("講義室または時限のデータがありません。")

else:
    availability_rows = []

    for _, room in rooms_df.iterrows():

        row = {
            "講義室": room["room_name"],
            "建物": room["building"],
            "階": room["floor"],
            "収容人数": room["capacity"]
        }

        for _, period in periods_df.iterrows():

            is_reserved = False

            if not reserved_df.empty:
                is_reserved = (
                    (
                        reserved_df["room_id"] == room["room_id"]
                    )
                    &
                    (
                        reserved_df["period_id"] == period["period_id"]
                    )
                ).any()

            if is_reserved:
                row[period["period_name"]] = "❌ 予約済"
            else:
                row[period["period_name"]] = "⭕ 空き"

        availability_rows.append(row)

    availability_df = pd.DataFrame(availability_rows)

    st.dataframe(
        availability_df,
        use_container_width=True,
        hide_index=True
    )


st.divider()


# ============================================================
# ② 新しい予約
# ============================================================

st.header("② 新しい予約")

students_df = fetch_all(
    """
    SELECT
        student_no,
        name
    FROM students
    ORDER BY student_no
    """
)


if rooms_df.empty or periods_df.empty or students_df.empty:
    st.warning("予約に必要なマスタデータが不足しています。")

else:
    student_options = {
        f"{row['student_no']}：{row['name']}":
            (row["student_no"], row["name"])
        for _, row in students_df.iterrows()
    }

    room_options = {
        f"{row['room_name']}（{row['building']}・{row['floor']}階・{row['capacity']}人）":
            row["room_id"]
        for _, row in rooms_df.iterrows()
    }

    period_options = {
        f"{row['period_name']}（{row['start_time']} ～ {row['end_time']}）":
            row["period_id"]
        for _, row in periods_df.iterrows()
    }

    with st.form("reservation_form"):

        selected_student_label = st.selectbox(
            "学生",
            list(student_options.keys())
        )

        selected_room_label = st.selectbox(
            "講義室",
            list(room_options.keys())
        )

        reservation_date = st.date_input(
            "予約日",
            value=selected_date,
            key="reservation_date"
        )

        selected_period_labels = st.multiselect(
            "予約する時限",
            list(period_options.keys())
        )

        purpose = st.text_input(
            "利用目的",
            placeholder="例：ゼミの打ち合わせ"
        )

        submitted = st.form_submit_button(
            "予約する",
            type="primary"
        )


    if submitted:

        if not selected_period_labels:
            st.error("予約する時限を1つ以上選択してください。")

        else:
            student_no, student_name = student_options[
                selected_student_label
            ]

            room_id = room_options[
                selected_room_label
            ]

            selected_period_ids = [
                period_options[label]
                for label in selected_period_labels
            ]

            conn = get_connection()
            cursor = conn.cursor()

            try:
                # ----------------------------
                # 空き状況を再確認
                # ----------------------------
                placeholders = ",".join(
                    ["%s"] * len(selected_period_ids)
                )

                check_sql = f"""
                    SELECT
                        p.period_name
                    FROM reservations r
                    JOIN reservation_periods rp
                        ON r.reservation_id = rp.reservation_id
                    JOIN periods p
                        ON rp.period_id = p.period_id
                    JOIN reservation_statuses rs
                        ON r.status_id = rs.status_id
                    WHERE r.room_id = %s
                      AND r.reserved_date = %s
                      AND rp.period_id IN ({placeholders})
                      AND rs.status_name <> 'キャンセル'
                """

                params = [
                    room_id,
                    reservation_date,
                    *selected_period_ids
                ]

                cursor.execute(check_sql, params)
                conflicts = cursor.fetchall()

                if conflicts:

                    conflict_names = [
                        row[0]
                        for row in conflicts
                    ]

                    st.error(
                        "次の時限はすでに予約されています："
                        + "、".join(conflict_names)
                    )

                else:
                    # ----------------------------
                    # 「予約済」のstatus_id取得
                    # ----------------------------
                    cursor.execute(
                        """
                        SELECT status_id
                        FROM reservation_statuses
                        WHERE status_name = %s
                        """,
                        ("予約済",)
                    )

                    status_row = cursor.fetchone()

                    if status_row is None:
                        st.error(
                            "「予約済」ステータスが見つかりません。"
                        )

                    else:
                        status_id = status_row[0]

                        # ----------------------------
                        # reservationsへ登録
                        # ----------------------------
                        cursor.execute(
                            """
                            INSERT INTO reservations
                            (
                                room_id,
                                reserved_date,
                                student_no,
                                reserver_name,
                                status_id,
                                purpose
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                room_id,
                                reservation_date,
                                student_no,
                                student_name,
                                status_id,
                                purpose
                            )
                        )

                        reservation_id = cursor.lastrowid

                        # ----------------------------
                        # reservation_periodsへ登録
                        # ----------------------------
                        for period_id in selected_period_ids:

                            cursor.execute(
                                """
                                INSERT INTO reservation_periods
                                (
                                    reservation_id,
                                    period_id
                                )
                                VALUES (%s, %s)
                                """,
                                (
                                    reservation_id,
                                    period_id
                                )
                            )

                        conn.commit()

                        st.success(
                            "予約が完了しました！"
                        )

                        st.rerun()

            except Exception as e:
                conn.rollback()

                st.error(
                    f"予約中にエラーが発生しました：{e}"
                )

            finally:
                cursor.close()
                conn.close()


st.divider()


# ============================================================
# ③ この日の予約一覧
# ============================================================

st.header("③ この日の予約一覧")

reservations_df = fetch_all(
    """
    SELECT
        r.reservation_id AS 予約ID,
        ro.room_name AS 講義室,
        ro.building AS 建物,
        GROUP_CONCAT(
            p.period_name
            ORDER BY p.period_id
            SEPARATOR '、'
        ) AS 時限,
        r.student_no AS 学籍番号,
        r.reserver_name AS 予約者,
        r.purpose AS 利用目的,
        rs.status_name AS 状態
    FROM reservations r
    JOIN rooms ro
        ON r.room_id = ro.room_id
    JOIN reservation_periods rp
        ON r.reservation_id = rp.reservation_id
    JOIN periods p
        ON rp.period_id = p.period_id
    JOIN reservation_statuses rs
        ON r.status_id = rs.status_id
    WHERE r.reserved_date = %s
    GROUP BY
        r.reservation_id,
        ro.room_name,
        ro.building,
        r.student_no,
        r.reserver_name,
        r.purpose,
        rs.status_name
    ORDER BY
        ro.room_name,
        MIN(p.period_id)
    """,
    (selected_date,)
)


if reservations_df.empty:
    st.info("この日の予約はありません。")

else:
    st.dataframe(
        reservations_df,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # ④ 予約キャンセル
    # ========================================================

    st.subheader("予約をキャンセル")

    active_reservations = reservations_df[
        reservations_df["状態"] != "キャンセル"
    ]


    if active_reservations.empty:
        st.info(
            "キャンセルできる予約はありません。"
        )

    else:
        cancel_options = {
            (
                f"予約ID {row['予約ID']}："
                f"{row['講義室']} / "
                f"{row['時限']} / "
                f"{row['予約者']}"
            ):
                row["予約ID"]
            for _, row in active_reservations.iterrows()
        }

        selected_cancel_label = st.selectbox(
            "キャンセルする予約",
            list(cancel_options.keys())
        )

        if st.button(
            "この予約をキャンセルする",
            type="secondary"
        ):

            reservation_id = cancel_options[
                selected_cancel_label
            ]

            cancel_status_id = get_status_id(
                "キャンセル"
            )

            if cancel_status_id is None:
                st.error(
                    "「キャンセル」ステータスが見つかりません。"
                )

            else:
                conn = get_connection()
                cursor = conn.cursor()

                try:
                    cursor.execute(
                        """
                        UPDATE reservations
                        SET status_id = %s
                        WHERE reservation_id = %s
                        """,
                        (
                            cancel_status_id,
                            reservation_id
                        )
                    )

                    conn.commit()

                    st.success(
                        "予約をキャンセルしました。"
                    )

                    st.rerun()

                except Exception as e:
                    conn.rollback()

                    st.error(
                        f"キャンセル中にエラーが発生しました：{e}"
                    )

                finally:
                    cursor.close()
                    conn.close()