# db.py : 班で共通のDB接続部品（接続情報はここ1か所だけに書く）
import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,          # docker-compose.yml の ports に合わせる
    "user": "student",
    "password": "student",
    "database": "sampledb",
    "charset": "utf8mb4",
    "use_unicode": True,
}

def get_connection():
    # 呼ぶたびに新しい接続を返す（使ったら close する）
    return mysql.connector.connect(**DB_CONFIG)
