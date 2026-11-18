import re
from pathlib import Path

import numpy as np
import pandas as pd

ACTIVITY_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = ACTIVITY_DIR / "data" / "ventas.csv"
OUTPUT_FILE = ACTIVITY_DIR / "submission" / "ventas.csv"

MISSING = {"", "N/A", "NA", "NAN", "NONE", "NULL", "SIN CORREO"}

CITIES = {
    "bogota": "Bogotá",
    "medellin": "Medellín",
    "sopo": "Sopó",
    "tenjo": "Tenjo",
}

LEGAL_SUFFIXES = [
    (r"\bS\.?A\.?S\.?$", "S.A.S."),
    (r"\bS\.?A\.?$", "S.A."),
    (r"\bLTDA\.?$", "LTDA."),
    (r"\bINC\.?$", "INC."),
]

SUPPLIER_ALIASES = {"POSTOBON S.A.": "POSTOBÓN S.A."}

WEIGHT_FACTORS ={"g": 0.001, "kg": 1.0, "ton": 1000.0}


def snake_case(name):
    name = name.strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", name).strip("_")


def strip_accents(text):
    table = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
    return text.translate(table)


def is_missing(value):
    return pd.isna(value) or str(value).strip().upper() in MISSING


def clean_supplier(value):
    text = re.sub(r"\s+", " ", str(value).strip()).upper()
    for pattern, replacement in LEGAL_SUFFIXES:
        text = re.sub(pattern, replacement, text)
    return SUPPLIER_ALIASES.get(text, text)


def clean_city(value):
    key = strip_accents(str(value).strip()).lower()
    return CITIES.get(key, str(value).strip().title())


def clean_date(value):
    text = str(value).strip()
    if m := re.fullmatch(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text):
        year, month, day = m.groups()
    elif m := re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})", text):
        first, second, year = m.groups()
        # Formato colombiano dd/mm por defecto; si el segundo valor no puede ser mes, es mm/dd.
        day, month = (second, first) if int(second) > 12 else (first, second)
        if len(year) == 2:
            year = "20" + year
    else:
        return None
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def parse_number(text):
    """Convierte cadenas con separadores de miles (',' o '.') a float."""
    text = text.replace(",", "")  # en montos y precios la coma siempre es separador de miles
    if text.count(".") > 1:
        parts = text.split(".")
        # 980.000.00 -> el último bloque de 2 dígitos es decimal; 1.250.000 -> todo miles.
        if len(parts[-1]) == 3:
            text = "".join(parts)
        else:
            text = "".join(parts[:-1]) + "." + parts[-1]
    elif re.fullmatch(r"\d{1,3}\.\d{3}", text):
        text = text.replace(".", "")
    return float(text)


def clean_amount(value):
    if is_missing(value):
        return np.nan
    text = str(value).strip().upper().replace("COP", "").replace("$", "").strip()
    multiplier = 1
    if text.endswith("K"):
        text, multiplier = text[:-1], 1000
    return parse_number(text) * multiplier


def clean_discount(value):
    if is_missing(value):
        return np.nan
    text = str(value).strip()
    if text.endswith("%"):
        return float(text[:-1]) / 100
    number = float(text)
    return number / 100 if number > 1 else number


def clean_weight(value):
    if is_missing(value):
        return np.nan
    text = str(value).strip().lower().replace(",", ".")
    m = re.fullmatch(r"([\d.]+)\s*(g|kg|ton)?", text)
    if not m:
        return np.nan
    number, unit = m.groups()
    return round(float(number) * WEIGHT_FACTORS[unit or "kg"], 4)


def clean_units(value):
    return pd.NA if is_missing(value) else int(float(str(value).strip()))


def clean_unit_price(value):
    if is_missing(value):
        return np.nan
    return parse_number(str(value).strip().replace("$", ""))


def clean_email(value):
    return np.nan if is_missing(value) else str(value).strip().lower()


def main():
    sales = pd.read_csv(INPUT_FILE, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    sales.columns = [snake_case(c) for c in sales.columns]

    sales["supplier_id"] = sales["supplier_id"].str.strip().str.zfill(4)
    sales["supplier"] = sales["supplier"].map(clean_supplier)
    sales["country"] = "COL"
    sales["city"] = sales["city"].map(clean_city)
    sales["purchase_date"] = sales["purchase_date"].map(clean_date)
    sales["amount"] = sales["amount"].map(clean_amount)
    sales["discount"] = sales["discount"].map(clean_discount)
    sales["weight"] = sales["weight"].map(clean_weight)
    sales["units"] = sales["units"].map(clean_units).astype("Int64")
    sales["unit_price"] = sales["unit_price"].map(clean_unit_price)
    sales["contact_email"] = sales["contact_email"].map(clean_email)

    sales = sales.drop_duplicates(subset="supplier_id", keep="first").reset_index(drop=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    sales.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
