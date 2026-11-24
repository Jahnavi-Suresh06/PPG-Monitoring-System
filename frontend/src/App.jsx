
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  HeartPulse,
  Gauge,
  Database,
  Wifi,
  WifiOff,
  RefreshCw,
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
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [batches, setBatches] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    let lastRecordId = 0;

    const fetchBatches = async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/ppg/batches?after_id=${lastRecordId}&limit=20`
        );

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const result = await response.json();
        const newBatches = result.batches || [];

        if (!active) return;

        setConnected(true);
        setError("");

        if (newBatches.length > 0) {
          setBatches((previous) => [...previous, ...newBatches]);
          lastRecordId = Math.max(
            lastRecordId,
            ...newBatches.map((batch) => batch.record_id)
          );
        }

        setLoading(false);
      } catch (err) {
        if (!active) return;
        setConnected(false);
        setError(err.message || "Unable to connect to the server");
        setLoading(false);
      }
    };

    fetchBatches();
    const interval = setInterval(fetchBatches, 2000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const latestBatch = batches.length
    ? batches[batches.length - 1]
    : null;

  const waveformData = useMemo(() => {
    if (!latestBatch?.samples) return [];

    return latestBatch.samples.map((value, index) => ({
      sample: index,
      time: (index / latestBatch.sampling_frequency).toFixed(2),
      amplitude: value,
    }));
  }, [latestBatch]);

  const totalSamples = batches.reduce(
    (total, batch) => total + (batch.sample_count || 0),
    0
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><Activity size={25} /></div>
          <div>
            <h2>PAI Edge</h2>
            <span>PPG Monitoring</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <div className="nav-item active">
          <Gauge size={19} />
          Dashboard
        </div>
        <div className="nav-item">
          <Activity size={19} />
          Signal Monitoring
        </div>
        <div className="nav-item">
          <Database size={19} />
          Data Batches
        </div>

        <div className="sidebar-bottom">
          <span className={`status-dot ${connected ? "online" : ""}`} />
          {connected ? "Server connected" : "Server disconnected"}
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">PATIENT MONITORING SYSTEM</p>
            <h1>PPG Dashboard</h1>
            <p className="subtitle">
              Monitor received PPG signals and data transmission
            </p>
          </div>

          <div className={`connection ${connected ? "connected" : "disconnected"}`}>
            {connected ? <Wifi size={17} /> : <WifiOff size={17} />}
            {connected ? "API Connected" : "API Disconnected"}
          </div>
        </header>

        {error && (
          <div className="error-banner">
            {error}. Check that your FastAPI server is running on port 8000.
          </div>
        )}

        <section className="metric-grid">
          <MetricCard
            icon={<Database />}
            label="Received Batches"
            value={batches.length}
            note="Batches retrieved from API"
          />
          <MetricCard
            icon={<Activity />}
            label="Total Samples"
            value={totalSamples.toLocaleString()}
            note="Samples received so far"
          />
          <MetricCard
            icon={<Gauge />}
            label="Sampling Frequency"
            value={latestBatch ? `${latestBatch.sampling_frequency} Hz` : "--"}
            note="From latest received batch"
          />
          <MetricCard
            icon={<HeartPulse />}
            label="Signal Quality (SQI)"
            value="Not available"
            note="Awaiting preprocessed CSV"
          />
        </section>

        <section className="content-grid">
          <div className="panel waveform-panel">
            <div className="panel-heading">
              <div>
                <h2>PPG Waveform</h2>
                <p>Latest received batch · Signal amplitude</p>
              </div>
              <span className="live-label">
                <span className="status-dot online" />
                Updating
              </span>
            </div>

            {waveformData.length > 0 ? (
              <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={waveformData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e8edf3" />
                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 11 }}
                      label={{
                        value: "Time (seconds)",
                        position: "insideBottom",
                        offset: -5,
                        fontSize: 12,
                      }}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="amplitude"
                      stroke="#16856b"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="empty-state">
                <Activity size={38} />
                <h3>{loading ? "Connecting to server..." : "No waveform data yet"}</h3>
                <p>Start the FastAPI server and send PPG batches to view the waveform.</p>
              </div>
            )}
          </div>

          <div className="panel details-panel">
            <h2>Latest Batch Details</h2>
            {latestBatch ? (
              <div className="details-list">
                <Detail label="Batch ID" value={latestBatch.batch_id} />
                <Detail label="Record ID" value={latestBatch.record_id} />
                <Detail label="Start Time" value={`${latestBatch.start_time} sec`} />
                <Detail label="Duration" value={`${latestBatch.duration_seconds} sec`} />
                <Detail label="Sample Count" value={latestBatch.sample_count} />
                <Detail label="Sampling Frequency" value={`${latestBatch.sampling_frequency} Hz`} />
                <Detail label="Received At" value={latestBatch.received_at || "--"} />
              </div>
            ) : (
              <p className="muted">Batch details will appear when data is received.</p>
            )}
          </div>
        </section>

        <section className="panel table-panel">
          <div className="panel-heading">
            <div>
              <h2>Received Batch History</h2>
              <p>Data retrieved from the FastAPI backend</p>
            </div>
            <button className="refresh-button" onClick={() => window.location.reload()}>
              <RefreshCw size={15} /> Refresh
            </button>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Record ID</th>
                  <th>Batch ID</th>
                  <th>Start Time</th>
                  <th>Duration</th>
                  <th>Samples</th>
                  <th>Frequency</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {[...batches].reverse().slice(0, 10).map((batch) => (
                  <tr key={batch.record_id}>
                    <td>#{batch.record_id}</td>
                    <td>{batch.batch_id}</td>
                    <td>{batch.start_time} sec</td>
                    <td>{batch.duration_seconds} sec</td>
                    <td>{batch.sample_count}</td>
                    <td>{batch.sampling_frequency} Hz</td>
                    <td><span className="received-badge">Received</span></td>
                  </tr>
                ))}
                {batches.length === 0 && (
                  <tr>
                    <td colSpan="7" className="empty-table">
                      No batches received yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <footer>
          PAI Edge · PPG Monitoring System · Data refreshes every 2 seconds
        </footer>
      </main>
    </div>
  );
}

function MetricCard({ icon, label, value, note }) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span className="metric-icon">{icon}</span>
      </div>
      <p>{label}</p>
      <h2>{value}</h2>
      <span className="metric-note">{note}</span>
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default App;
