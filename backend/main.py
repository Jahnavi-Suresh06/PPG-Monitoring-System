import json
import os
import csv
import math
import asyncio
import time

import mysql.connector
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

WAVEFORM_PATH = (
    PROJECT_ROOT
    / "signal_processing"
    / "received_ppg_filtered.csv"
)

transmission_completed = False


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="PPG Monitoring System API",
    description="REST API for PPG waveform transmission and monitoring",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://10.104.202.164:5173",
        "http://10.104.202.164:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# DATA MODEL
# --------------------------------------------------

class PPGBatch(BaseModel):
    batch_id: int
    start_time: float
    sampling_frequency: int
    duration_seconds: float
    sample_count: int
    samples: List[float]


# --------------------------------------------------
# MYSQL DATABASE CONNECTION
# --------------------------------------------------

class MySQLConnection:
    """Compatibility wrapper for the existing execute/fetch query pattern."""

    def __init__(self):
        required_settings = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
        missing = [key for key in required_settings if not os.getenv(key)]
        if missing:
            raise RuntimeError(
                "Missing MySQL settings in .env: " + ", ".join(missing)
            )

        self.connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "3307")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )

    def execute(self, query, params=None):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query.replace("?", "%s"), params or ())
        return cursor

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()


def get_connection():
    return MySQLConnection()


def initialize_database():
    connection = get_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS ppg_batches (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                batch_id INT NOT NULL,
                start_time DOUBLE NOT NULL,
                sampling_frequency INT NOT NULL,
                duration_seconds DOUBLE NOT NULL,
                sample_count INT NOT NULL,
                samples_json JSON NOT NULL,
                received_at DATETIME(6) NOT NULL
            )
        """)
        connection.commit()
    finally:
        connection.close()


def decode_samples_json(value):
    """Return samples as a Python list for MySQL JSON/string results."""
    if isinstance(value, list):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    raise ValueError("Unexpected samples_json value returned by MySQL")


@app.on_event("startup")
def startup_event():
    initialize_database()


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "PPG Monitoring System API is running",
        "status": "success"
    }


# --------------------------------------------------
# TRANSMISSION STATUS
# --------------------------------------------------

@app.get("/api/ppg/status")
def get_transmission_status():

    return {
        "transmission_completed": transmission_completed
    }


@app.post("/api/ppg/complete")
def complete_transmission():

    global transmission_completed

    transmission_completed = True

    return {
        "message": "PPG transmission completed",
        "transmission_completed": True
    }


# --------------------------------------------------
# RECEIVE PPG BATCH
# --------------------------------------------------

@app.post("/api/ppg/batch")
def receive_ppg_batch(batch: PPGBatch):

    global transmission_completed

    if batch.sampling_frequency != 125:
        raise HTTPException(
            status_code=400,
            detail="Invalid sampling frequency. Expected 125 Hz."
        )

    if abs(batch.duration_seconds - 2.0) > 0.001:
        raise HTTPException(
            status_code=400,
            detail="Invalid batch duration. Expected 2.0 seconds."
        )

    if batch.sample_count != len(batch.samples):
        raise HTTPException(
            status_code=400,
            detail="Sample count mismatch."
        )

    if batch.sample_count != 250:
        raise HTTPException(
            status_code=400,
            detail="Expected 250 samples per batch."
        )

    if not 1 <= batch.batch_id <= 32:
        raise HTTPException(
            status_code=400,
            detail="Only batch IDs 1 to 32 are accepted."
        )

    expected_start_time = round((batch.batch_id - 1) * 2.0, 3)

    if abs(batch.start_time - expected_start_time) > 0.001:
        raise HTTPException(
            status_code=400,
            detail="Invalid batch start time."
        )

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO ppg_batches (
            batch_id,
            start_time,
            sampling_frequency,
            duration_seconds,
            sample_count,
            samples_json,
            received_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            batch.batch_id,
            batch.start_time,
            batch.sampling_frequency,
            batch.duration_seconds,
            batch.sample_count,
            json.dumps(batch.samples),
            datetime.now(timezone.utc).replace(tzinfo=None)
        )
    )

    connection.commit()

    record_id = cursor.lastrowid

    connection.close()

    transmission_completed = False

    return {
        "message": "PPG batch received and stored successfully",
        "status": "success",
        "record_id": record_id,
        "batch_id": batch.batch_id,
        "start_time": batch.start_time,
        "duration_seconds": batch.duration_seconds,
        "sampling_frequency": batch.sampling_frequency,
        "samples_received": batch.sample_count,
        "samples": batch.samples[:10]
    }


# --------------------------------------------------
# GET RECEIVED BATCHES
# --------------------------------------------------

@app.get("/api/ppg/batches")
def get_ppg_batches(
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=500)
):

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT * FROM ppg_batches
        WHERE id > ?
        ORDER BY id ASC
        LIMIT ?
        """,
        (after_id, limit)
    ).fetchall()

    connection.close()

    return {
        "total_returned": len(rows),

        "batches": [
            {
                "record_id": row["id"],
                "batch_id": row["batch_id"],
                "start_time": row["start_time"],
                "sampling_frequency": row["sampling_frequency"],
                "duration_seconds": row["duration_seconds"],
                "sample_count": row["sample_count"],
                "samples": decode_samples_json(row["samples_json"]),
                "received_at": row["received_at"]
            }
            for row in rows
        ]
    }


