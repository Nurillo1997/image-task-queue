import { useState, useEffect, useCallback } from "react";
import { uploadImage, getTaskStatus, getResultUrl } from "./api";
import "./App.css";

const OPERATIONS = [
  { value: "resize", label: "Resize (max 800px)" },
  { value: "watermark", label: "Add watermark" },
  { value: "grayscale", label: "Grayscale" },
];

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [operation, setOperation] = useState("resize");
  const [tasks, setTasks] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);

  const pollTaskStatuses = useCallback(async () => {
    setTasks((currentTasks) => {
      const unfinished = currentTasks.filter(
        (t) => t.status === "pending" || t.status === "processing"
      );
      if (unfinished.length === 0) return currentTasks;

      Promise.all(
        unfinished.map((t) =>
          getTaskStatus(t.task_id).catch(() => null)
        )
      ).then((results) => {
        setTasks((latest) =>
          latest.map((t) => {
            const updated = results.find((r) => r && r.task_id === t.task_id);
            return updated ? { ...t, ...updated } : t;
          })
        );
      });

      return currentTasks;
    });
  }, []);

  useEffect(() => {
    const interval = setInterval(pollTaskStatuses, 2000);
    return () => clearInterval(interval);
  }, [pollTaskStatuses]);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0] || null);
    setError(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Avval rasm tanlang");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const result = await uploadImage(selectedFile, operation);
      setTasks((prev) => [
        {
          task_id: result.task_id,
          status: result.status,
          original_filename: selectedFile.name,
          operation,
        },
        ...prev,
      ]);
      setSelectedFile(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="card">
      <h1>Image processing service</h1>
      <p className="subtitle">FastAPI + RabbitMQ + Celery + PostgreSQL</p>

      <div className="upload-zone">
        <input type="file" accept="image/jpeg,image/png" onChange={handleFileChange} />
        {selectedFile && <p className="file-name">{selectedFile.name}</p>}
      </div>

      <div className="controls">
        <select value={operation} onChange={(e) => setOperation(e.target.value)}>
          {OPERATIONS.map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </select>
        <button onClick={handleUpload} disabled={isUploading}>
          {isUploading ? "Uploading..." : "Upload and process"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="task-list">
        <p className="section-title">Recent tasks</p>
        {tasks.length === 0 && <p className="empty">Hali tasklar yo'q</p>}
        {tasks.map((task) => (
          <TaskRow key={task.task_id} task={task} />
        ))}
      </div>
    </div>
  );
}

function TaskRow({ task }) {
  const statusLabel = {
    pending: "Pending",
    processing: "Processing",
    done: "Done",
    failed: "Failed",
  }[task.status];

  return (
    <div className="task-row">
      <div className="task-info">
        <p className="task-name">{task.original_filename}</p>
        <p className="task-op">{task.operation}</p>
      </div>
      <span className={`badge badge-${task.status}`}>{statusLabel}</span>
      {task.status === "done" && (
        <a href={getResultUrl(task.task_id)} target="_blank" rel="noreferrer">
          Download
        </a>
      )}
    </div>
  );
}

export default App;
