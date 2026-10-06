import pandas as pd
import psycopg2
from pathlib import Path
from io import StringIO

# -----------------------------
# CONFIG
# -----------------------------

DATA_DIR = Path.home() / "Downloads" / "archive"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "olist_bi",
    "user": "postgres",
    "password": "Akshat@2027"
}

# CSV -> PostgreSQL table
TABLES = {
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv"
}

# -----------------------------
# CONNECT
# -----------------------------

conn = psycopg2.connect(**DB_CONFIG)
print("Connected to PostgreSQL!")

# -----------------------------
# LOAD EACH TABLE
# -----------------------------

for table, filename in TABLES.items():

    print(f"\nLoading {filename} → {table}")

    filepath = DATA_DIR / filename

    df = pd.read_csv(filepath)

    # Remove duplicate review IDs
    if table == "reviews":
        before = len(df)
        df = df.drop_duplicates(subset=["review_id"], keep="first")
        print(f"  Removed {before - len(df):,} duplicate reviews")

    # Convert integer-like columns to nullable integers
    integer_columns = [
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty"
    ]

    for col in integer_columns:
        if col in df.columns:
            df[col] = df[col].round().astype("Int64")

    # Convert timestamp columns
    timestamp_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
        "shipping_limit_date",
        "review_creation_date",
        "review_answer_timestamp"
    ]

    for col in timestamp_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert NaN to PostgreSQL NULL
    df = df.where(pd.notnull(df), None)

    # Convert dataframe to CSV-like buffer
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="\\N")
    buffer.seek(0)

    # Load using PostgreSQL COPY
    cursor = conn.cursor()

    cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")

    cursor.copy_expert(
        f"""
        COPY {table}
        FROM STDIN
        WITH CSV
        NULL '\\N'
        """,
        buffer
    )

    conn.commit()
    cursor.close()

    print(f"✓ {len(df):,} rows loaded")

# -----------------------------
# DONE
# -----------------------------

conn.close()

print("\n" + "=" * 50)
print("🎉 OLIST DATA LOADED SUCCESSFULLY")
print("=" * 50)