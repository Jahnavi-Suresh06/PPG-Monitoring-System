
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from scipy.signal import butter, sosfiltfilt

# 1. Load dataset
file_path = "south/dataset/s10_sit.csv"
df = pd.read_csv(file_path)

# 2. Select only PLETH 1
df["time"] = pd.to_datetime(df["time"])
df["pleth_1"] = pd.to_numeric(df["pleth_1"], errors="coerce")

df = df.dropna(subset=["time", "pleth_1"]).reset_index(drop=True)

# 3. Extract signal and calculate sampling frequency
time_seconds = (
    df["time"] - df["time"].iloc[0]
).dt.total_seconds().to_numpy()

ppg_raw = df["pleth_1"].to_numpy(dtype=float)

time_diffs = np.diff(time_seconds)
fs = 1.0 / np.median(time_diffs)

print(f"Sampling frequency: {fs:.2f} Hz")
print(f"Total samples: {len(ppg_raw)}")
print(f"Duration: {time_seconds[-1]:.2f} seconds")

if not np.allclose(time_diffs, np.median(time_diffs),
                   rtol=0.01, atol=1e-9):
    raise ValueError(
        "Irregular timestamps detected. Inspect before filtering.")

# 4. Design Butterworth band-pass filter
low_cutoff = 0.5
high_cutoff = 8.0
filter_order = 4

sos = butter(
    filter_order,
    [low_cutoff, high_cutoff],
    btype="bandpass",
    fs=fs,
    output="sos"
)

# 5. Apply zero-phase filtering to the complete signal
ppg_filtered = sosfiltfilt(sos, ppg_raw)

# 6. Save filtered data
output = pd.DataFrame({
    "time_seconds": time_seconds,
    "pleth_1_raw": ppg_raw,
    "pleth_1_filtered": ppg_filtered
})

output.to_csv(
    "signal_processing/pleth1_filtered.csv",
    index=False
)

# 7. Compare raw and filtered waveforms
samples_to_plot = int(10 * fs)

plt.figure(figsize=(14, 8))

plt.subplot(2, 1, 1)
plt.plot(time_seconds[:samples_to_plot],
         ppg_raw[:samples_to_plot])
plt.title("Raw PPG Signal - PLETH 1")
plt.ylabel("Amplitude")
plt.grid(True)

plt.subplot(2, 1, 2)
plt.plot(time_seconds[:samples_to_plot],
         ppg_filtered[:samples_to_plot],
         color="green")
plt.title("Filtered PPG Signal - Butterworth Bandpass")
plt.xlabel("Time (seconds)")
plt.ylabel("Amplitude")
plt.grid(True)

plt.tight_layout()
plt.savefig("signal_processing/raw_vs_filtered.png", dpi=150)
plt.show()

print("Filtering completed successfully.")
print("Filtered CSV saved.")
