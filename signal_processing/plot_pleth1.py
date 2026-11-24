
import pandas as pd
import matplotlib.pyplot as plt

# Load teammate's dataset
file_path = "south/dataset/s10_sit.csv"
df = pd.read_csv(file_path)

# Select only PLETH 1
df["time"] = pd.to_datetime(df["time"])

# Convert timestamps into elapsed seconds
time_seconds = (
    df["time"] - df["time"].iloc[0]
).dt.total_seconds()

ppg_signal = df["pleth_1"]

# Plot first 10 seconds
sampling_frequency = 500
samples_to_plot = 10 * sampling_frequency

plt.figure(figsize=(14, 5))

plt.plot(
    time_seconds.iloc[:samples_to_plot],
    ppg_signal.iloc[:samples_to_plot],
    linewidth=1
)

plt.title("Raw PPG Signal - PLETH 1")
plt.xlabel("Time (seconds)")
plt.ylabel("PPG Amplitude")
plt.grid(True)
plt.tight_layout()

plt.show()
