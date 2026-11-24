
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("signal_processing/pleth1_filtered.csv")
features = pd.read_csv("signal_processing/pleth1_artifact_windows.csv")

# Inspect 45 to 100 seconds
start_time = 45
end_time = 100

region = df[
    (df["time_seconds"] >= start_time) &
    (df["time_seconds"] <= end_time)
]

feature_region = features[
    (features["start_time"] >= start_time) &
    (features["start_time"] < end_time)
]

fig, axes = plt.subplots(2, 1, figsize=(15, 9))

# Filtered waveform
axes[0].plot(
    region["time_seconds"],
    region["pleth_1_filtered"],
    linewidth=0.6
)

axes[0].set_title("Filtered PPG: 45–100 Seconds")
axes[0].set_ylabel("Amplitude")
axes[0].grid(True)

# Window amplitude measurements
axes[1].plot(
    feature_region["start_time"],
    feature_region["peak_to_peak"],
    marker="o",
    label="Peak-to-peak amplitude"
)

for _, row in feature_region[
    feature_region["artifact_suspected"]
].iterrows():
    axes[1].axvspan(
        row["start_time"],
        row["end_time"],
        color="red",
        alpha=0.15
    )

axes[1].set_title("Amplitude Changes and Flagged Windows")
axes[1].set_xlabel("Time (seconds)")
axes[1].set_ylabel("Peak-to-peak amplitude")
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.savefig(
    "signal_processing/review_45_100_seconds.png",
    dpi=150
)
plt.show()
