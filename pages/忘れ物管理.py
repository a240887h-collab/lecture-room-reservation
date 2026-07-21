# -*- coding: utf-8 -*-
# ============================================================
# 忘れ物管理
# ・忘れ物の一覧表示
# ・キーワード、分類、状態による検索
# ・新しい忘れ物の登録
# ・保管中、返却済、廃棄への状態変更
# ============================================================

import datetime

import pandas as pd
import streamlit as st

from db import get_connection


# ------------------------------------------------------------
# ページ設定
# ------------------------------------------------------------
st.set_page_config(
    page_title="忘れ物管理",
    page_icon="🧳",
    layout="wide"
)

st.title("🧳 忘れ物管理")
st.write("学内で見つかった忘れ物の登録・検索・状態変更ができます。")


# ============================================================
# 共通処理
# ============================================================

def fetch_dataframe(sql, params=None):
    """SELECT結果をDataFrameで返す"""

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        return pd.DataFrame(rows)

    finally:
        cursor.close()
        conn.close()


def get_status_id(status_name):
    """状態名からstatus_idを取得する"""

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT status_id
            FROM lost_item_statuses
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
# タブ
# ============================================================

list_tab, register_tab, update_tab = st.tabs(
    [
        "📋 一覧・検索",
        "➕ 忘れ物を登録",
        "🔄 状態を変更"
    ]
)


# ============================================================
# ① 一覧・検索
# ============================================================

