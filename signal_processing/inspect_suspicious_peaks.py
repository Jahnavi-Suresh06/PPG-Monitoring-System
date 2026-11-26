
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("signal_processing")

df = pd.read_csv(BASE / "received_pulse_detection.csv")

windows = [
    (43.7, 45.4, "Region 1: Around 44 seconds"),
    (94.0, 97.3, "Region 2: Around 95-97 seconds"),
    (100.7, 103.8, "Region 3: Around 101-103 seconds")
]

fig, axes = plt.subplots(3, 1, figsize=(15, 12))

for ax, (start, end, title) in zip(axes, windows):

    section = df[
        (df["time_seconds"] >= start) &
        (df["time_seconds"] <= end)
    ]

    peaks = section[section["is_systolic_peak"]]
    valleys = section[section["is_valley"]]

    ax.plot(
        section["time_seconds"],
        section["ppg_filtered"],
        label="Filtered PPG"
    )

    ax.scatter(
        peaks["time_seconds"],
        peaks["ppg_filtered"],
        color="red",
        s=55,
        label="Detected peaks",
        zorder=3
    )

    ax.scatter(
        valleys["time_seconds"],
        valleys["ppg_filtered"],
        color="green",
        s=45,
        label="Detected valleys",
        zorder=3
    )

    ax.set_title(title)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Amplitude")
    ax.grid(True)
    ax.legend()

plt.tight_layout()

output = BASE / "suspicious_peak_regions.png"
plt.savefig(output, dpi=150)
plt.show()

print("Saved:", output)
