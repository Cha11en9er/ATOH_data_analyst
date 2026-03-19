import os
import csv

import psycopg2
from psycopg2 import sql

try:
    # попробуем подтянуть переменные из .env, если есть python-dotenv
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # если python-dotenv не установлен, просто используем переменные окружения
    pass


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "file_crawler_results.csv")


def get_conn_params():
    """Читает параметры подключения к PostgreSQL из переменных окружения / .env."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "dbname": os.getenv("POSTGRES_DB", "crawler_db"),
        "default_db": os.getenv("POSTGRES_DEFAULT_DB", "postgres"),
    }


def ensure_database_exists(params):
    """
    Создаёт БД, если она ещё не существует.

    Подключаемся к служебной БД (обычно postgres) и пытаемся выполнить CREATE DATABASE.
    Если БД уже есть, ловим DuplicateDatabase и игнорируем.
    """
    dbname = params["dbname"]
    default_db = params["default_db"]

    tmp_params = params.copy()
    tmp_params["dbname"] = default_db

    conn = psycopg2.connect(
        host=tmp_params["host"],
        port=tmp_params["port"],
        user=tmp_params["user"],
        password=tmp_params["password"],
        dbname=tmp_params["dbname"],
    )
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s;"), [dbname]
            )
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
                print(f"База данных {dbname} создана.")
            else:
                print(f"База данных {dbname} уже существует.")
    finally:
        conn.close()


def create_schema_and_table(params):
    """
    Создаёт схему и таблицу для хранения результатов краулера.

    Схема: crawler
    Таблица: files
      - id: первичный ключ
      - path: путь к файлу
      - file_type: тип файла (txt, csv, pdf, ...)
      - content: извлечённый текст
      - content_tsv: tsvector для полнотекстового поиска (GENERATED ALWAYS)
    """
    conn = psycopg2.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname=params["dbname"],
    )
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            # создаём схему, если её ещё нет
            cur.execute("CREATE SCHEMA IF NOT EXISTS crawler;")

            # создаём таблицу с tsvector-колонкой
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS crawler.files (
                    id BIGSERIAL PRIMARY KEY,
                    path TEXT NOT NULL,
                    file_type TEXT,
                    content TEXT,
                    content_tsv tsvector GENERATED ALWAYS AS (
                        to_tsvector('russian', coalesce(content, ''))
                    ) STORED
                );
                """
            )

            # индекс по tsvector для ускорения полнотекстового поиска
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_files_content_tsv
                ON crawler.files
                USING GIN (content_tsv);
                """
            )

        print("Схема crawler и таблица crawler.files готовы.")
    finally:
        conn.close()


def load_csv_into_db(params):
    """Импортирует данные из file_crawler_results.csv в таблицу crawler.files."""
    conn = psycopg2.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname=params["dbname"],
    )
    conn.autocommit = False

    try:
        with conn, conn.cursor() as cur, open(
            CSV_PATH, "r", encoding="utf-8"
        ) as f:
            reader = csv.DictReader(f)

            rows = [
                (row["Path"], row["Type"], row["Content"])
                for row in reader
            ]

            # очищаем таблицу перед загрузкой (по желанию)
            cur.execute("TRUNCATE TABLE crawler.files;")

            cur.executemany(
                """
                INSERT INTO crawler.files (path, file_type, content)
                VALUES (%s, %s, %s);
                """,
                rows,
            )

        print(f"Загружено {len(rows)} строк из {CSV_PATH} в crawler.files.")
    finally:
        conn.close()


def example_fulltext_search_query():
    """
    Пример SQL-запроса для полнотекстового поиска.

    SELECT path, file_type
    FROM crawler.files
    WHERE content_tsv @@ plainto_tsquery('russian', 'txt file');

    Здесь:
      - content_tsv — tsvector-колонка с проиндексированным текстом;
      - @@ — оператор "соответствует текстовому запросу";
      - plainto_tsquery('russian', 'txt file') — преобразует строку в запрос
        для русского морфологического словаря.
    """
    pass


def main():
    params = get_conn_params()

    ensure_database_exists(params)
    create_schema_and_table(params)
    load_csv_into_db(params)

    print(
        "\nПример полнотекстового запроса см. в функции "
        "example_fulltext_search_query() в этом файле."
    )


if __name__ == "__main__":
    main()