with list_tab:

    st.header("忘れ物一覧")

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        keyword = st.text_input(
            "キーワード",
            placeholder="品名・場所・特徴から検索"
        )

    with filter_col2:
        category_filter = st.selectbox(
            "分類",
            [
                "すべて",
                "傘",
                "財布",
                "鍵",
                "スマホ・電子機器",
                "衣類",
                "文房具",
                "学生証・カード",
                "その他"
            ]
        )

    with filter_col3:
        status_filter = st.selectbox(
            "状態",
            [
                "すべて",
                "保管中",
                "返却済",
                "廃棄"
            ]
        )

    # 基本となる一覧取得SQL
    list_sql = """
        SELECT
            li.lost_item_id AS 忘れ物ID,
            li.item_name AS 品名,
            li.category AS 分類,
            li.found_place AS 発見場所,
            li.found_date AS 発見日,
            li.description AS 特徴,
            COALESCE(s.name, '未登録') AS 発見者,
            lis.status_name AS 状態,
            COALESCE(li.claimant_name, '') AS 受取人,
            li.created_at AS 登録日時
        FROM lost_items li
        JOIN lost_item_statuses lis
            ON li.status_id = lis.status_id
        LEFT JOIN students s
            ON li.finder_student_no = s.student_no
        WHERE 1 = 1
    """

    # SQLのプレースホルダへ渡す値
    list_params = []

    # キーワードが入力されている場合だけ検索条件を追加
    if keyword:
        list_sql += """
            AND (
                li.item_name LIKE %s
                OR li.found_place LIKE %s
                OR li.description LIKE %s
            )
        """

        search_keyword = f"%{keyword}%"

        list_params.extend(
            [
                search_keyword,
                search_keyword,
                search_keyword
            ]
        )

    # 「すべて」以外なら分類条件を追加
    if category_filter != "すべて":
        list_sql += " AND li.category = %s"
        list_params.append(category_filter)

    # 「すべて」以外なら状態条件を追加
    if status_filter != "すべて":
        list_sql += " AND lis.status_name = %s"
        list_params.append(status_filter)

    # 新しく見つかった順に並べる
    list_sql += """
        ORDER BY
            li.found_date DESC,
            li.lost_item_id DESC
    """

    try:
        items_df = fetch_dataframe(
            list_sql,
            tuple(list_params)
        )

        if items_df.empty:
            st.info("条件に一致する忘れ物はありません。")

        else:
            # 状態ごとの件数を表示
            metric_col1, metric_col2, metric_col3 = st.columns(3)

            with metric_col1:
                st.metric(
                    "表示件数",
                    len(items_df)
                )

            with metric_col2:
                st.metric(
                    "保管中",
                    int((items_df["状態"] == "保管中").sum())
                )

            with metric_col3:
                st.metric(
                    "返却済",
                    int((items_df["状態"] == "返却済").sum())
                )

            st.dataframe(
                items_df,
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(
            f"忘れ物一覧の取得中にエラーが発生しました：{e}"
        )


# ============================================================
# ② 忘れ物の登録
# ============================================================

with register_tab:

    st.header("新しい忘れ物を登録")

    try:
        students_df = fetch_dataframe(
            """
            SELECT
                student_no,
                name
            FROM students
            ORDER BY student_no
            """
        )

        student_options = {
            "発見者を登録しない": None
        }

        if not students_df.empty:
            for _, student in students_df.iterrows():

                label = (
                    f"{student['student_no']}："
                    f"{student['name']}"
                )

                student_options[label] = student["student_no"]

        with st.form("lost_item_register_form"):

            item_name = st.text_input(
                "品名",
                placeholder="例：黒い傘"
            )

            selected_category = st.selectbox(
                "分類",
                [
                    "傘",
                    "財布",
                    "鍵",
                    "スマホ・電子機器",
                    "衣類",
                    "文房具",
                    "学生証・カード",
                    "その他"
                ]
            )

            # 「その他」の場合は自由入力できるようにする
            other_category = ""

            if selected_category == "その他":
                other_category = st.text_input(
                    "その他の分類",
                    placeholder="分類を入力してください"
                )

            found_place = st.text_input(
                "発見場所",
                placeholder="例：1号館3階"
            )

            found_date = st.date_input(
                "発見日",
                value=datetime.date.today()
            )

            description = st.text_area(
                "特徴・説明",
                placeholder="例：持ち手に白いテープが付いている"
            )

            selected_student = st.selectbox(
                "発見者",
                list(student_options.keys())
            )

            register_submitted = st.form_submit_button(
                "忘れ物を登録する",
                type="primary"
            )

        if register_submitted:

            # 必須項目の入力確認
            if not item_name.strip():
                st.error("品名を入力してください。")

            elif not found_place.strip():
                st.error("発見場所を入力してください。")

            elif (
                selected_category == "その他"
                and not other_category.strip()
            ):
                st.error("その他の分類を入力してください。")

            else:
                # その他の場合は入力された分類を使用
                final_category = selected_category

                if selected_category == "その他":
                    final_category = other_category.strip()

                # 発見者の学籍番号を取得
                finder_student_no = student_options[
                    selected_student
                ]

                # 新規登録時は「保管中」にする
                keeping_status_id = get_status_id("保管中")

                if keeping_status_id is None:
                    st.error(
                        "「保管中」のステータスが見つかりません。"
                    )

                else:
                    conn = get_connection()
                    cursor = conn.cursor()

                    try:
                        cursor.execute(
                            """
                            INSERT INTO lost_items
                            (
                                item_name,
                                category,
                                found_place,
                                found_date,
                                description,
                                finder_student_no,
                                status_id
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                item_name.strip(),
                                final_category,
                                found_place.strip(),
                                found_date,
                                description.strip(),
                                finder_student_no,
                                keeping_status_id
                            )
                        )

                        # INSERT結果をDBへ保存
                        conn.commit()

                        st.success(
                            "忘れ物を登録しました。"
                        )

                        # 画面を読み直して一覧へ反映
                        st.rerun()

                    except Exception as e:
                        # エラー時は変更を取り消す
                        conn.rollback()

                        st.error(
                            f"登録中にエラーが発生しました：{e}"
                        )

                    finally:
                        cursor.close()
                        conn.close()

    except Exception as e:
        st.error(
            f"登録画面の準備中にエラーが発生しました：{e}"
        )


# ============================================================
# ③ 状態変更
# ============================================================

with update_tab:

    st.header("忘れ物の状態を変更")

    try:
        targets_df = fetch_dataframe(
            """
            SELECT
                li.lost_item_id,
                li.item_name,
                li.found_place,
                li.found_date,
                lis.status_name
            FROM lost_items li
            JOIN lost_item_statuses lis
                ON li.status_id = lis.status_id
            ORDER BY
                li.found_date DESC,
                li.lost_item_id DESC
            """
        )

        if targets_df.empty:
            st.info("状態を変更できる忘れ物がありません。")

        else:
            target_options = {}

            for _, item in targets_df.iterrows():

                label = (
                    f"ID {item['lost_item_id']}："
                    f"{item['item_name']} / "
                    f"{item['found_place']} / "
                    f"現在：{item['status_name']}"
                )

                target_options[label] = item["lost_item_id"]

            selected_target = st.selectbox(
                "変更する忘れ物",
                list(target_options.keys())
            )

            new_status = st.selectbox(
                "変更後の状態",
                [
                    "保管中",
                    "返却済",
                    "廃棄"
                ]
            )

            claimant_name = ""

            # 返却済の場合のみ受取人を入力
            if new_status == "返却済":
                claimant_name = st.text_input(
                    "受取人の氏名",
                    placeholder="例：田中太郎"
                )

            confirm = st.checkbox(
                "変更内容を確認しました"
            )

            if st.button(
                "状態を変更する",
                type="primary"
            ):

                if not confirm:
                    st.error(
                        "確認欄にチェックしてください。"
                    )

                elif (
                    new_status == "返却済"
                    and not claimant_name.strip()
                ):
                    st.error(
                        "返却済にする場合は受取人を入力してください。"
                    )

                else:
                    selected_status_id = get_status_id(
                        new_status
                    )

                    if selected_status_id is None:
                        st.error(
                            f"「{new_status}」のステータスがありません。"
                        )

                    else:
                        lost_item_id = target_options[
                            selected_target
                        ]

                        conn = get_connection()
                        cursor = conn.cursor()

                        try:
                            # 返却済以外なら受取人を空にする
                            final_claimant_name = None

                            if new_status == "返却済":
                                final_claimant_name = (
                                    claimant_name.strip()
                                )

                            cursor.execute(
                                """
                                UPDATE lost_items
                                SET
                                    status_id = %s,
                                    claimant_name = %s
                                WHERE lost_item_id = %s
                                """,
                                (
                                    selected_status_id,
                                    final_claimant_name,
                                    lost_item_id
                                )
                            )

                            # UPDATE結果をDBへ保存
                            conn.commit()

                            st.success(
                                "忘れ物の状態を変更しました。"
                            )

                            # 変更後の内容を表示するため再読み込み
                            st.rerun()

                        except Exception as e:
                            conn.rollback()

                            st.error(
                                f"状態変更中にエラーが発生しました：{e}"
                            )

                        finally:
                            cursor.close()
                            conn.close()

    except Exception as e:
        st.error(
            f"状態変更画面の取得中にエラーが発生しました：{e}"
        )