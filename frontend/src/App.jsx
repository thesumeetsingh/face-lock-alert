import { useEffect, useRef, useState } from "react";

const API = "http://localhost:5000/api";

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function getLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({});
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude
      }),
      () => resolve({}),
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
    );
  });
}

function CameraCapture({ count, onComplete, busy }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const [captured, setCaptured] = useState([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 },
          audio: false
        });
        if (!active) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        videoRef.current.srcObject = stream;
        setRunning(true);
      } catch {
        setError("Camera access was blocked. Allow camera permission and try again.");
      }
    }
    startCamera();
    return () => {
      active = false;
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  function captureFrame() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return null;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.85);
  }

  async function captureRegistrationImages() {
    setError("");
    const images = [];
    for (let i = 0; i < count; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 350));
      const image = captureFrame();
      if (!image) {
        setError("Could not capture from the camera.");
        return;
      }
      images.push(image);
      setCaptured([...images]);
    }
    onComplete(images);
  }

  return (
    <div className="camera-box">
      {error && <div className="error">{error}</div>}
      <video ref={videoRef} autoPlay playsInline muted />
      <canvas ref={canvasRef} hidden />
      <p className="muted">Keep your face centered. The system will capture {count} images automatically.</p>
      <div className="progress"><div style={{ width: `${(captured.length / count) * 100}%` }} /></div>
      <p className="muted">Captured {captured.length} / {count}</p>
      <button className="button" disabled={!running || busy || captured.length > 0} onClick={captureRegistrationImages}>
        {busy ? "Processing..." : "Start Face Capture"}
      </button>
    </div>
  );
}

async function captureLoginImage() {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("Camera access is not available in this browser.");

  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 640, height: 480, facingMode: "user" },
    audio: false
  });

  try {
    const video = document.createElement("video");
    video.autoplay = true;
    video.playsInline = true;
    video.muted = true;
    video.srcObject = stream;

    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("Camera did not become ready.")), 5000);
      video.onloadedmetadata = async () => {
        clearTimeout(timeout);
        try {
          await video.play();
          resolve();
        } catch (error) {
          reject(error);
        }
      };
    });

    await new Promise((resolve) => setTimeout(resolve, 700));
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.9);
  } finally {
    stream.getTracks().forEach((track) => track.stop());
  }
}

function Register({ onDone, onLogin }) {
  const [step, setStep] = useState(1);
  const [userId, setUserId] = useState(null);
  const [captureCount, setCaptureCount] = useState(15);
  const [form, setForm] = useState({ name: "", username: "", email: "", phone: "", password: "", confirmation: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/config").then((data) => setCaptureCount(data.capture_count)).catch(() => {});
  }, []);

  async function submitDetails(event) {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirmation) return setError("Passwords do not match.");
    setBusy(true);
    try {
      const data = await api("/auth/register", { method: "POST", body: JSON.stringify(form) });
      setUserId(data.user_id);
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitFaces(images) {
    setBusy(true);
    setError("");
    try {
      const data = await api("/auth/register-face", {
        method: "POST",
        body: JSON.stringify({ user_id: userId, images })
      });
      onDone(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card auth-card">
      <div className="eyebrow">FACE LOCK ALERT</div>
      <h1>Create account</h1>
      {step === 1 ? (
        <form onSubmit={submitDetails}>
          {['name', 'username', 'email', 'phone'].map((field) => (
            <input key={field} required type={field === 'email' ? 'email' : 'text'} placeholder={field === 'phone' ? 'Phone (+919876543210)' : field[0].toUpperCase() + field.slice(1)} value={form[field]} onChange={(e) => setForm({ ...form, [field]: e.target.value })} />
          ))}
          <input required type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <input required type="password" placeholder="Confirm password" value={form.confirmation} onChange={(e) => setForm({ ...form, confirmation: e.target.value })} />
          {error && <div className="error">{error}</div>}
          <button className="button" disabled={busy}>{busy ? "Creating..." : "Continue to Face Setup"}</button>
          <button type="button" className="link-button" onClick={onLogin}>Already have an account? Login</button>
        </form>
      ) : (
        <>
          <p className="muted">Your account is created. Keep your face centered while the system captures multiple samples.</p>
          {error && <div className="error">{error}</div>}
          {!busy && <CameraCapture count={captureCount} onComplete={submitFaces} busy={busy} />}
          {busy && <p className="muted">Processing and storing your face data...</p>}
        </>
      )}
    </section>
  );
}

function Login({ onDone, onRegister }) {
  const [credentials, setCredentials] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitLogin(event) {
    event.preventDefault();
    setError("");
    setStatus("Opening camera and capturing your face...");
    setBusy(true);
    try {
      const image = await captureLoginImage();
      setStatus("Checking location...");
      const location = await getLocation();
      setStatus("Verifying credentials and face...");
      const data = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ ...credentials, image, location })
      });
      onDone(data.user);
    } catch (err) {
      setError(err.message);
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card auth-card">
      <div className="eyebrow">FACE LOCK ALERT</div>
      <h1>Secure login</h1>
      <p className="muted">Enter your username and password and press Login. Your face is captured automatically.</p>
      <form onSubmit={submitLogin}>
        <input required disabled={busy} placeholder="Username" value={credentials.username} onChange={(e) => setCredentials({ ...credentials, username: e.target.value })} />
        <input required disabled={busy} type="password" placeholder="Password" value={credentials.password} onChange={(e) => setCredentials({ ...credentials, password: e.target.value })} />
        {status && <div className="status">{status}</div>}
        {error && <div className="error">{error}</div>}
        <button className="button" disabled={busy}>{busy ? "Verifying..." : "Login"}</button>
        <button type="button" className="link-button" disabled={busy} onClick={onRegister}>Create a new account</button>
      </form>
    </section>
  );
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(value.endsWith("Z") ? value : `${value}Z`).toLocaleString();
}

