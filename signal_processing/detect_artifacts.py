
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ------------------------------------------------
# 1. Load filtered PPG data
# ------------------------------------------------

file_path = "signal_processing/pleth1_filtered.csv"
df = pd.read_csv(file_path)

time = df["time_seconds"].to_numpy()
signal = df["pleth_1_filtered"].to_numpy()

sampling_frequency = 500
window_duration = 2
window_size = sampling_frequency * window_duration

print("PPG MOTION ARTIFACT ANALYSIS")
print("----------------------------")
print("Sampling frequency:", sampling_frequency, "Hz")
print("Total samples:", len(signal))
print("Window duration:", window_duration, "seconds")

# ------------------------------------------------
# 2. Calculate features for each window
# ------------------------------------------------

results = []

for start in range(0, len(signal), window_size):

    end = min(start + window_size, len(signal))
    segment = signal[start:end]

    if len(segment) < sampling_frequency:
        continue

    # Peak-to-peak amplitude
    amplitude_range = np.ptp(segment)

    # Signal standard deviation
    signal_std = np.std(segment)

    # Derivative RMS
    differences = np.diff(segment)
    derivative_rms = np.sqrt(np.mean(differences ** 2))

    # Flatline check
    is_flatline = amplitude_range < 1e-6

    results.append({
        "start_time": time[start],
        "end_time": time[end - 1],
        "sample_count": len(segment),
        "peak_to_peak": amplitude_range,
        "standard_deviation": signal_std,
        "derivative_rms": derivative_rms,
        "flatline": is_flatline
    })

features = pd.DataFrame(results)

# ------------------------------------------------
# 3. Adaptive thresholds using median and MAD
# ------------------------------------------------

def robust_limits(values):

    median = np.median(values)
    mad = np.median(np.abs(values - median))

    robust_spread = 1.4826 * mad

    lower = median - 3 * robust_spread
    upper = median + 3 * robust_spread

    return lower, upper


# Calculate thresholds
amp_lower, amp_upper = robust_limits(
    features["peak_to_peak"]
)

std_lower, std_upper = robust_limits(
    features["standard_deviation"]
)

derivative_lower, derivative_upper = robust_limits(
    features["derivative_rms"]
)

print("\nADAPTIVE THRESHOLDS")
print("-------------------")
print("Amplitude lower:", round(amp_lower, 2))
print("Amplitude upper:", round(amp_upper, 2))
print("Std lower:", round(std_lower, 2))
print("Std upper:", round(std_upper, 2))
print("Derivative upper:", round(derivative_upper, 2))

# ------------------------------------------------
# 4. Flag suspicious windows
# ------------------------------------------------

features["low_amplitude"] = (
    features["peak_to_peak"] < amp_lower
)

features["high_amplitude"] = (
    features["peak_to_peak"] > amp_upper
)

features["unusual_variation"] = (
    (features["standard_deviation"] < std_lower) |
    (features["standard_deviation"] > std_upper)
)

features["rapid_changes"] = (
    features["derivative_rms"] > derivative_upper
)

features["artifact_suspected"] = (
    features["low_amplitude"] |
    features["high_amplitude"] |
    features["unusual_variation"] |
    features["rapid_changes"] |
    features["flatline"]
)

# Record the reason for each flag
def get_reason(row):

    reasons = []

    if row["low_amplitude"]:
        reasons.append("Low amplitude")

    if row["high_amplitude"]:
        reasons.append("High amplitude")

    if row["unusual_variation"]:
        reasons.append("Unusual variation")

    if row["rapid_changes"]:
        reasons.append("Rapid changes")

    if row["flatline"]:
        reasons.append("Flatline")

    return ", ".join(reasons) if reasons else "Normal"


features["reason"] = features.apply(get_reason, axis=1)

# ------------------------------------------------
# 5. Save analysis results
# ------------------------------------------------

output_file = "signal_processing/pleth1_artifact_windows.csv"

features.to_csv(output_file, index=False)

# ------------------------------------------------
# 6. Print summary
# ------------------------------------------------

total_windows = len(features)
flagged_windows = features["artifact_suspected"].sum()
normal_windows = total_windows - flagged_windows

print("\nANALYSIS SUMMARY")
print("----------------")
print("Total windows:", total_windows)
print("Normal windows:", normal_windows)
print("Suspicious windows:", flagged_windows)

print(
    "Suspicious percentage:",
    round(flagged_windows / total_windows * 100, 2),
    "%"
)

print("\nSUSPICIOUS WINDOWS")
print("------------------")

print(
    features.loc[
        features["artifact_suspected"],
        ["start_time", "end_time", "reason"]
    ].to_string(index=False)
)

# ------------------------------------------------
# 7. Plot filtered signal and suspicious windows
# ------------------------------------------------

plt.figure(figsize=(15, 6))

plt.plot(
    time,
    signal,
    linewidth=0.6,
    label="Filtered PPG"
)

for _, row in features[
    features["artifact_suspected"]
].iterrows():

    plt.axvspan(
        row["start_time"],
        row["end_time"],
        alpha=0.2,
        color="red"
    )

plt.title("PPG Signal with Suspected Artifact Windows")
plt.xlabel("Time (seconds)")
plt.ylabel("Filtered PPG Amplitude")
plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig(
    "signal_processing/pleth1_artifact_review.png",
    dpi=150
)

plt.show()

print("\nArtifact analysis completed.")
print("Results saved:", output_file)
