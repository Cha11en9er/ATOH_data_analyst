#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Очистка данных: clients_data.json + transactions_data.xlsx
Исходные файлы не изменяются. Результат → папка clean_output/
"""
import json
import re
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

import numpy as np
import pandas as pd

# ─────────────────────── КОНСТАНТЫ ───────────────────────
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
ALLOWED_GENDERS = {"Женщина", "Мужчина"}
MISSING_ID      = "НЕУКАЗАННЫЙ_ID"
DATE_FMT        = "%Y-%m-%d %H:%M:%S"
DATE_MIN        = pd.Timestamp("2000-01-01")
DATE_MAX        = pd.Timestamp("2035-12-31")

SRC = Path(".")
OUT = Path("clean_data")
OUT.mkdir(exist_ok=True)


# ─────────────────────── УТИЛИТЫ ─────────────────────────
def is_valid_uuid(value) -> bool:
    """True, если значение соответствует формату UUID."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return False
    return bool(UUID_RE.fullmatch(str(value).strip()))


def normalize_id(value) -> str:
    """Корректный UUID → нижний регистр; иначе → плейсхолдер."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return MISSING_ID
    s = str(value).strip()
    return s.lower() if UUID_RE.fullmatch(s) else MISSING_ID


def parse_amount(value) -> float:
    """
    '12345,6789' или '12345.6789' → 12345.6789
    Пусто, буквы, отрицательное → NaN
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    s = str(value).strip().replace("\xa0", "").replace(" ", "")
    if not s or s.lower() == "nan":
        return np.nan
    # Разрешаем как запятую, так и точку в качестве разделителя
    if not re.fullmatch(r"\d+(?:[.,]\d+)?", s):
        return np.nan
    val = float(s.replace(",", "."))
    return val if val >= 0 else np.nan


def vc_table(series: pd.Series, col: str) -> str:
    """value_counts → Markdown-таблица."""
    vc = series.fillna("<пусто>").value_counts(dropna=False).sort_values(ascending=False)
    rows = [f"| {col} | Кол-во |", "| --- | ---: |"]
    for v, c in vc.items():
        rows.append(f"| {v} | {c} |")
    return "\n".join(rows)


def dump_json(df: pd.DataFrame, path: Path) -> None:
    # Гарантируем существование директории перед записью файла
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


# ─────────────────── ФУНКЦИЯ 1: clients JSON ─────────────
def clean_clients(src: Path, dst: Path) -> tuple[pd.DataFrame, dict]:
    """Читает JSON, чистит, сохраняет. Возвращает (df, audit)."""
    df = pd.read_json(src)

    # 1. Переименование: id → client_id  (фиксируется в MD-отчёте)
    if "id" in df.columns and "client_id" not in df.columns:
        df = df.rename(columns={"id": "client_id"})

    audit = {"исходных_строк": len(df)}

    # 2. client_id — UUID-проверка; пустые/битые → плейсхолдер
    bad_id = ~df["client_id"].apply(is_valid_uuid)
    audit["client_id_→_плейсхолдер"] = int(bad_id.sum())
    df["client_id"] = df["client_id"].apply(normalize_id)

    # 3. Дубликаты client_id (keep first)
    before = len(df)
    df = df.drop_duplicates(subset="client_id", keep="first").reset_index(drop=True)
    audit["дубликатов_client_id_удалено"] = before - len(df)

    # 4. age: числовое, ≥ 0, округление до 2 знаков
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    neg = df["age"] < 0
    audit["age_отрицательных_→_NaN"] = int(neg.sum())
    df.loc[neg, "age"] = np.nan
    audit["age_пропусков_итого"] = int(df["age"].isna().sum())
    df["age"] = df["age"].round(2)

    # 5. gender: только 2 допустимых значения
    invalid_g = df["gender"].notna() & ~df["gender"].isin(ALLOWED_GENDERS)
    audit["gender_некорректных_→_NaN"] = int(invalid_g.sum())
    df.loc[invalid_g, "gender"] = np.nan
    audit["gender_пропусков_итого"] = int(df["gender"].isna().sum())

    # 6. net_worth: числовое, ≥ 0, округление до 3 знаков
    df["net_worth"] = pd.to_numeric(df["net_worth"], errors="coerce")
    neg_nw = df["net_worth"] < 0
    audit["net_worth_отрицательных_→_NaN"] = int(neg_nw.sum())
    df.loc[neg_nw, "net_worth"] = np.nan
    audit["net_worth_пропусков_итого"] = int(df["net_worth"].isna().sum())
    df["net_worth"] = df["net_worth"].round(3)

    audit["итоговых_строк"] = len(df)
    dump_json(df, dst)
    return df, audit