function Dashboard({ user, onLogout }) {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");

  async function loadDashboard() {
    try {
      setError("");
      const data = await api("/dashboard");
      setDashboard(data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  if (!dashboard) {
    return <main className="dashboard-page"><div className="dashboard-shell"><p className="muted">Loading dashboard...</p></div></main>;
  }

  const { stats, attempts } = dashboard;

  return (
    <main className="dashboard-page">
      <div className="dashboard-shell">
        <header className="dashboard-header">
          <div>
            <div className="eyebrow">FACE LOCK ALERT</div>
            <h1>Security dashboard</h1>
            <p className="muted">Monitor your account activity and unsuccessful login attempts.</p>
          </div>
          <button className="button logout-button" onClick={onLogout}>Logout</button>
        </header>

        {error && <div className="error">{error}</div>}

        <section className="stats-grid">
          <div className="stat-card"><span>Total attempts</span><strong>{stats.total_attempts}</strong></div>
          <div className="stat-card"><span>Successful</span><strong>{stats.successful_attempts}</strong></div>
          <div className="stat-card danger-stat"><span>Unsuccessful</span><strong>{stats.unsuccessful_attempts}</strong></div>
          <div className="stat-card"><span>Last successful login</span><strong className="small-stat">{formatDate(stats.last_successful_login)}</strong></div>
        </section>

        <section className="dashboard-grid">
          <div className="panel profile-panel">
            <div className="panel-title">Account details</div>
            <div className="profile-details">
              <div><span>Name</span><strong>{user.name}</strong></div>
              <div><span>Username</span><strong>{user.username}</strong></div>
              <div><span>Email</span><strong>{user.email}</strong></div>
              <div><span>Phone</span><strong>{user.phone}</strong></div>
              <div><span>Registered</span><strong>{formatDate(user.created_at)}</strong></div>
            </div>
          </div>

          <div className="panel activity-panel">
            <div className="panel-heading">
              <div>
                <div className="panel-title">Recent login activity</div>
                <p className="muted">Latest 20 authentication attempts.</p>
              </div>
              <button className="refresh-button" onClick={loadDashboard}>Refresh</button>
            </div>

            {attempts.length === 0 ? (
              <div className="empty">No login activity recorded yet.</div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Status</th><th>Time</th><th>Reason</th><th>Location</th><th>Face score</th><th>Image</th></tr></thead>
                  <tbody>
                    {attempts.map((attempt) => (
                      <tr key={attempt.id}>
                        <td><span className={attempt.success ? "badge success" : "badge failed"}>{attempt.success ? "Success" : "Failed"}</span></td>
                        <td>{formatDate(attempt.attempted_at)}</td>
                        <td>{attempt.reason}</td>
                        <td>{attempt.latitude != null && attempt.longitude != null ? <a href={`https://www.google.com/maps?q=${attempt.latitude},${attempt.longitude}`} target="_blank" rel="noreferrer">View map</a> : "Unavailable"}</td>
                        <td>{attempt.confidence != null ? attempt.confidence.toFixed(2) : "—"}</td>
                        <td>{attempt.has_image ? <a href={`${API}/dashboard/attempts/${attempt.id}/image`} target="_blank" rel="noreferrer">View</a> : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

export default function App() {
  const [page, setPage] = useState("login");
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api("/me").then((data) => setUser(data.user)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    setUser(null);
    setPage("login");
  }

  if (loading) return <main className="app"><p className="muted">Loading...</p></main>;

  return (
    <>
      {user ? <Dashboard user={user} onLogout={logout} /> : (
        <main className="app">
          {page === "register" ? <Register onDone={setUser} onLogin={() => setPage("login")} /> : <Login onDone={setUser} onRegister={() => setPage("register")} />}
        </main>
      )}
    </>
  );
}