# --------------------------------------------------
# GET LATEST BATCH
# --------------------------------------------------

@app.get("/api/ppg/latest")
def get_latest_ppg_batch():

    connection = get_connection()

    row = connection.execute(
        """
        SELECT * FROM ppg_batches
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    connection.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="No PPG batches found"
        )

    return {
        "record_id": row["id"],
        "batch_id": row["batch_id"],
        "start_time": row["start_time"],
        "sampling_frequency": row["sampling_frequency"],
        "duration_seconds": row["duration_seconds"],
        "sample_count": row["sample_count"],
        "samples": decode_samples_json(row["samples_json"]),
        "received_at": row["received_at"]
    }


# --------------------------------------------------
# GET RAW AND FILTERED PPG WAVEFORM
# --------------------------------------------------

@app.get("/api/ppg/waveform")
def get_complete_waveform(
    start_time: float = Query(default=0, ge=0),
    end_time: float = Query(default=480, gt=0),
    max_points: int = Query(default=60000, ge=100, le=60000)
):

    if start_time >= end_time:
        raise HTTPException(
            status_code=400,
            detail="start_time must be smaller than end_time"
        )

    if not WAVEFORM_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed PPG waveform CSV not found"
        )

    points = []

    try:

        with open(
            WAVEFORM_PATH,
            "r",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            required_columns = {
                "time_seconds",
                "ppg_raw",
                "ppg_filtered"
            }

            if (
                not reader.fieldnames
                or not required_columns.issubset(set(reader.fieldnames))
            ):
                raise HTTPException(
                    status_code=500,
                    detail="CSV must contain time_seconds, ppg_raw and ppg_filtered"
                )

            for row in reader:

                timestamp = float(row["time_seconds"])

                if start_time <= timestamp <= end_time:

                    points.append({
                        "time_seconds": timestamp,
                        "ppg_raw": float(row["ppg_raw"]),
                        "ppg_filtered": float(row["ppg_filtered"])
                    })

    except HTTPException:
        raise

    except (KeyError, ValueError, OSError) as error:

        raise HTTPException(
            status_code=500,
            detail=f"Error reading waveform CSV: {error}"
        )

    if not points:

        raise HTTPException(
            status_code=404,
            detail="No waveform samples found in the requested time range"
        )

    original_count = len(points)

    last_point = points[-1]

    if original_count > max_points:

        step = math.ceil(original_count / max_points)

        points = points[::step]

        if points[-1]["time_seconds"] != last_point["time_seconds"]:
            points.append(last_point)

    return {
        "sampling_frequency": 125,
        "total_samples": original_count,
        "returned_samples": len(points),
        "start_time": points[0]["time_seconds"],
        "end_time": points[-1]["time_seconds"],
        "waveform": points
    }


# --------------------------------------------------
# ANALYSIS BATCH AND INDIVIDUAL PULSE APIs
# --------------------------------------------------

ANALYSIS_SUMMARY_PATH = (
    PROJECT_ROOT
    / "signal_processing"
    / "analysis_batch_summary.csv"
)

ANALYSIS_WAVEFORMS_PATH = (
    PROJECT_ROOT
    / "signal_processing"
    / "analysis_batch_waveforms.csv"
)


@app.get("/api/ppg/analysis-batches")
def get_analysis_batches():

    if not ANALYSIS_SUMMARY_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Analysis batch summary not found"
        )

    batches = {}

    with open(ANALYSIS_SUMMARY_PATH, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            batch_id = int(row["analysis_batch_id"])

            if batch_id not in batches:
                batches[batch_id] = {
                    "analysis_batch_id": batch_id,
                    "pulse_count": 0
                }

            batches[batch_id]["pulse_count"] += 1

    return {
        "total_batches": len(batches),
        "batches": list(batches.values())
    }


@app.get("/api/ppg/analysis-batches/{batch_id}/pulses/{pulse_number}")
def get_analysis_pulse(batch_id: int, pulse_number: int):

    if not 1 <= batch_id <= 5:
        raise HTTPException(404, detail="Analysis batch not found")

    if not 1 <= pulse_number <= 32:
        raise HTTPException(404, detail="Pulse not found")

    if not ANALYSIS_SUMMARY_PATH.exists() or not ANALYSIS_WAVEFORMS_PATH.exists():
        raise HTTPException(404, detail="Analysis files not found")

    metadata = None

    with open(ANALYSIS_SUMMARY_PATH, "r", newline="") as file:
        for row in csv.DictReader(file):
            if (
                int(row["analysis_batch_id"]) == batch_id
                and int(row["pulse_number"]) == pulse_number
            ):
                metadata = row
                break

    if metadata is None:
        raise HTTPException(404, detail="Pulse not found")

    waveform = []

    with open(ANALYSIS_WAVEFORMS_PATH, "r", newline="") as file:
        for row in csv.DictReader(file):
            if (
                int(row["analysis_batch_id"]) == batch_id
                and int(row["pulse_number"]) == pulse_number
            ):
                waveform.append({
                    "time_seconds": float(row["time_seconds"]),
                    "relative_time_seconds": float(
                        row["relative_time_seconds"]
                    ),
                    "ppg_filtered": float(row["ppg_filtered"]),
                    "is_systolic_peak": row["is_systolic_peak"].lower() == "true",
                    "is_start_valley": row["is_start_valley"].lower() == "true",
                    "is_end_valley": row["is_end_valley"].lower() == "true"
                })

    if not waveform:
        raise HTTPException(404, detail="Pulse waveform not found")

    return {
        "analysis_batch_id": batch_id,
        "pulse_number": pulse_number,
        "metadata": {
            "start_time": float(metadata["start_time"]),
            "peak_time": float(metadata["peak_time"]),
            "end_time": float(metadata["end_time"]),
            "duration_seconds": float(metadata["duration_seconds"])
        },
        "sample_count": len(waveform),
        "waveform": waveform
    }


# --------------------------------------------------
# CURRENT RECORDING ANALYSIS API
# --------------------------------------------------

PULSE_DETECTION_PATH = (
    PROJECT_ROOT
    / "signal_processing"
    / "received_pulse_detection.csv"
)

SIGNAL_QUALITY_PATH = (
    PROJECT_ROOT
    / "signal_processing"
    / "received_signal_quality.csv"
)


def calculate_median(values):
    values = sorted(values)

    if not values:
        return None

    middle = len(values) // 2

    if len(values) % 2:
        return float(values[middle])

    return float((values[middle - 1] + values[middle]) / 2)


def calculate_cv_percent(values):
    if len(values) < 2:
        return None

    average = sum(values) / len(values)

    if average == 0:
        return None

    variance = sum(
        (value - average) ** 2 for value in values
    ) / len(values)

    return (math.sqrt(variance) / abs(average)) * 100


@app.get("/api/ppg/analysis")
def get_current_recording_analysis():

    # 1. Load the latest 32 batches from MySQL

    connection = get_connection()

    rows = connection.execute("""
        SELECT
            id,
            batch_id,
            sampling_frequency,
            duration_seconds,
            sample_count
        FROM ppg_batches
        ORDER BY id DESC
        LIMIT 32
    """).fetchall()

    connection.close()

    rows.reverse()

    if len(rows) != 32:
        raise HTTPException(
            status_code=400,
            detail="A complete 32-batch recording is not available."
        )

    batch_ids = [row["batch_id"] for row in rows]

    if batch_ids != list(range(1, 33)):
        raise HTTPException(
            status_code=400,
            detail="Latest database records are not one complete recording."
        )

    if any(
        row["sampling_frequency"] != 125
        or row["sample_count"] != 250
        or abs(row["duration_seconds"] - 2.0) > 0.001
        for row in rows
    ):
        raise HTTPException(
            status_code=400,
            detail="Recording batch configuration is invalid."
        )

    total_samples = sum(row["sample_count"] for row in rows)
    sampling_frequency = 125
    duration_seconds = total_samples / sampling_frequency

    # 2. Read current pulse detection results

    if not PULSE_DETECTION_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Current pulse detection CSV not found."
        )

    try:
        with open(PULSE_DETECTION_PATH, "r", newline="") as file:
            pulse_rows = list(csv.DictReader(file))

        if len(pulse_rows) != total_samples:
            raise ValueError(
                "Pulse detection sample count does not match the recording."
            )

        peaks = [
            row for row in pulse_rows
            if row["is_systolic_peak"].strip().lower() == "true"
        ]

        peak_times = [
            float(row["time_seconds"]) for row in peaks
        ]

        peak_amplitudes = [
            float(row["ppg_filtered"]) for row in peaks
        ]

    except (KeyError, ValueError, OSError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"Pulse analysis data error: {error}"
        )

    # 3. Calculate pulse intervals and heart rate

    intervals = [
        peak_times[index + 1] - peak_times[index]
        for index in range(len(peak_times) - 1)
    ]

    heart_rates = [
        60.0 / interval
        for interval in intervals
        if interval > 0
    ]

    mean_interval = (
        sum(intervals) / len(intervals)
        if intervals else None
    )

    mean_hr = (
        sum(heart_rates) / len(heart_rates)
        if heart_rates else None
    )

    median_hr = calculate_median(heart_rates)

    interval_cv = calculate_cv_percent(intervals)
    amplitude_cv = calculate_cv_percent(peak_amplitudes)

    # 4. Preliminary pulse consistency assessment

    if len(peak_times) < 4:
        pulse_consistency = "INSUFFICIENT_PULSES"

    elif (
        interval_cv is not None
        and amplitude_cv is not None
        and interval_cv <= 15
        and amplitude_cv <= 40
    ):
        pulse_consistency = "CONSISTENT"

    else:
        pulse_consistency = "REVIEW_REQUIRED"

    # 5. Read current signal-quality indicators

    if not SIGNAL_QUALITY_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Current signal quality CSV not found."
        )

    try:
        with open(SIGNAL_QUALITY_PATH, "r", newline="") as file:
            quality_rows = list(csv.DictReader(file))

        if len(quality_rows) != 1:
            raise ValueError(
                "Expected one quality window for the current recording."
            )

        quality = quality_rows[0]

        if int(quality["sample_count"]) != total_samples:
            raise ValueError(
                "Signal quality sample count does not match the recording."
            )

        signal_quality = {
            "raw_range": float(quality["raw_range"]),
            "raw_std": float(quality["raw_std"]),
            "filtered_range": float(quality["filtered_range"]),
            "filtered_std": float(quality["filtered_std"]),
            "analyzed_samples": int(quality["sample_count"]),
            "analyzed_duration_seconds": float(
                quality["duration_seconds"]
            )
        }

    except (KeyError, ValueError, OSError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"Signal quality data error: {error}"
        )

    # 6. SQI reporting: no invented percentage

    if duration_seconds < 10:
        sqi_status = "PRELIMINARY"
        sqi_message = (
            "Recording is shorter than 10 seconds. "
            "Insufficient duration for a reliable SQI assessment."
        )
    else:
        sqi_status = "ENGINEERING_REVIEW"
        sqi_message = (
            "Signal indicators are available. "
            "A validated SQI scoring method has not been established."
        )

    # 7. Return one common analysis response

    return {
        "recording": {
            "batch_count": len(rows),
            "total_samples": total_samples,
            "sampling_frequency": sampling_frequency,
            "duration_seconds": duration_seconds,
            "first_record_id": rows[0]["id"],
            "last_record_id": rows[-1]["id"]
        },
        "pulse_analysis": {
            "detected_pulses": len(peak_times),
            "interval_count": len(intervals),
            "mean_interval_seconds": mean_interval,
            "mean_heart_rate_bpm": mean_hr,
            "median_heart_rate_bpm": median_hr,
            "minimum_heart_rate_bpm": (
                min(heart_rates) if heart_rates else None
            ),
            "maximum_heart_rate_bpm": (
                max(heart_rates) if heart_rates else None
            ),
            "interval_cv_percent": interval_cv,
            "amplitude_cv_percent": amplitude_cv,
            "pulse_consistency": pulse_consistency
        },
        "signal_quality": signal_quality,
        "sqi": {
            "status": sqi_status,
            "score": None,
            "message": sqi_message
        }
    }


# --------------------------------------------------
# REAL-TIME PLAYBACK SYNCHRONIZATION
# --------------------------------------------------

playback_state = {
    "playback_index": 0,
    "is_playing": False,
    "device_on": True,
    "waveform_length": 0,
    "playback_step": 5,
    "updated_at": time.time()
}

connected_playback_clients = set()
playback_task = None


async def broadcast_playback_state():
    """Send the current playback state to every connected dashboard."""

    disconnected = []

    for client in connected_playback_clients:
        try:
            await client.send_json({
                "type": "PLAYBACK_STATE",
                **playback_state
            })
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        connected_playback_clients.discard(client)


async def playback_engine():
    """One authoritative playback timer shared by both laptops."""

    while True:
        await asyncio.sleep(0.04)

        if (
            playback_state["is_playing"]
            and playback_state["device_on"]
            and playback_state["waveform_length"] > 0
        ):
            length = playback_state["waveform_length"]

            playback_state["playback_index"] = (
                playback_state["playback_index"]
                + playback_state["playback_step"]
            ) % length

            playback_state["updated_at"] = time.time()

            await broadcast_playback_state()


@app.websocket("/ws/playback")
async def playback_websocket(websocket: WebSocket):
    """One shared playback controller for the server and client dashboards."""
    global playback_task

    await websocket.accept()
    connected_playback_clients.add(websocket)
    print("Playback WebSocket connected; active clients:", len(connected_playback_clients))

    if playback_task is None or playback_task.done():
        playback_task = asyncio.create_task(playback_engine())

    try:
        # Send the current state immediately after accepting the connection.
        await websocket.send_json({"type": "PLAYBACK_STATE", **playback_state})

        while True:
            message = await websocket.receive_json()
            action = message.get("action")

            if action == "REGISTER":
                length = int(message.get("waveform_length", 0))
                if length > 0:
                    first_registration = playback_state["waveform_length"] <= 0
                    playback_state["waveform_length"] = length
                    if first_registration:
                        # Start at the beginning; dashboards render the next window.
                        playback_state["playback_index"] = 0
                    else:
                        playback_state["playback_index"] = min(
                            playback_state["playback_index"], length - 1
                        )

            elif action == "PLAY":
                if playback_state["device_on"]:
                    playback_state["is_playing"] = True
            elif action == "PAUSE":
                playback_state["is_playing"] = False
            elif action == "STOP":
                playback_state["is_playing"] = False
                playback_state["playback_index"] = min(
                    124, max(0, playback_state["waveform_length"] - 1)
                )
            elif action == "RESET":
                playback_state["is_playing"] = False
                playback_state["playback_index"] = 0
            elif action == "TOGGLE_DEVICE":
                playback_state["device_on"] = not playback_state["device_on"]
                if not playback_state["device_on"]:
                    playback_state["is_playing"] = False

            playback_state["updated_at"] = time.time()
            await broadcast_playback_state()

    except WebSocketDisconnect:
        print("Playback WebSocket disconnected")
    except Exception as error:
        print(f"Playback WebSocket error: {type(error).__name__}: {error}")
    finally:
        connected_playback_clients.discard(websocket)
        print("Playback WebSocket clients remaining:", len(connected_playback_clients))
