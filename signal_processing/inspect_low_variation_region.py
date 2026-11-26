
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("signal_processing")

df = pd.read_csv(BASE / "received_ppg_filtered.csv")
det = pd.read_csv(BASE / "received_pulse_detection.csv")

start, end = 85, 125

section = df[
    (df["time_seconds"] >= start) &
    (df["time_seconds"] <= end)
]

detected = det[
    (det["time_seconds"] >= start) &
    (det["time_seconds"] <= end)
]

fig, axes = plt.subplots(2, 1, figsize=(16, 9), sharex=True)

# Raw signal
axes[0].plot(
    section["time_seconds"],
    section["ppg_raw"],
    label="Raw PPG"
)
axes[0].set_title("Raw PPG: 85–125 seconds")
axes[0].set_ylabel("Amplitude")
axes[0].grid(True)
axes[0].legend()

# Filtered signal with detected peaks
axes[1].plot(
    section["time_seconds"],
    section["ppg_filtered"],
    label="Filtered PPG"
)

peaks = detected[detected["is_systolic_peak"]]

axes[1].scatter(
    peaks["time_seconds"],
    peaks["ppg_filtered"],
    color="red",
    s=35,
    label="Detected peaks"
)

axes[1].set_title("Filtered PPG and Detected Peaks")
axes[1].set_xlabel("Time (seconds)")
axes[1].set_ylabel("Amplitude")
axes[1].grid(True)
axes[1].legend()

plt.tight_layout()

output = BASE / "low_variation_region_85_125.png"
plt.savefig(output, dpi=150)

print("Saved:", output)

plt.show()
