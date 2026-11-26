
import { useEffect, useMemo, useRef, useState } from "react";

import {
  Activity,
  Database,
  Wifi,
  WifiOff,
  Clock,
  RefreshCw,
  ChevronDown,
  Play,
  Pause,
  Square,
  RotateCcw,
  Power,
  HeartPulse,
} from "lucide-react";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

import "./ServerDashboard.css";

const API_URL = "http://localhost:8000";

const SAMPLING_FREQUENCY = 125;
const WINDOW_SECONDS = 10;
const WINDOW_SIZE = SAMPLING_FREQUENCY * WINDOW_SECONDS;

export default function ServerDashboard() {
  const [batches, setBatches] = useState([]);
  const [latestBatch, setLatestBatch] = useState(null);

  const [waveform, setWaveform] = useState([]);
  const [waveformInfo, setWaveformInfo] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);

  const [playbackIndex, setPlaybackIndex] = useState(0);

  const [connected, setConnected] = useState(false);
  const [transmissionCompleted, setTransmissionCompleted] =
    useState(false);

  const [error, setError] = useState("");
  const [waveformError, setWaveformError] = useState("");
  const [analysisError, setAnalysisError] = useState("");

  const [loading, setLoading] = useState(true);
  const [waveformLoading, setWaveformLoading] = useState(true);

  const [deviceOn, setDeviceOn] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);

  const [lastUpdated, setLastUpdated] = useState(null);
  const [showPayload, setShowPayload] = useState(false);

  const playbackSocketRef = useRef(null);
  const pendingPlaybackCommandRef = useRef(null);

  // FETCH CURRENT RECORDING ANALYSIS
  useEffect(() => {
    let active = true;

    const fetchAnalysis = async () => {
      try {
        const response = await fetch(`${API_URL}/api/ppg/analysis`);

        if (!response.ok) {
          throw new Error(`Analysis API returned ${response.status}`);
        }

        const result = await response.json();

        if (!active) return;

        setAnalysisData(result);
        setAnalysisError("");
      } catch (err) {
        if (active) {
          setAnalysisError(err.message);
        }
      }
    };

    fetchAnalysis();

    const interval = setInterval(fetchAnalysis, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // FETCH REST TRANSPORT BATCHES AND SERVER STATUS
  useEffect(() => {
    let active = true;
    let lastRecordId = 0;

    const fetchBatches = async () => {
      try {
        const [batchResponse, statusResponse] = await Promise.all([
          fetch(
            `${API_URL}/api/ppg/batches?after_id=${lastRecordId}&limit=500`
          ),
          fetch(`${API_URL}/api/ppg/status`),
        ]);

        if (!batchResponse.ok || !statusResponse.ok) {
          throw new Error("Unable to fetch server data");
        }

        const batchResult = await batchResponse.json();
        const statusResult = await statusResponse.json();

        if (!active) return;

        const newBatches = batchResult.batches || [];

        if (newBatches.length > 0) {
          const maxRecordId = Math.max(
            ...newBatches.map((batch) => batch.record_id)
          );

          lastRecordId = Math.max(lastRecordId, maxRecordId);

          setBatches((previous) => [
            ...previous,
            ...newBatches,
          ]);
        }

        setTransmissionCompleted(
          Boolean(statusResult.transmission_completed)
        );

        setConnected(true);
        setError("");
        setLastUpdated(new Date());
      } catch (err) {
        if (active) {
          setConnected(false);
          setError(err.message);
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    const fetchLatestBatch = async () => {
      try {
        const response = await fetch(`${API_URL}/api/ppg/latest`);

        if (!response.ok) {
          throw new Error("Unable to fetch latest batch");
        }

        const result = await response.json();

        if (active) {
          setLatestBatch(result);
        }
      } catch (err) {
        if (active) {
          console.error("Latest batch fetch error:", err);
        }
      }
    };

    fetchBatches();
    fetchLatestBatch();

    const interval = setInterval(() => {
      fetchBatches();
      fetchLatestBatch();
    }, 2000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // FETCH FILTERED PPG WAVEFORM
  useEffect(() => {
    let active = true;

    const fetchWaveform = async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/ppg/waveform?max_points=60000`
        );

        if (!response.ok) {
          throw new Error(`Waveform API returned ${response.status}`);
        }

        const result = await response.json();

        if (!active) return;

        setWaveform(result.waveform || []);
        setWaveformInfo(result);
        setWaveformError("");
      } catch (err) {
        if (active) {
          setWaveformError(err.message);
        }
      } finally {
        if (active) {
          setWaveformLoading(false);
        }
      }
    };

    fetchWaveform();

    return () => {
      active = false;
    };
  }, []);

  // CONNECT TO THE SHARED BACKEND PLAYBACK CONTROLLER
  useEffect(() => {
    if (waveform.length === 0) return;

    const socket = new WebSocket("ws://localhost:8000/ws/playback"); playbackSocketRef.current = socket;

    socket.onopen = () => {
      socket.send(JSON.stringify({
        action: "REGISTER",
        waveform_length: waveform.length,
      }));

      // Apply the latest button command if it was clicked while connecting.
      const pendingAction = pendingPlaybackCommandRef.current;
      if (pendingAction) {
        socket.send(JSON.stringify({ action: pendingAction }));
        pendingPlaybackCommandRef.current = null;
      }
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type !== "PLAYBACK_STATE") return;

        if (typeof message.playback_index === "number") {
          setPlaybackIndex(
            Math.max(0, Math.min(message.playback_index, waveform.length - 1))
          );
        }

        if (typeof message.device_on === "boolean") {
          setDeviceOn(message.device_on);
        }

        if (typeof message.is_playing === "boolean") {
          setIsPlaying(message.is_playing);
        }
      } catch (err) {
        console.error("Invalid playback state received:", err);
      }
    };

    socket.onerror = () => {
      console.error("Playback WebSocket connection error");
    };

    socket.onclose = () => {
      if (playbackSocketRef.current === socket) {
        playbackSocketRef.current = null;
      }
    };

    return () => {
      socket.close();
      if (playbackSocketRef.current === socket) {
        playbackSocketRef.current = null;
      }
    };
  }, [waveform.length]);

  // SEND PLAYBACK COMMANDS TO THE BACKEND
  const sendPlaybackCommand = (action) => {
    const socket = playbackSocketRef.current;

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action }));
      return;
    }

    if (socket && socket.readyState === WebSocket.CONNECTING) {
      pendingPlaybackCommandRef.current = action;
      return;
    }

    console.error(
      "Playback WebSocket is not connected. Check that the backend is running and reachable."
    );
  };

  const handleDeviceToggle = () => sendPlaybackCommand("TOGGLE_DEVICE");
  const handlePlay = () => sendPlaybackCommand("PLAY");
  const handlePause = () => sendPlaybackCommand("PAUSE");
  const handleStop = () => sendPlaybackCommand("STOP");
  const handleReset = () => sendPlaybackCommand("RESET");

  // CHART DATA
  const chartData = useMemo(() => {
    if (!waveform.length) return [];

    const safeIndex = Math.min(
      playbackIndex,
      waveform.length - 1
    );

    const startIndex = Math.max(
      0,
      safeIndex - WINDOW_SIZE + 1
    );

    return waveform
      .slice(startIndex, safeIndex + 1)
      .map((point) => ({
        time: point.time_seconds,
        amplitude: point.ppg_filtered,
      }));
  }, [waveform, playbackIndex]);

  // CURRENT ANALYSIS METRICS
  const pulseAnalysis = analysisData?.pulse_analysis;
  const recording = analysisData?.recording;
  const signalQuality = analysisData?.signal_quality;
  const sqi = analysisData?.sqi;

  const totalPulses =
    pulseAnalysis?.detected_pulses ?? "--";

  const medianHeartRate =
    pulseAnalysis?.median_heart_rate_bpm;

  const pulseConsistency =
    pulseAnalysis?.pulse_consistency ?? "--";

  const totalSamples =
    recording?.total_samples ?? "--";

  const recordingDuration =
    recording?.duration_seconds != null
      ? recording.duration_seconds.toFixed(2)
      : "--";

  const samplingFrequency =
    recording?.sampling_frequency ?? SAMPLING_FREQUENCY;

  const currentPlaybackTime =
    waveform[playbackIndex]?.time_seconds ?? 0;

  const playbackStatus = !deviceOn
    ? "Device OFF"
    : isPlaying
      ? "Playback running"
      : "Playback paused";

  return (
    <div className="server-dashboard">
      {/* HEADER */}
      <header className="server-header">
        <div>
          <div className="server-title-row">
            <Activity size={25} />
            <h1>Server Dashboard</h1>
          </div>

          <p>PPG Monitoring System · REST API Server</p>
        </div>

        <div className="server-connection">
          {connected ? <Wifi size={17} /> : <WifiOff size={17} />}

          <span>
            {connected
              ? "Server Connected"
              : "Server Disconnected"}
          </span>
        </div>
      </header>

      {error && (
        <div className="server-error">
          {error}
        </div>
      )}

      {analysisError && (
        <div className="server-error">
          Analysis: {analysisError}
        </div>
      )}

      {/* CURRENT RECORDING METRICS */}
      <section className="server-metrics">
        <Metric
          icon={<HeartPulse />}
          label="Detected Pulses"
          value={totalPulses}
        />

        <Metric
          icon={<HeartPulse />}
          label="Median Heart Rate"
          value={
            medianHeartRate != null
              ? `${medianHeartRate.toFixed(2)} BPM`
              : "--"
          }
        />

        <Metric
          icon={<Database />}
          label="Total Samples"
          value={
            typeof totalSamples === "number"
              ? totalSamples.toLocaleString()
              : totalSamples
          }
        />

        <Metric
          icon={<Activity />}
          label="Signal Duration"
          value={`${recordingDuration} sec`}
        />
      </section>

      {/* ADDITIONAL ANALYSIS */}
      <section className="server-card">
        <div className="server-card-header">
          <div>
            <h2>Pulse Analysis</h2>
            <p>
              Current recording statistics from the common analysis API
            </p>
          </div>
        </div>

        <div className="server-details-grid">
          <Detail
            label="Sampling Frequency"
            value={`${samplingFrequency} Hz`}
          />

          <Detail
            label="Mean Heart Rate"
            value={
              pulseAnalysis?.mean_heart_rate_bpm != null
                ? `${pulseAnalysis.mean_heart_rate_bpm.toFixed(2)} BPM`
                : "--"
            }
          />

          <Detail
            label="Mean Pulse Interval"
            value={
              pulseAnalysis?.mean_interval_seconds != null
                ? `${pulseAnalysis.mean_interval_seconds.toFixed(4)} sec`
                : "--"
            }
          />

          <Detail
            label="Pulse Consistency"
            value={pulseConsistency}
          />

          <Detail
            label="Interval CV"
            value={
              pulseAnalysis?.interval_cv_percent != null
                ? `${pulseAnalysis.interval_cv_percent.toFixed(2)}%`
                : "--"
            }
          />

          <Detail
            label="Amplitude CV"
            value={
              pulseAnalysis?.amplitude_cv_percent != null
                ? `${pulseAnalysis.amplitude_cv_percent.toFixed(2)}%`
                : "--"
            }
          />
        </div>
      </section>

      {/* SQI */}
      <section className="server-card">
        <div className="server-card-header">
          <div>
            <h2>Signal Quality Assessment</h2>
            <p>
              Preliminary engineering assessment — not clinically validated
            </p>
          </div>

          <span className="server-status-label">
            {sqi?.status ?? "LOADING"}
          </span>
        </div>

        {sqi && signalQuality ? (
          <>
            <p>{sqi.message}</p>

            <div className="server-details-grid">
              <Detail
                label="SQI Score"
                value={sqi.score ?? "Not calculated"}
              />

              <Detail
                label="Raw Signal Range"
                value={signalQuality.raw_range.toFixed(5)}
              />

              <Detail
                label="Raw Signal Std"
                value={signalQuality.raw_std.toFixed(5)}
              />

              <Detail
                label="Filtered Signal Range"
                value={signalQuality.filtered_range.toFixed(5)}
              />

              <Detail
                label="Filtered Signal Std"
                value={signalQuality.filtered_std.toFixed(5)}
              />

              <Detail
                label="Samples Analysed"
                value={signalQuality.analyzed_samples}
              />
            </div>
          </>
        ) : (
          <div className="server-empty">
            Loading signal quality assessment...
          </div>
        )}
      </section>

      {/* WAVEFORM */}
      <section className="server-card">
        <div className="server-card-header">
          <div>
            <h2>Filtered PPG Waveform</h2>
            <p>
              Same synchronized waveform displayed on the Client Dashboard
            </p>
          </div>

          <div
            className={`server-playback-status ${isPlaying && deviceOn ? "playing" : ""
              }`}
          >
            <span className="server-status-dot" />
            {playbackStatus}
          </div>
        </div>

        {waveformError && (
          <div className="server-error">
            {waveformError}
          </div>
        )}

        {/* PLAYBACK CONTROLS */}
        <div className="server-playback-controls">
          <div className="server-playback-buttons">
            <button
              className="server-control-button server-power-button"
              onClick={handleDeviceToggle}
            >
              <Power size={17} />
              {deviceOn ? "Device ON" : "Device OFF"}
            </button>

            <button
              className="server-control-button server-play-button"
              onClick={handlePlay}
              disabled={!deviceOn || !waveform.length || isPlaying}
            >
              <Play size={16} />
              Play
            </button>

            <button
              className="server-control-button"
              onClick={handlePause}
              disabled={!isPlaying}
            >
              <Pause size={16} />
              Pause
            </button>

            <button
              className="server-control-button"
              onClick={handleStop}
              disabled={!waveform.length}
            >
              <Square size={15} />
              Stop
            </button>

            <button
              className="server-control-button"
              onClick={handleReset}
              disabled={!waveform.length}
            >
              <RotateCcw size={16} />
              Reset
            </button>
          </div>

          <div className="server-playback-time">
            {currentPlaybackTime.toFixed(2)} sec
            <span> / {recordingDuration} sec</span>
          </div>
        </div>

        {waveformLoading ? (
          <div className="server-empty">
            Loading filtered waveform...
          </div>
        ) : chartData.length ? (
          <>
            <div className="server-chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{
                    top: 10,
                    right: 25,
                    left: 10,
                    bottom: 20,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#e5e7eb"
                  />

                  <XAxis
                    dataKey="time"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    tickFormatter={(value) =>
                      Number(value).toFixed(1)
                    }
                    tick={{ fontSize: 11 }}
                    label={{
                      value: "Time (seconds)",
                      position: "insideBottom",
                      offset: -10,
                    }}
                  />

                  <YAxis
                    tick={{ fontSize: 11 }}
                    label={{
                      value: "Amplitude",
                      angle: -90,
                      position: "insideLeft",
                    }}
                  />

                  <Tooltip
                    labelFormatter={(value) =>
                      `Time: ${Number(value).toFixed(3)} sec`
                    }
                    formatter={(value) => [
                      Number(value).toFixed(5),
                      "Filtered PPG",
                    ]}
                  />

                  <Line
                    type="linear"
                    dataKey="amplitude"
                    stroke="#2563eb"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="server-chart-footer">
              <span>
                Total source samples:{" "}
                {waveformInfo?.total_samples?.toLocaleString() ??
                  totalSamples}
              </span>

              <span>
                Sampling frequency: {samplingFrequency} Hz
              </span>

              <span>Window: {WINDOW_SECONDS} seconds</span>
            </div>
          </>
        ) : (
          <div className="server-empty">
            No filtered waveform data available.
          </div>
        )}
      </section>

      {/* LATEST RECEIVED BATCH */}
      <section className="server-card">
        <div className="server-card-header">
          <div>
            <h2>Latest Received REST Batch</h2>
            <p>
              Actual batch information received and stored by the server
            </p>
          </div>
        </div>

        {latestBatch ? (
          <div className="server-details-grid">
            <Detail
              label="Batch ID"
              value={latestBatch.batch_id}
            />

            <Detail
              label="Record ID"
              value={latestBatch.record_id}
            />

            <Detail
              label="Sample Count"
              value={latestBatch.sample_count}
            />

            <Detail
              label="Sampling Frequency"
              value={`${latestBatch.sampling_frequency} Hz`}
            />

            <Detail
              label="Duration"
              value={`${latestBatch.duration_seconds} seconds`}
            />

            <Detail
              label="Start Time"
              value={latestBatch.start_time}
            />

            <Detail
              label="Received At"
              value={latestBatch.received_at}
            />
          </div>
        ) : (
          <div className="server-empty">
            {loading
              ? "Waiting for received batches..."
              : "No REST batches received yet."}
          </div>
        )}

        {latestBatch && (
          <div className="server-payload-section">
            <button
              className="server-payload-toggle"
              onClick={() => setShowPayload(!showPayload)}
            >
              <span>Latest REST Payload (JSON)</span>

              <ChevronDown
                size={18}
                style={{
                  transform: showPayload
                    ? "rotate(180deg)"
                    : "rotate(0deg)",
                }}
              />
            </button>

            {showPayload && (
              <pre className="server-json">
                {JSON.stringify(latestBatch, null, 2)}
              </pre>
            )}
          </div>
        )}
      </section>

      {/* RECEIVED BATCH HISTORY */}
      <section className="server-card">
        <div className="server-card-header">
          <div>
            <h2>Received Batch History</h2>
            <p>Batches received through the REST API</p>
          </div>

          <div className="server-status-label">
            <Database size={17} />
            {batches.length} Records
          </div>
        </div>

        {batches.length ? (
          <div className="server-table-wrapper">
            <table className="server-table">
              <thead>
                <tr>
                  <th>Record ID</th>
                  <th>Batch ID</th>
                  <th>Samples</th>
                  <th>Frequency</th>
                  <th>Duration</th>
                  <th>Received At</th>
                </tr>
              </thead>

              <tbody>
                {[...batches]
                  .slice(-10)
                  .reverse()
                  .map((batch) => (
                    <tr key={batch.record_id}>
                      <td>{batch.record_id}</td>
                      <td>{batch.batch_id}</td>
                      <td>{batch.sample_count}</td>
                      <td>{batch.sampling_frequency} Hz</td>
                      <td>{batch.duration_seconds} s</td>
                      <td>{batch.received_at}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="server-empty">
            No batch records available.
          </div>
        )}
      </section>

      {/* FOOTER */}
      <footer className="server-footer">
        <div>
          {connected ? <Wifi size={16} /> : <WifiOff size={16} />}
          <span>
            {connected
              ? "REST API connection active"
              : "Waiting for server connection"}
          </span>
        </div>

        <div>
          <Clock size={16} />
          <span>
            Last updated:{" "}
            {lastUpdated
              ? lastUpdated.toLocaleTimeString()
              : "--"}
          </span>
        </div>

        <div>
          <RefreshCw size={16} />
          <span>
            {transmissionCompleted
              ? "Transmission completed"
              : "Transmission in progress"}
          </span>
        </div>
      </footer>
    </div>
  );
}

// METRIC CARD
function Metric({ icon, label, value }) {
  return (
    <div className="server-metric-card">
      <div className="server-metric-icon">{icon}</div>

      <div>
        <p>{label}</p>
        <h3>{value}</h3>
      </div>
    </div>
  );
}

// DETAIL ROW
function Detail({ label, value }) {
  return (
    <div className="server-detail-item">
      <span>{label}</span>
      <strong>{value ?? "--"}</strong>
    </div>
  );
}
