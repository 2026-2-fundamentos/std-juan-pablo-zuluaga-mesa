"""Limpieza de ventas.csv con SQL (SQLite).

pandas solo se usa para leer el CSV crudo como texto y escribir el resultado;
toda la limpieza ocurre en la consulta SQL.
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd

ACTIVITY_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = ACTIVITY_DIR / "data" / "ventas.csv"
OUTPUT_FILE = ACTIVITY_DIR / "submission" / "ventas.csv"

# Tabla de proveedores: clave normalizada (mayúsculas, sin tildes, sin puntos ni
# espacios) -> nombre canónico.
SUPPLIERS_SQL = """
CREATE TABLE suppliers (key TEXT PRIMARY KEY, name TEXT);
INSERT INTO suppliers VALUES
    ('ABBCOLOMBIALTDA', 'ABB COLOMBIA LTDA.'),
    ('ALPINAPRODUCTOSALIMENTICIOS', 'ALPINA PRODUCTOS ALIMENTICIOS'),
    ('AMAZONWEBSERVICESCOLOMBIA', 'AMAZON WEB SERVICES COLOMBIA'),
    ('BANCOLOMBIASA', 'BANCOLOMBIA S.A.'),
    ('CEMENTOSARGOSSA', 'CEMENTOS ARGOS S.A.'),
    ('CLAROCOLOMBIA', 'CLARO COLOMBIA'),
    ('CORONASAS', 'CORONA S.A.S.'),
    ('ECOPETROLSA', 'ECOPETROL S.A.'),
    ('GOOGLECOLOMBIALTDA', 'GOOGLE COLOMBIA LTDA.'),
    ('GRUPOEXITOSA', 'GRUPO ÉXITO S.A.'),
    ('IBMCOLOMBIASAS', 'IBM COLOMBIA S.A.S.'),
    ('MICROSOFTCOLOMBIAINC', 'MICROSOFT COLOMBIA INC.'),
    ('NUTRESASA', 'NUTRESA S.A.'),
    ('ORACLECOLOMBIALTDA', 'ORACLE COLOMBIA LTDA.'),
    ('POSTOBONSA', 'POSTOBÓN S.A.'),
    ('SAPCOLOMBIASAS', 'SAP COLOMBIA S.A.S.'),
    ('SCHNEIDERELECTRIC', 'SCHNEIDER ELECTRIC'),
    ('SIEMENSSAS', 'SIEMENS S.A.S.'),
    ('SURASA', 'SURA S.A.'),
    ('TELEFONICACOLOMBIA', 'TELEFÓNICA COLOMBIA');
"""

CLEAN_SQL = """
WITH
-- 1. Una fila por supplier_id (se eliminan los registros duplicados).
dedup AS (
    SELECT rowid AS row_order, *
    FROM raw
    WHERE rowid IN (SELECT MIN(rowid) FROM raw GROUP BY TRIM(supplier_id))
),

-- 2. Textos normalizados que se usan en los pasos siguientes.
prep AS (
    SELECT
        row_order,
        TRIM(supplier_id) AS supplier_id,
        UPPER(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                REPLACE(REPLACE(TRIM(supplier), '.', ''), ' ', ''),
            'é', 'E'), 'É', 'E'), 'ó', 'O'), 'Ó', 'O'), 'í', 'I'), 'á', 'A')
        ) AS supplier_key,
        LOWER(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                TRIM(city),
            'Á', 'a'), 'á', 'a'), 'Í', 'i'), 'í', 'i'), 'Ó', 'o'), 'ó', 'o')
        ) AS city_key,
        TRIM(purchase_date) AS d,
        REPLACE(REPLACE(REPLACE(REPLACE(UPPER(TRIM(amount)), 'COP', ''), '$', ''), ',', ''), ' ', '')
            AS amount_txt,
        TRIM(discount) AS discount_txt,
        REPLACE(LOWER(TRIM(weight)), ',', '.') AS weight_txt,
        TRIM(units) AS units_txt,
        REPLACE(REPLACE(TRIM(unit_price), '$', ''), ',', '') AS price_txt,
        LOWER(TRIM(contact_email)) AS email_txt
    FROM dedup
),

