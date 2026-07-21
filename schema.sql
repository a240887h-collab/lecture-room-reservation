-- ============================================================
-- 座席確保（講義室予約）schema.sql  ※班で1つに統一して共有する
-- ============================================================
-- 文字化け防止のため UTF-8 を明示する
SET NAMES utf8mb4;
ALTER DATABASE sampledb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
--   ・主キーは テーブル名_id + AUTO_INCREMENT（students は自然キー）
--   ・日付は DATE、時刻は TIME、作成日時は DATETIME
--   ・予約⇔時限の多対多は中間テーブル reservation_periods に分解
--   ・利用者（学生）は students マスタに登録（ホーム画面②で使用）
-- ============================================================

-- 作り直せるように 子→親 の順で削除
DROP TABLE IF EXISTS reservation_periods;
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS lost_items;
DROP TABLE IF EXISTS lost_item_statuses;
DROP TABLE IF EXISTS reservation_statuses;
DROP TABLE IF EXISTS periods;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS students;

-- 学生（マスタ：ホーム画面②で登録・選択）
CREATE TABLE students (
    student_no VARCHAR(20) PRIMARY KEY,              -- 学籍番号（不変で一意な自然キー）
    name       VARCHAR(50) NOT NULL,                 -- 氏名
    pin        VARCHAR(10) NOT NULL DEFAULT '0000'   -- 簡易暗証番号（任意のログイン用）
);

-- 講義室（マスタ）
CREATE TABLE rooms (
    room_id   INT         AUTO_INCREMENT PRIMARY KEY,  -- 講義室ID
    room_name VARCHAR(50) NOT NULL,                    -- 講義室名/番号
    building  VARCHAR(50),                             -- 建物
    floor     INT,                                     -- 階
    capacity  INT         NOT NULL                     -- 収容人数
);

-- 時限（マスタ）
CREATE TABLE periods (
    period_id   INT         AUTO_INCREMENT PRIMARY KEY, -- 時限ID
    period_name VARCHAR(20) NOT NULL UNIQUE,            -- 1限〜5限
    start_time  TIME        NOT NULL,                   -- 開始時刻
    end_time    TIME        NOT NULL                    -- 終了時刻
);

-- 予約ステータス（マスタ）
CREATE TABLE reservation_statuses (
    status_id   INT         AUTO_INCREMENT PRIMARY KEY, -- ステータスID
    status_name VARCHAR(20) NOT NULL UNIQUE             -- 予約済/利用済/キャンセル
);

-- 忘れ物ステータス（マスタ）
CREATE TABLE lost_item_statuses (
    status_id   INT         AUTO_INCREMENT PRIMARY KEY,
    status_name VARCHAR(20) NOT NULL UNIQUE
);

-- 予約（記録テーブル）
CREATE TABLE reservations (
    reservation_id INT          AUTO_INCREMENT PRIMARY KEY,          -- 予約ID
    room_id        INT          NOT NULL,                           -- どの講義室か(FK)
    reserved_date  DATE         NOT NULL,                           -- 予約日
    student_no     VARCHAR(20)  NOT NULL,                           -- 予約した学生(FK→students)
    reserver_name  VARCHAR(50)  NOT NULL,                           -- 予約時の氏名（表示用の控え）
    status_id      INT          NOT NULL,                           -- 予約状態(FK)
    purpose        VARCHAR(100),                                    -- 利用目的
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 作成日時
    FOREIGN KEY (room_id)    REFERENCES rooms(room_id),
    FOREIGN KEY (student_no) REFERENCES students(student_no),
    FOREIGN KEY (status_id)  REFERENCES reservation_statuses(status_id)
);

-- 予約コマ（中間テーブル：予約⇔時限の多対多を分解）
CREATE TABLE reservation_periods (
    reservation_id INT NOT NULL,                        -- どの予約に
    period_id      INT NOT NULL,                        -- どの時限を
    PRIMARY KEY (reservation_id, period_id),            -- 複合主キーで重複防止
    FOREIGN KEY (reservation_id) REFERENCES reservations(reservation_id),
    FOREIGN KEY (period_id)      REFERENCES periods(period_id)
);

-- 忘れ物（記録テーブル）
CREATE TABLE lost_items (
    lost_item_id      INT          AUTO_INCREMENT PRIMARY KEY,
    item_name         VARCHAR(100) NOT NULL,
    category          VARCHAR(50)  NOT NULL,
    found_place       VARCHAR(100) NOT NULL,
    found_date        DATE         NOT NULL,
    description       VARCHAR(255),
    finder_student_no VARCHAR(20),
    status_id         INT          NOT NULL,
    claimant_name     VARCHAR(50),
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (finder_student_no) REFERENCES students(student_no),
    FOREIGN KEY (status_id)         REFERENCES lost_item_statuses(status_id)
);

-- ============================================================
-- 初期データ（親→子 の順で入れる）
-- ============================================================
INSERT INTO students (student_no, name, pin) VALUES
    ('1244811075', '陳志遠',   '1111'),
    ('1244811033', '高橋聡太', '2222'),
    ('1244810000', '田中太郎', '3333');

INSERT INTO rooms (room_name, building, floor, capacity) VALUES
    ('3101', 'さつき', 1, 200),
    ('3102', 'さつき', 1, 60),
    ('3103', 'さつき', 1, 60),
    ('3104', 'さつき', 1, 60),
    ('3201', 'さつき', 2, 60),
    ('3202', 'さつき', 2, 90),
    ('3203', 'さつき', 2, 60),
    ('3204', 'さつき', 2, 30);

INSERT INTO periods (period_name, start_time, end_time) VALUES
    ('1限', '08:50:00', '10:30:00'), 
    ('2限', '10:40:00', '12:20:00'),
    ('3限', '13:10:00', '14:50:00'), 
    ('4限', '15:00:00', '16:40:00'),
    ('5限', '16:50:00', '18:30:00');

INSERT INTO reservation_statuses (status_name) VALUES
    ('予約済'), ('利用済'), ('キャンセル');

INSERT INTO lost_item_statuses (status_name) VALUES
    ('保管中'), ('返却済'), ('廃棄');

INSERT INTO reservations (room_id, reserved_date, student_no, reserver_name, status_id, purpose) VALUES
    (1, '2026-07-10', '1244811075', '陳志遠',   1, 'ゼミの打ち合わせ'),
    (3, '2026-07-11', '1244810000', '田中太郎', 1, '勉強会');

-- 予約1は1限と2限の連続、予約2は3限
INSERT INTO reservation_periods (reservation_id, period_id) VALUES
    (1, 1),
    (1, 2),
    (2, 3);

INSERT INTO lost_items (
    item_name, category, found_place, found_date, description, finder_student_no, status_id, claimant_name
) VALUES
    ('黒い傘', '傘', '1号館3階', '2026-07-12', '手元に白いテープあり', '1244811033', 1, NULL);
