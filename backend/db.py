import os
from contextlib import contextmanager
from datetime import datetime

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "face_lock_alert")


def _server_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def _connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


@contextmanager
def get_connection():
    connection = _connection()
    try:
        yield connection
    finally:
        connection.close()


def init_db():
    server = _server_connection()
    try:
        cursor = server.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        server.commit()
        cursor.close()
    finally:
        server.close()

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                username VARCHAR(80) NOT NULL UNIQUE,
                email VARCHAR(190) NOT NULL UNIQUE,
                phone VARCHAR(20) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL
            ) ENGINE=InnoDB
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS face_samples (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT UNSIGNED NOT NULL,
                image_blob MEDIUMBLOB NOT NULL,
                created_at DATETIME NOT NULL,
                CONSTRAINT fk_face_samples_user
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE,
                INDEX idx_face_samples_user (user_id)
            ) ENGINE=InnoDB
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS face_models (
                user_id BIGINT UNSIGNED PRIMARY KEY,
                model_blob MEDIUMBLOB NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT fk_face_models_user
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS login_attempts (
                id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT UNSIGNED NULL,
                username_attempted VARCHAR(80) NOT NULL,
                success TINYINT(1) NOT NULL DEFAULT 0,
                reason VARCHAR(120) NOT NULL,
                confidence DECIMAL(10, 4) NULL,
                latitude DECIMAL(10, 7) NULL,
                longitude DECIMAL(10, 7) NULL,
                attempted_at DATETIME NOT NULL,
                image_blob MEDIUMBLOB NULL,
                CONSTRAINT fk_login_attempts_user
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE SET NULL,
                INDEX idx_login_attempts_user_time (user_id, attempted_at),
                INDEX idx_login_attempts_success (success)
            ) ENGINE=InnoDB
            """
        )

        connection.commit()
        cursor.close()


def get_user_by_id(user_id):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return row


def get_user_by_username(username):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        cursor.close()
        return row


def email_exists(email):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        cursor.close()
        return row is not None


def create_user(name, username, email, phone, password_hash, created_at):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO users (name, username, email, phone, password_hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (name, username, email, phone, password_hash, created_at),
        )
        connection.commit()
        user_id = cursor.lastrowid
        cursor.close()
        return user_id


def save_face_data(user_id, face_blobs, model_blob, saved_at):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM face_samples WHERE user_id = %s", (user_id,))

        for blob in face_blobs:
            cursor.execute(
                """
                INSERT INTO face_samples (user_id, image_blob, created_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, blob, saved_at),
            )

        cursor.execute(
            """
            INSERT INTO face_models (user_id, model_blob, updated_at)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                model_blob = VALUES(model_blob),
                updated_at = VALUES(updated_at)
            """,
            (user_id, model_blob, saved_at),
        )
        connection.commit()
        cursor.close()


def get_face_model(user_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT model_blob FROM face_models WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return bytes(row[0]) if row else None


def create_login_attempt(
    user_id,
    username_attempted,
    success,
    reason,
    confidence,
    latitude,
    longitude,
    attempted_at,
    image_blob=None,
):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO login_attempts
            (user_id, username_attempted, success, reason, confidence,
             latitude, longitude, attempted_at, image_blob)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                username_attempted,
                int(success),
                reason,
                confidence,
                latitude,
                longitude,
                attempted_at,
                image_blob,
            ),
        )
        connection.commit()
        attempt_id = cursor.lastrowid
        cursor.close()
        return attempt_id


def get_login_stats(user_id):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_attempts,
                COALESCE(SUM(success = 1), 0) AS successful_attempts,
                COALESCE(SUM(success = 0), 0) AS unsuccessful_attempts,
                MAX(CASE WHEN success = 1 THEN attempted_at END) AS last_successful_login
            FROM login_attempts
            WHERE user_id = %s
            """,
            (user_id,),
        )
        stats = cursor.fetchone()
        cursor.close()
        return stats


def get_recent_attempts(user_id, limit=20):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                id,
                success,
                reason,
                confidence,
                latitude,
                longitude,
                attempted_at,
                image_blob IS NOT NULL AS has_image
            FROM login_attempts
            WHERE user_id = %s
            ORDER BY attempted_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows


def get_attempt_image(user_id, attempt_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT image_blob
            FROM login_attempts
            WHERE id = %s AND user_id = %s AND image_blob IS NOT NULL
            """,
            (attempt_id, user_id),
        )
        row = cursor.fetchone()
        cursor.close()
        return bytes(row[0]) if row else None
