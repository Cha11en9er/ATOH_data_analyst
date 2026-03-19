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
def clean_clients(src: Path) -> tuple[pd.DataFrame, dict]:
    """Читает JSON, чистит. Возвращает (df, audit)."""
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
    return df, audit


# ─────────────────── ФУНКЦИЯ 2: transactions Excel ───────
def clean_transactions(src: Path) -> tuple[pd.DataFrame, dict, dict]:
    """Читает Excel, чистит. Возвращает (df, audit, vcounts)."""
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
    return df, audit, vcounts


def work_with_data(clients_df: pd.DataFrame, tx_df: pd.DataFrame) -> dict:
    """
    Выполняет базовый анализ очищенных транзакций и клиентов.

    Считает:
    1. Количество строк в таблицах клиентов и транзакций
    2. Топ-5 самых популярных услуг по количеству заказов
    3. Среднюю сумму транзакции по каждому городу
    4. Услугу с максимальной выручкой
    5. Долю транзакций по способам оплаты
    6. Выручку за последний месяц, который есть в данных
    """
    tx = tx_df.copy()

    transactions_count = len(tx)
    clients_count = len(clients_df)

    top_5_services = (
        tx["service"]
        .fillna("Не указано")
        .value_counts()
        .head(5)
        .rename_axis("service")
        .reset_index(name="orders_count")
    )

    average_by_city = (
        tx.groupby("city", dropna=False)["amount"]
        .mean()
        .sort_values(ascending=False)
        .reset_index(name="avg_amount")
    )

    revenue_by_service = (
        tx.groupby("service", dropna=False)["amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index(name="total_revenue")
    )
    top_service_by_revenue = revenue_by_service.head(1)

    payment_methods_percent = (
        tx["payment_method"]
        .fillna("Не указано")
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
        .rename_axis("payment_method")
        .reset_index(name="percent")
    )

    last_date = tx["transaction_date"].max()

    if pd.notna(last_date):
        last_year = last_date.year
        last_month = last_date.month
        last_month_data = tx[
            (tx["transaction_date"].dt.year == last_year)
            & (tx["transaction_date"].dt.month == last_month)
        ]
        last_month_revenue = last_month_data["amount"].sum()
    else:
        last_month_data = pd.DataFrame()
        last_month_revenue = np.nan

    return {
        "transactions_count": transactions_count,
        "clients_count": clients_count,
        "top_5_services": top_5_services,
        "average_by_city": average_by_city,
        "revenue_by_service": revenue_by_service,
        "top_service_by_revenue": top_service_by_revenue,
        "payment_methods_percent": payment_methods_percent,
        "last_month_revenue": last_month_revenue,
        "last_month_data": last_month_data,
    }


def net_worth_sort(net_worth: float) -> str:
    if pd.isna(net_worth):
        return "Капитал не указан"
    if net_worth < 100_000:
        return "Низкий капитал"
    if net_worth <= 1_000_000:
        return "Средний капитал"
    return "Высокий капитал"


def merge_data(clients_df: pd.DataFrame, tx_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged_df = pd.merge(
        tx_df,
        clients_df,
        on="client_id",
        how="left",
    )
    merged_df["net_worth_category"] = merged_df["net_worth"].apply(net_worth_sort)
    revenue_by_level = (
        merged_df.groupby("net_worth_category", dropna=False)["amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index(name="total_revenue")
    )
    return merged_df, revenue_by_level


def visualization(merged_df: pd.DataFrame, clients_df: pd.DataFrame, tx_df: pd.DataFrame) -> None:
    merged_df.info()
    clients_df.info()
    tx_df.info()

    plt.rcParams["figure.figsize"] = (10, 5)

    plt.figure()
    merged_df["amount"].plot(kind="hist", bins=50, color="skyblue", edgecolor="black")
    plt.title("Распределение сумм транзакций")
    plt.xlabel("Сумма транзакции")
    plt.ylabel("Количество таких транзакций")
    plt.show()

    plt.figure()
    revenue_by_service = (
        merged_df.groupby("service")["amount"]
        .sum()
        .sort_values(ascending=False)
    )
    revenue_by_service.plot(kind="bar", color="coral", edgecolor="black")
    plt.title("Выручка по видам услуг")
    plt.xlabel("Название услуги")
    plt.ylabel("Суммарная выручка")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()

    plt.figure()
    avg_amount_by_age = merged_df.groupby("age")["amount"].mean()
    avg_amount_by_age.plot(kind="line", marker="o", color="green")
    plt.title("Зависимость средней суммы транзакции от возраста")
    plt.xlabel("Возраст клиента (лет)")
    plt.ylabel("Средний чек (сумма транзакции)")
    plt.grid(True)
    plt.show()


def forecast_next_month(tx_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    tx = tx_df.copy()
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"], errors="coerce")
    tx = tx.dropna(subset=["transaction_date"])
    tx["month"] = tx["transaction_date"].dt.to_period("M")

    monthly_stats = (
        tx.groupby("month")
        .agg(
            transactions_count=("transaction_id", "count"),
            total_revenue=("amount", "sum"),
        )
        .reset_index()
        .sort_values("month")
    )

    if len(monthly_stats) < 2:
        return monthly_stats, {
            "message": "Недостаточно данных для прогнозирования. Нужно хотя бы 2 месяца данных."
        }

    monthly_stats["month_index"] = np.arange(len(monthly_stats))
    X = monthly_stats[["month_index"]]

    y_count = monthly_stats["transactions_count"]
    model_count = LinearRegression()
    model_count.fit(X, y_count)

    y_revenue = monthly_stats["total_revenue"]
    model_revenue = LinearRegression()
    model_revenue.fit(X, y_revenue)

    next_month_index = pd.DataFrame(
        {"month_index": [len(monthly_stats)]}
    )
    predicted_transactions = model_count.predict(next_month_index)[0]
    predicted_revenue = model_revenue.predict(next_month_index)[0]

    last_month = monthly_stats["month"].max()
    next_month = last_month + 1

    forecast_result = {
        "next_month": str(next_month),
        "predicted_transactions_count": max(0, round(predicted_transactions)),
        "predicted_revenue": round(max(0, predicted_revenue), 2),
    }

    return monthly_stats, forecast_result


def plot_forecast(monthly_stats: pd.DataFrame, forecast_result: dict) -> None:
    if "month_index" not in monthly_stats.columns:
        return

    months = monthly_stats["month"].astype(str).tolist()
    month_indices = monthly_stats["month_index"].tolist()

    next_label = forecast_result.get("next_month", "next")
    months.append(next_label)
    month_indices.append(max(month_indices) + 1)

    plt.figure(figsize=(10, 5))
    plt.plot(
        monthly_stats["month_index"],
        monthly_stats["transactions_count"],
        marker="o",
        label="Факт: кол-во транзакций",
    )
    plt.plot(
        [month_indices[-1]],
        [forecast_result.get("predicted_transactions_count", 0)],
        marker="x",
        color="red",
        label="Прогноз: кол-во транзакций",
    )
    plt.xticks(ticks=range(len(months)), labels=months, rotation=45, ha="right")
    plt.xlabel("Месяц")
    plt.ylabel("Количество транзакций")
    plt.title("Прогноз количества транзакций на следующий месяц")
    plt.legend()
    plt.tight_layout()
    plt.show()


# ─────────────────────── MAIN ────────────────────────────
def main():
    clients_df, c_audit = clean_clients(SRC / "raw_data/clients_data.json")
    tx_df, t_audit, vcounts = clean_transactions(SRC / "raw_data/transactions_data.xlsx")

    print("\n=== Аудит clients ===")
    for k, v in c_audit.items():
        print(f"{k}: {v}")

    print("\n=== Аудит transactions ===")
    for k, v in t_audit.items():
        print(f"{k}: {v}")

    print("\n=== value_counts по категориальным полям в транзакциях ===")
    for col, table_md in vcounts.items():
        print(f"\n{col}:\n{table_md}")

    analysis_results = work_with_data(clients_df, tx_df)

    print("\n=== Основной анализ ===")
    print("Количество транзакций:", analysis_results["transactions_count"])
    print("Количество клиентов:", analysis_results["clients_count"])
    print("\nТоп-5 услуг:")
    print(analysis_results["top_5_services"])
    print("\nСредняя сумма транзакции по городам:")
    print(analysis_results["average_by_city"])
    print("\nУслуга с максимальной выручкой:")
    print(analysis_results["top_service_by_revenue"])
    print("\nРаспределение способов оплаты, %:")
    print(analysis_results["payment_methods_percent"])
    print("\nВыручка за последний месяц:")
    print(analysis_results["last_month_revenue"])

    merged_df, revenue_by_level = merge_data(clients_df, tx_df)

    print("\n=== Выручка по уровням капитала ===")
    print(revenue_by_level)

    visualization(merged_df, clients_df, tx_df)

    monthly_stats, forecast_result = forecast_next_month(tx_df)

    print("\n=== Помесячная статистика ===")
    print(monthly_stats)

    print("\n=== Прогноз на следующий месяц ===")
    print(forecast_result)

    plot_forecast(monthly_stats, forecast_result)


if __name__ == "__main__":
    main()