
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. LOAD VERSION 2 RESULTS
# ==========================================

df = pd.read_csv(
    "signal_processing/pleth1_artifact_windows_v2.csv"
)

amplitude = df["peak_to_peak"]

# ==========================================
# 2. GLOBAL AND LOCAL BASELINES
# ==========================================

global_baseline = amplitude.median()

# 15 windows represent approximately 30 seconds
# because the windows overlap with a 2-second step.
local_baseline = amplitude.shift(1).rolling(
    window=15,
    min_periods=5
).median()

# Use global baseline until enough previous windows exist
local_baseline = local_baseline.fillna(global_baseline)

df["global_amplitude_ratio"] = (
    amplitude / global_baseline
)

df["local_amplitude_baseline"] = local_baseline

df["local_amplitude_ratio"] = (
    amplitude / local_baseline
)

# ==========================================
# 3. DETECT AMPLITUDE CHANGES
# ==========================================

# Compare each window with the previous window
df["previous_amplitude"] = amplitude.shift(1)

df["amplitude_change_ratio"] = (
    amplitude / df["previous_amplitude"]
)

# Exploratory thresholds, not clinical cutoffs
df["low_amplitude_change"] = (
    df["local_amplitude_ratio"] < 0.50
)

df["high_amplitude_change"] = (
    df["local_amplitude_ratio"] > 2.00
)

df["sudden_amplitude_change"] = (
    (df["amplitude_change_ratio"] < 0.67) |
    (df["amplitude_change_ratio"] > 1.50)
)

# ==========================================
# 4. CHECK PULSE REGULARITY
# ==========================================

df["irregular_pulse_intervals"] = (
    df["interval_cv"] > 0.15
)

df["inconsistent_pulse_amplitudes"] = (
    df["amplitude_cv"] > 0.40
)

df["insufficient_pulses"] = (
    df["pulse_count"] < 4
)

# ==========================================
# 5. CLASSIFY WINDOWS
# ==========================================

statuses = []
reasons_list = []

for _, row in df.iterrows():

    reasons = []

    if row["low_amplitude_change"]:
        reasons.append("Low relative amplitude")

    if row["high_amplitude_change"]:
        reasons.append("High relative amplitude")

    if row["sudden_amplitude_change"]:
        reasons.append("Sudden amplitude change")

    if row["irregular_pulse_intervals"]:
        reasons.append("Irregular pulse intervals")

    if row["inconsistent_pulse_amplitudes"]:
        reasons.append("Inconsistent pulse amplitudes")

    if row["insufficient_pulses"]:
        reasons.append("Insufficient pulse peaks")

    # These are preliminary engineering labels.
    if row["insufficient_pulses"]:
        status = "POOR"

    elif (
        row["irregular_pulse_intervals"]
        or row["inconsistent_pulse_amplitudes"]
        or row["low_amplitude_change"]
        or row["high_amplitude_change"]
        or row["sudden_amplitude_change"]
    ):
        status = "SUSPICIOUS"

    else:
        status = "GOOD"

    statuses.append(status)

    reasons_list.append(
        "; ".join(reasons) if reasons else "No anomaly detected"
    )

df["status"] = statuses
df["reason"] = reasons_list

# ==========================================
# 6. SAVE RESULTS
# ==========================================

output_file = (
    "signal_processing/pleth1_artifact_windows_v3.csv"
)

df.to_csv(output_file, index=False)

# ==========================================
# 7. PRINT SUMMARY
# ==========================================

print("PPG ARTIFACT DETECTION - VERSION 3")
print("----------------------------------")

print("Total windows:", len(df))

print("\nClassification:")
print(df["status"].value_counts().to_string())

print("\nFlag reasons:")
print(
    df.loc[df["status"] != "GOOD", "reason"]
    .value_counts()
    .to_string()
)

print("\nWindows from 40 to 100 seconds:")

print(
    df[
        (df["start_time"] >= 40) &
        (df["start_time"] <= 100)
    ][
        [
            "start_time",
            "peak_to_peak",
            "local_amplitude_ratio",
            "amplitude_change_ratio",
            "status",
            "reason"
        ]
    ].to_string(index=False)
)

# ==========================================
# 8. PLOT AMPLITUDE BASELINES
# ==========================================

plt.figure(figsize=(15, 6))

plt.plot(
    df["start_time"],
    df["peak_to_peak"],
    label="Window amplitude",
    linewidth=1
)

plt.plot(
    df["start_time"],
    df["local_amplitude_baseline"],
    label="Rolling local baseline",
    linewidth=2
)

plt.axhline(
    global_baseline,
    linestyle="--",
    label="Global median"
)

plt.xlabel("Time (seconds)")
plt.ylabel("Peak-to-peak amplitude")
plt.title("PPG Amplitude Analysis - Version 3")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    "signal_processing/pleth1_amplitude_v3.png",
    dpi=150
)

plt.show()

# ==========================================
# 9. PLOT CLASSIFICATION
# ==========================================

plt.figure(figsize=(15, 5))

plt.plot(
    df["start_time"],
    df["peak_to_peak"],
    label="PPG amplitude",
    linewidth=1
)

for _, row in df.iterrows():

    if row["status"] == "SUSPICIOUS":

        plt.axvspan(
            row["start_time"],
            row["end_time"],
            color="orange",
            alpha=0.12
        )

    elif row["status"] == "POOR":

        plt.axvspan(
            row["start_time"],
            row["end_time"],
            color="red",
            alpha=0.20
        )

plt.title("PPG Quality Review - Version 3")
plt.xlabel("Time (seconds)")
plt.ylabel("Peak-to-peak amplitude")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    "signal_processing/pleth1_quality_v3.png",
    dpi=150
)

plt.show()

print("\nVersion 3 analysis completed.")
print("Results saved:", output_file)
