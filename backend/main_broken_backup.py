
import csv
import math

from fastapi import Query


@app.get("/api/ppg/waveform")
def get_complete_waveform(
    start_time: float = Query(default=0, ge=0),
    end_time: float = Query(default=480, gt=0),
    max_points: int = Query(default=60000, ge=100, le=60000)
):
    """
    Retrieve raw and filtered PPG waveform samples.

    Default:
    - Sampling frequency: 125 Hz
    - Duration: 480 seconds
    - Total samples: 60,000
    - Returns all samples without downsampling.
    """

    waveform_path = (
        PROJECT_ROOT
        / "signal_processing"
        / "received_ppg_filtered.csv"
    )

    # Check whether processed waveform file exists
    if not waveform_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed PPG waveform file not found"
        )

    # Validate time range
    if end_time <= start_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be greater than start time"
        )

    points = []

    # Read actual processed PPG data
    with open(
        waveform_path,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            timestamp = float(row["time_seconds"])

            if start_time <= timestamp <= end_time:
                points.append({
                    "time_seconds": timestamp,
                    "ppg_raw": float(row["ppg_raw"]),
                    "ppg_filtered": float(row["ppg_filtered"])
                })

    # Check whether samples are available
    if not points:
        raise HTTPException(
            status_code=404,
            detail="No waveform samples found in this time range"
        )

    total_samples = len(points)

    # Downsample only when the requested limit is smaller
    if total_samples > max_points:

        step = math.ceil(
            (total_samples - 1) / (max_points - 1)
        )

        sampled_points = points[::step]

        # Preserve the final sample
        if sampled_points[-1] != points[-1]:
            sampled_points.append(points[-1])

        points = sampled_points

    return {
        "sampling_frequency": 125,
        "total_samples": total_samples,
        "returned_samples": len(points),
        "start_time": points[0]["time_seconds"],
        "end_time": points[-1]["time_seconds"],
        "waveform": points
    }