# ─────────────────── ФУНКЦИЯ 2: transactions Excel ───────
def clean_transactions(src: Path, dst: Path) -> tuple[pd.DataFrame, dict, dict]:
    """Читает Excel, чистит, сохраняет. Возвращает (df, audit, vcounts)."""
    df = pd.read_excel(src, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    # Нормализуем строки: убираем лишние пробелы, пустые → NaN
    df = df.apply(lambda col: col.str.strip() if col.dtype == object else col)
    df = df.replace({"": np.nan, "nan": np.nan})

    audit  = {"исходных_строк": len(df)}
    vcounts = {}

    # ── transaction_id: невалидный UUID → УДАЛИТЬ строку ──
    valid_tid = df["transaction_id"].apply(is_valid_uuid)
    audit["transaction_id_невалидных_УДАЛЕНО"] = int((~valid_tid).sum())
    df = df[valid_tid].copy()

    dup_tid = df["transaction_id"].duplicated(keep="first")
    audit["transaction_id_дубликатов_УДАЛЕНО"] = int(dup_tid.sum())
    df = df[~dup_tid].copy()

    # ── client_id: пусто/невалидно → плейсхолдер ──
    df["client_id"] = df["client_id"].apply(normalize_id)
    audit["client_id_плейсхолдеров"] = int((df["client_id"] == MISSING_ID).sum())

    # ── transaction_date: пусто/плохой формат/вне диапазона → УДАЛИТЬ строку ──
    parsed = pd.to_datetime(df["transaction_date"], format=DATE_FMT, errors="coerce")

    bad_fmt = parsed.isna()
    audit["transaction_date_плохой_формат_УДАЛЕНО"] = int(bad_fmt.sum())
    df = df[~bad_fmt].copy()
    parsed = parsed[~bad_fmt]

    out_rng = ~parsed.between(DATE_MIN, DATE_MAX)
    audit["transaction_date_вне_диапазона_УДАЛЕНО"] = int(out_rng.sum())
    df = df[~out_rng].copy()
    parsed = parsed[~out_rng]

    # Храним дату как datetime64[ns], чтобы можно было использовать .dt
    df["transaction_date"] = parsed

    # ── amount: пусто/буквы/отрицательное → NaN (строка остаётся) ──
    df["amount"] = df["amount"].apply(parse_amount)
    audit["amount_пропусков_или_аномальных"] = int(df["amount"].isna().sum())

    # ── Категориальные поля: считаем, не удаляем ──
    for col in ["service", "payment_method", "city", "consultant"]:
        audit[f"{col}_пропусков"] = int(df[col].isna().sum())
        vcounts[col] = vc_table(df[col], col)

    df = df.reset_index(drop=True)
    audit["итоговых_строк"] = len(df)

    dump_json(df, dst)
    return df, audit, vcounts


def work_with_data(clients_df: pd.DataFrame, tx_df: pd.DataFrame):
    print('transactions data len:', len(tx_df))
    print('clients data len:', len(clients_df))
    # print(tx_df.info())
    top_5_services = tx_df["service"].value_counts().head(5)
    # print(top_5_services)

    average_by_city = tx_df.groupby('city')['amount'].mean()
    # print(average_by_city)

    best_service = tx_df.groupby('service')['amount'].sum()
    top_best_service = best_service.sort_values(ascending=False).head(1)
    # print(top_best_service)

    payment_methods_percent = tx_df['payment_method'].value_counts(normalize=True)
    # print(payment_methods_percent.round(2).astype(str) + '%', '\n')

    last_date = tx_df['transaction_date'].max()
    last_month_data = tx_df[(tx_df['transaction_date'].dt.year == last_date.year) & (tx_df['transaction_date'].dt.month == last_date.month)]

    last_month_revenue = last_month_data['amount'].sum()
    # print(f'Выручка за последний месяц: {last_month_revenue:.2f}')

def net_worth_sort(net_worth: float):
    if net_worth < 100000:
        return 'Низкий капитал'
    elif net_worth > 1000000:
        return 'Высокий капитал'
    else:
        return 'Средний капитал'

def merge_data(clients_df: pd.DataFrame, tx_df: pd.DataFrame):
    merged_df = pd.merge(clients_df, tx_df, on='client_id', how='left')

    merged_df['net_worth_category'] = merged_df['net_worth'].apply(net_worth_sort)

    revenue_by_level = merged_df.groupby('net_worth_category')['amount'].sum().sort_values(ascending=False)

    return merged_df
    # print(revenue_by_level)

def vizualization(merged_df: pd.DataFrame, clients_df: pd.DataFrame, tx_df: pd.DataFrame):
    print(merged_df.info())
    print(clients_df.info())
    print(tx_df.info())


        # --- Настройка внешнего вида (опционально) ---
    # Делаем графики чуть крупнее по умолчанию
    plt.rcParams["figure.figsize"] = (10, 5) 

    # =====================================================================
    # График 1: Построить распределение сумм транзакций
    # =====================================================================
    plt.figure() # Создаем новый пустой график

    # Используем гистограмму (hist), она лучше всего показывает распределение.
    # bins=50 означает, что мы разобьем все суммы на 50 столбиков.
    merged_df['amount'].plot(kind='hist', bins=50, color='skyblue', edgecolor='black')

    # Добавляем подписи, чтобы было понятно, что нарисовано
    plt.title('Распределение сумм транзакций')
    plt.xlabel('Сумма транзакции')
    plt.ylabel('Количество таких транзакций')

    plt.show() # Выводим график на экран


    # =====================================================================
    # График 2: Создать диаграмму выручки по услугам
    # =====================================================================
    plt.figure()

    # Сначала группируем данные: берем колонку 'service', суммируем 'amount' 
    # и сразу сортируем по убыванию, чтобы график был красивым
    revenue_by_service = merged_df.groupby('service')['amount'].sum().sort_values(ascending=False)

    # Строим столбчатую диаграмму (bar)
    revenue_by_service.plot(kind='bar', color='coral', edgecolor='black')

    plt.title('Выручка по видам услуг')
    plt.xlabel('Название услуги')
    plt.ylabel('Суммарная выручка')

    # Поворачиваем названия услуг по оси X на 45 градусов, чтобы текст не слипался
    plt.xticks(rotation=45, ha='right') 
    plt.tight_layout() # Эта команда автоматически подгоняет отступы, чтобы текст не обрезался

    plt.show()


    # =====================================================================
    # График 3: Зависимость средней суммы транзакции от возраста клиентов
    # =====================================================================
    plt.figure()

    # Группируем по возрасту ('age') и считаем СРЕДНЮЮ сумму ('mean')
    avg_amount_by_age = merged_df.groupby('age')['amount'].mean()

    # Строим обычный линейный график (line). 
    # marker='o' добавит точки на изгибах линии для каждого возраста.
    avg_amount_by_age.plot(kind='line', marker='o', color='green')

    plt.title('Зависимость средней суммы транзакции от возраста')
    plt.xlabel('Возраст клиента (лет)')
    plt.ylabel('Средний чек (сумма транзакции)')
    plt.grid(True) # Включаем сетку на фоне для удобства чтения значений

    plt.show()

# ─────────────────────── MAIN ────────────────────────────
def main():
    clients_df, c_audit = clean_clients(
        src=SRC / "raw_data/clients_data.json",
        dst=OUT / "clients_clean.json",
    )
    tx_df, t_audit, vcounts = clean_transactions(
        src=SRC / "raw_data/transactions_data.xlsx",
        dst=OUT / "transactions_clean.json",
    )

    print(f"\nГотово! Результаты в: {OUT.resolve()}")
    print(f"  clients_clean.json      — {len(clients_df)} строк")
    print(f"  transactions_clean.json — {len(tx_df)} строк")

    work_with_data(clients_df, tx_df)
    merge_data(clients_df, tx_df)
    vizualization(merge_data(clients_df, tx_df), clients_df, tx_df)

if __name__ == "__main__":
    main()