-- 3. Conversión de cada columna a su formato final.
clean AS (
    SELECT
        row_order,
        supplier_id,
        s.name AS supplier,
        'COL' AS country,
        CASE city_key
            WHEN 'bogota' THEN 'Bogotá'
            WHEN 'medellin' THEN 'Medellín'
            WHEN 'sopo' THEN 'Sopó'
            WHEN 'tenjo' THEN 'Tenjo'
        END AS city,

        CASE
            -- yyyy/mm/dd y yyyy-mm-dd
            WHEN d GLOB '[0-9][0-9][0-9][0-9][/-][0-9][0-9][/-][0-9][0-9]'
                THEN SUBSTR(d, 1, 4) || '-' || SUBSTR(d, 6, 2) || '-' || SUBSTR(d, 9, 2)
            -- dd.mm.yyyy
            WHEN d GLOB '[0-9][0-9].[0-9][0-9].[0-9][0-9][0-9][0-9]'
                THEN SUBSTR(d, 7, 4) || '-' || SUBSTR(d, 4, 2) || '-' || SUBSTR(d, 1, 2)
            -- dd-mm-yy
            WHEN d GLOB '[0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                THEN '20' || SUBSTR(d, 7, 2) || '-' || SUBSTR(d, 4, 2) || '-' || SUBSTR(d, 1, 2)
            -- aa/bb/yyyy: dd/mm por defecto; mm/dd si el segundo número no puede ser mes
            WHEN d GLOB '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]' AND CAST(SUBSTR(d, 4, 2) AS INTEGER) > 12
                THEN SUBSTR(d, 7, 4) || '-' || SUBSTR(d, 1, 2) || '-' || SUBSTR(d, 4, 2)
            WHEN d GLOB '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]'
                THEN SUBSTR(d, 7, 4) || '-' || SUBSTR(d, 4, 2) || '-' || SUBSTR(d, 1, 2)
        END AS purchase_date,

        CASE
            WHEN amount_txt IN ('', 'N/A') THEN NULL
            WHEN amount_txt GLOB '*K'
                THEN CAST(SUBSTR(amount_txt, 1, LENGTH(amount_txt) - 1) AS REAL) * 1000
            -- el punto separa miles: 480.000, 1.250.000
            WHEN amount_txt GLOB '*.[0-9][0-9][0-9]'
                THEN CAST(REPLACE(amount_txt, '.', '') AS REAL)
            ELSE CAST(amount_txt AS REAL)
        END AS amount,

        CASE
            WHEN discount_txt IN ('', 'N/A') THEN NULL
            WHEN discount_txt GLOB '*%'
                THEN CAST(TRIM(REPLACE(discount_txt, '%', '')) AS REAL) / 100
            WHEN CAST(discount_txt AS REAL) > 1 THEN CAST(discount_txt AS REAL) / 100
            ELSE CAST(discount_txt AS REAL)
        END AS discount,

        CASE
            WHEN weight_txt IN ('', 'n/a') THEN NULL
            WHEN weight_txt GLOB '*ton' THEN CAST(TRIM(REPLACE(weight_txt, 'ton', '')) AS REAL) * 1000
            WHEN weight_txt GLOB '*kg' THEN CAST(TRIM(REPLACE(weight_txt, 'kg', '')) AS REAL)
            WHEN weight_txt GLOB '*g' THEN CAST(TRIM(REPLACE(weight_txt, 'g', '')) AS REAL) / 1000
            ELSE CAST(weight_txt AS REAL)  -- sin unidad: kilogramos
        END AS weight,

        CASE WHEN units_txt IN ('', 'N/A') THEN NULL ELSE CAST(units_txt AS INTEGER) END AS units,

        CASE
            WHEN price_txt IN ('', 'N/A') THEN NULL
            -- 980.000.00: los primeros puntos separan miles, el último es decimal
            WHEN LENGTH(price_txt) - LENGTH(REPLACE(price_txt, '.', '')) > 1
                THEN CAST(
                    REPLACE(SUBSTR(price_txt, 1, LENGTH(price_txt) - 3), '.', '')
                    || SUBSTR(price_txt, -3) AS REAL)
            ELSE CAST(price_txt AS REAL)
        END AS unit_price,

        CASE WHEN email_txt IN ('', 'n/a', 'sin correo') THEN NULL ELSE email_txt END AS contact_email
    FROM prep
    LEFT JOIN suppliers AS s ON s.key = prep.supplier_key
)

SELECT
    supplier_id, supplier, country, city, purchase_date,
    amount, discount, ROUND(weight, 4) AS weight, units, unit_price, contact_email
FROM clean
ORDER BY row_order
"""


def snake_case(name):
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def main():
    raw = pd.read_csv(INPUT_FILE, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    raw.columns = [snake_case(c) for c in raw.columns]

    with sqlite3.connect(":memory:") as conn:
        raw.to_sql("raw", conn, index=False)
        conn.executescript(SUPPLIERS_SQL)
        sales = pd.read_sql_query(CLEAN_SQL, conn)

    sales["units"] = sales["units"].astype("Int64")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    sales.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
