import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ACTIVITY_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ACTIVITY_DIR / "data"
SUBMISSION_DIR = ACTIVITY_DIR / "submission"

QUERY = """
SELECT
    t.driver_id,
    SUM(t.hours_logged) AS hours_logged,
    SUM(t.miles_logged) AS miles_logged,
    d.name
FROM timesheet AS t
JOIN drivers AS d ON d.driver_id = t.driver_id
GROUP BY t.driver_id, d.name
ORDER BY t.driver_id
"""


def load_table(conn, filename, table):
    df = pd.read_csv(DATA_DIR / filename)
    df.columns = [c.replace("-", "_").replace("driverId", "driver_id") for c in df.columns]
    df.to_sql(table, conn, index=False)


def main():
    with sqlite3.connect(":memory:") as conn:
        load_table(conn, "drivers.csv", "drivers")
        load_table(conn, "timesheet.csv", "timesheet")
        summary = pd.read_sql_query(QUERY, conn)
        top10 = pd.read_sql_query(
            "SELECT name, miles_logged FROM (" + QUERY + ") ORDER BY miles_logged DESC LIMIT 10",
            conn,
        )

    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUBMISSION_DIR / "summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    top10.iloc[::-1].plot.barh(x="name", y="miles_logged", ax=ax, color="tab:blue", legend=False)
    ax.set_title("Top 10 conductores por millas registradas")
    ax.set_xlabel("Millas registradas")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(SUBMISSION_DIR / "top10_drivers.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
