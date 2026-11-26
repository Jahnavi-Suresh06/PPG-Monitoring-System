
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("signal_processing")

df = pd.read_csv(BASE / "received_ppg_filtered.csv")
det = pd.read_csv(BASE / "received_pulse_detection.csv")

windows = [
    (43.7, 45.4, "Around 44 seconds"),
    (94.0, 97.3, "Around 95-97 seconds"),
    (100.7, 103.8, "Around 101-103 seconds")
]

fig, axes = plt.subplots(3, 1, figsize=(15, 12))

for ax, (start, end, title) in zip(axes, windows):

    section = df[
        (df["time_seconds"] >= start) &
        (df["time_seconds"] <= end)
    ]

    detected = det[
        (det["time_seconds"] >= start) &
        (det["time_seconds"] <= end) &
        (det["is_systolic_peak"])
    ]

    ax.plot(
        section["time_seconds"],
        section["ppg_raw"],
        label="Raw PPG",
        alpha=0.8
    )

    ax.plot(
        section["time_seconds"],
        section["ppg_filtered"],
        label="Filtered PPG",
        linewidth=1.5
    )

    ax.scatter(
        detected["time_seconds"],
        detected["ppg_filtered"],
        color="red",
        label="Detected peaks",
        zorder=3
    )

    ax.set_title(title)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Amplitude")
    ax.grid(True)
    ax.legend()

plt.tight_layout()

output = BASE / "raw_vs_filtered_suspicious_regions.png"
plt.savefig(output, dpi=150)
plt.show()

print("Saved:", output)
