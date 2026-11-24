
import pandas as pd
import matplotlib.pyplot as plt

signal = pd.read_csv(
    "signal_processing/pleth1_filtered.csv"
)

windows = pd.read_csv(
    "signal_processing/pleth1_artifact_windows_v3.csv"
)

# Inspect the region containing the suspicious windows
start_time = 25
end_time = 115

region = signal[
    (signal["time_seconds"] >= start_time) &
    (signal["time_seconds"] <= end_time)
]

plt.figure(figsize=(16, 6))

plt.plot(
    region["time_seconds"],
    region["pleth_1_filtered"],
    linewidth=0.8,
    label="Filtered PPG"
)

# Mark suspicious windows
flagged = windows[
    (windows["status"] != "GOOD") &
    (windows["start_time"] <= end_time) &
    (windows["end_time"] >= start_time)
]

for _, row in flagged.iterrows():

    plt.axvspan(
        max(row["start_time"], start_time),
        min(row["end_time"], end_time),
        color="orange",
        alpha=0.12
    )

plt.xlabel("Time (seconds)")
plt.ylabel("Filtered PPG amplitude")
plt.title("Filtered PPG with Version 3 Suspicious Windows")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    "signal_processing/pleth1_v3_inspection.png",
    dpi=150
)

plt.show()

print("Suspicious windows inspected:", len(flagged))
