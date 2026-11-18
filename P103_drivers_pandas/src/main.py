from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ACTIVITY_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ACTIVITY_DIR / "data"
SUBMISSION_DIR = ACTIVITY_DIR / "submission"


def main():
    drivers = pd.read_csv(DATA_DIR / "drivers.csv")
    timesheet = pd.read_csv(DATA_DIR / "timesheet.csv")

    summary = (
        timesheet.groupby("driverId", as_index=False)[["hours-logged", "miles-logged"]]
        .sum()
        .merge(drivers[["driverId", "name"]], on="driverId")
    )

    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUBMISSION_DIR / "summary.csv", index=False)

    top10 = summary.nlargest(10, "miles-logged").set_index("name")["miles-logged"]
    fig, ax = plt.subplots(figsize=(8, 5))
    top10.sort_values().plot.barh(ax=ax, color="tab:orange")
    ax.set_title("Top 10 conductores por millas registradas")
    ax.set_xlabel("Millas registradas")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(SUBMISSION_DIR / "top10_drivers.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
