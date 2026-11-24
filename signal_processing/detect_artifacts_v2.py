
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from scipy.signal import find_peaks

# ==========================================
# 1. LOAD FILTERED PPG DATA
# ==========================================

df = pd.read_csv("signal_processing/pleth1_filtered.csv")

time = df["time_seconds"].to_numpy()
signal = df["pleth_1_filtered"].to_numpy()

fs = 500

# Analysis settings
window_seconds = 10
step_seconds = 2

window_size = window_seconds * fs
step_size = step_seconds * fs

print("PPG ARTIFACT DETECTION - VERSION 2")
print("----------------------------------")
print("Sampling frequency:", fs, "Hz")
print("Window duration:", window_seconds, "seconds")
print("Window step:", step_seconds, "seconds")
print("Total samples:", len(signal))


# ==========================================
# 2. ANALYSE EACH WINDOW
# ==========================================

results = []

for start in range(0, len(signal) - window_size + 1, step_size):

    end = start + window_size

    segment = signal[start:end]

    start_time = time[start]
    end_time = time[end - 1]

    amplitude_range = np.ptp(segment)
    signal_std = np.std(segment)

    # Detect nearly flat signals
    is_flatline = amplitude_range < 1e-6

    # Find pulse peaks
    minimum_distance = int(0.30 * fs)

    minimum_prominence = max(
        0.25 * signal_std,
        1e-6
    )

    peaks, properties = find_peaks(
        segment,
        distance=minimum_distance,
        prominence=minimum_prominence
    )

    prominences = properties.get(
        "prominences",
        np.array([])
    )

    pulse_count = len(peaks)

    # Calculate pulse intervals
    if pulse_count >= 2:

        intervals = np.diff(peaks) / fs

        median_interval = np.median(intervals)

        estimated_hr = 60 / median_interval

        interval_cv = (
            np.std(intervals) / np.mean(intervals)
            if np.mean(intervals) > 0 else np.nan
        )

    else:

        median_interval = np.nan
        estimated_hr = np.nan
        interval_cv = np.nan

    # Calculate pulse amplitude consistency
    if len(prominences) >= 3:

        amplitude_cv = (
            np.std(prominences) / np.mean(prominences)
            if np.mean(prominences) > 0 else np.nan
        )

    else:

        amplitude_cv = np.nan

    # ======================================
    # 3. QUALITY FLAGS
    # ======================================

    reasons = []

    if is_flatline:

        status = "POOR"
        reasons.append("Flatline")

    elif pulse_count == 0:

        status = "POOR"
        reasons.append("No pulse peaks detected")

    else:

        status = "GOOD"

        # Insufficient pulses for reliable assessment
        if pulse_count < 4:
            reasons.append("Insufficient pulse peaks")

        # Check plausible pulse interval
        if not np.isnan(estimated_hr):

            if estimated_hr < 40 or estimated_hr > 200:
                reasons.append("Unusual estimated heart rate")

        # Check beat-to-beat interval consistency
        if not np.isnan(interval_cv):

            if interval_cv > 0.25:
                reasons.append("Irregular pulse intervals")

        # Check pulse amplitude consistency
        if not np.isnan(amplitude_cv):

            if amplitude_cv > 0.50:
                reasons.append("Inconsistent pulse amplitudes")

        if reasons:
            status = "SUSPICIOUS"

    results.append({

        "start_time": start_time,
        "end_time": end_time,
        "pulse_count": pulse_count,
        "peak_to_peak": amplitude_range,
        "signal_std": signal_std,
        "median_interval": median_interval,
        "estimated_hr_bpm": estimated_hr,
        "interval_cv": interval_cv,
        "amplitude_cv": amplitude_cv,
        "flatline": is_flatline,
        "status": status,
        "reason": "; ".join(reasons) if reasons else "No anomaly detected"

    })


# ==========================================
# 4. SAVE RESULTS
# ==========================================

features = pd.DataFrame(results)

output_file = (
    "signal_processing/pleth1_artifact_windows_v2.csv"
)

features.to_csv(output_file, index=False)


# ==========================================
# 5. PRINT SUMMARY
# ==========================================

print("\nANALYSIS SUMMARY")
print("----------------")

print("Total windows:", len(features))

print("\nWindow classification:")

print(
    features["status"].value_counts().to_string()
)

print("\nClassification percentages:")

print(
    (features["status"].value_counts(normalize=True) * 100)
    .round(2)
    .to_string()
)

print("\nSUSPICIOUS WINDOWS:")

print(
    features.loc[
        features["status"] != "GOOD",
        [
            "start_time",
            "end_time",
            "pulse_count",
            "estimated_hr_bpm",
            "interval_cv",
            "amplitude_cv",
            "status",
            "reason"
        ]
    ].to_string(index=False)
)


# ==========================================
# 6. PLOT SIGNAL WITH FLAGS
# ==========================================

plt.figure(figsize=(16, 6))

plt.plot(
    time,
    signal,
    linewidth=0.5,
    label="Filtered PPG"
)

for _, row in features.iterrows():

    if row["status"] == "SUSPICIOUS":

        plt.axvspan(
            row["start_time"],
            row["end_time"],
            color="orange",
            alpha=0.15
        )

    elif row["status"] == "POOR":

        plt.axvspan(
            row["start_time"],
            row["end_time"],
            color="red",
            alpha=0.20
        )

plt.title("PPG Artifact Detection - Version 2")
plt.xlabel("Time (seconds)")
plt.ylabel("Filtered PPG Amplitude")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    "signal_processing/pleth1_artifact_review_v2.png",
    dpi=150
)

plt.show()

print("\nVersion 2 analysis completed.")
print("Results saved:", output_file)
