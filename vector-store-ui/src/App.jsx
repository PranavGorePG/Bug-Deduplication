import { useState, useEffect, useRef } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

function Toast({ toasts, removeToast }) {
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span className="toast-icon">
            {t.type === "success" ? "✅" : t.type === "error" ? "❌" : "⏳"}
          </span>
          <span>{t.message}</span>
          <button className="toast-close" onClick={() => removeToast(t.id)}>×</button>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [collections, setCollections] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [collectionStatus, setCollectionStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);

  // Upload state
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  // Add / Delete collection state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [addingCollection, setAddingCollection] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deletingCollection, setDeletingCollection] = useState(false);

  // Clear (reset) state
  const [confirmClear, setConfirmClear] = useState(false);
  const [clearing, setClearing] = useState(false);

  const [loadingCollections, setLoadingCollections] = useState(true);
  const [toasts, setToasts] = useState([]);
  let toastId = useRef(0);

  const addToast = (message, type = "success") => {
    const id = ++toastId.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4500);
  };
  const removeToast = (id) => setToasts((prev) => prev.filter((t) => t.id !== id));

  // ── Fetch all collections ──────────────────────────────────────────────────
  const fetchCollections = async () => {
    setLoadingCollections(true);
    try {
      const res = await fetch(`${API_BASE}/vector-store/collections`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setCollections(data);
      // keep selection valid
      if (data.length > 0) {
        setSelectedProduct((prev) =>
          data.find((c) => c.name === prev) ? prev : data[0].name
        );
      } else {
        setSelectedProduct("");
      }
    } catch {
      addToast("Could not load collections. Is the backend running?", "error");
    } finally {
      setLoadingCollections(false);
    }
  };

  // ── Fetch status for the active collection ─────────────────────────────────
  const fetchCollectionStatus = async (name) => {
    if (!name) { setCollectionStatus(null); return; }
    setLoadingStatus(true);
    try {
      const res = await fetch(`${API_BASE}/vector-store/collection/${encodeURIComponent(name)}/status`);
      if (!res.ok) throw new Error();
      setCollectionStatus(await res.json());
    } catch {
      setCollectionStatus(null);
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => { fetchCollections(); }, []);
  useEffect(() => {
    // Reset per-collection UI state when selection changes
    setFile(null);
    setConfirmClear(false);
    setConfirmDelete(false);
    setShowAddForm(false);
    fetchCollectionStatus(selectedProduct);
  }, [selectedProduct]);

  // ── Upload file ────────────────────────────────────────────────────────────
  const handleFileChange = (e) => { if (e.target.files[0]) setFile(e.target.files[0]); };
  const handleDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return addToast("Please select a file first.", "error");
    if (!selectedProduct) return addToast("Please select a product collection.", "error");
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(
        `${API_BASE}/vector-store/append?product_name=${encodeURIComponent(selectedProduct)}`,
        { method: "POST", body: formData }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      addToast(`${data.issues_added} issues added to "${selectedProduct}"!`, "success");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      fetchCollectionStatus(selectedProduct);
      fetchCollections();
    } catch (err) {
      addToast(err.message || "Upload failed.", "error");
    } finally {
      setUploading(false);
    }
  };

  // ── Add collection ─────────────────────────────────────────────────────────
  const handleAddCollection = async () => {
    const name = newCollectionName.trim();
    if (!name) return addToast("Enter a collection name.", "error");
    setAddingCollection(true);
    try {
      const res = await fetch(
        `${API_BASE}/vector-store/collection/create?product_name=${encodeURIComponent(name)}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create");
      addToast(`Collection "${name}" created!`, "success");
      setNewCollectionName("");
      setShowAddForm(false);
      await fetchCollections();
      setSelectedProduct(data.collection_name || name);
    } catch (err) {
      addToast(err.message || "Failed to create collection.", "error");
    } finally {
      setAddingCollection(false);
    }
  };

  // ── Delete collection ──────────────────────────────────────────────────────
  const handleDeleteCollection = async () => {
    setDeletingCollection(true);
    setConfirmDelete(false);
    try {
      const res = await fetch(
        `${API_BASE}/vector-store/collection/${encodeURIComponent(selectedProduct)}`,
        { method: "DELETE" }
      );
      if (!res.ok) throw new Error("Delete failed");
      addToast(`Collection "${selectedProduct}" deleted.`, "success");
      setCollectionStatus(null);
      await fetchCollections();
    } catch (err) {
      addToast(err.message || "Delete failed.", "error");
    } finally {
      setDeletingCollection(false);
    }
  };

  // ── Clear data ─────────────────────────────────────────────────────────────
  const handleClear = async () => {
    setClearing(true);
    setConfirmClear(false);
    try {
      const res = await fetch(
        `${API_BASE}/vector-store/collection/${encodeURIComponent(selectedProduct)}/clear`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Clear failed");
      addToast(`Cleared ${data.points_deleted} vectors from "${selectedProduct}". Collection kept.`, "success");
      fetchCollectionStatus(selectedProduct);
      fetchCollections();
    } catch (err) {
      addToast(err.message || "Clear failed.", "error");
    } finally {
      setClearing(false);
    }
  };

  const activeCollection = collections.find((c) => c.name === selectedProduct);

  return (
    <div className="app">
      <Toast toasts={toasts} removeToast={removeToast} />

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">🐞</span>
            <div>
              <h1 className="logo-title">Bug Dedup</h1>
              <p className="logo-sub">Vector Store Manager</p>
            </div>
          </div>
          <div className="header-actions">
            <span className={`status-pill ${loadingCollections ? "pill-loading" : "pill-online"}`}>
              {loadingCollections ? "Loading…" : "Backend Online"}
            </span>
            <button className="btn-icon" onClick={fetchCollections} title="Refresh">🔄</button>
          </div>
        </div>
      </header>

      <main className="main">
        {/* ── Stats ──────────────────────────────────────────────────────── */}
        <div className="stats-bar">
          <div className="stat-card">
            <span className="stat-num">{collections.length}</span>
            <span className="stat-label">Collections</span>
          </div>
          <div className="stat-card">
            <span className="stat-num">
              {collections.reduce((s, c) => s + (c.vectors_count || 0), 0)}
            </span>
            <span className="stat-label">Total Vectors</span>
          </div>
          {collectionStatus && (
            <div className="stat-card stat-active">
              <span className="stat-num">{collectionStatus.total_issues}</span>
              <span className="stat-label">Vectors in "{selectedProduct}"</span>
            </div>
          )}
        </div>

        {/* ── Collection Selector Bar ────────────────────────────────────── */}
        <div className="collection-bar">
          <div className="collection-tabs-wrap">
            {loadingCollections ? (
              [1, 2, 3].map((i) => <div key={i} className="tab-skeleton" />)
            ) : collections.length === 0 ? (
              <span className="no-collections">No collections yet</span>
            ) : (
              collections.map((c) => (
                <button
                  key={c.name}
                  className={`collection-tab ${c.name === selectedProduct ? "tab-active" : ""}`}
                  onClick={() => setSelectedProduct(c.name)}
                >
                  <span className="tab-dot" />
                  {c.name}
                  {c.vectors_count != null && (
                    <span className="tab-count">{c.vectors_count}</span>
                  )}
                </button>
              ))
            )}
          </div>
          <div className="collection-bar-actions">
            <button
              className="btn-bar btn-add"
              onClick={() => { setShowAddForm((v) => !v); setConfirmDelete(false); setConfirmClear(false); }}
            >
              + Add
            </button>
            <button
              className="btn-bar btn-del"
              onClick={() => { setConfirmDelete((v) => !v); setShowAddForm(false); setConfirmClear(false); }}
              disabled={!selectedProduct}
            >
              🗑 Delete
            </button>
          </div>
        </div>

        {/* ── Add Collection Inline Form ──────────────────────────────────── */}
        {showAddForm && (
          <div className="inline-form">
            <input
              className="text-input"
              placeholder="Collection name (e.g. my-product)"
              value={newCollectionName}
              onChange={(e) => setNewCollectionName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddCollection()}
              autoFocus
            />
            <button
              className="btn btn-primary btn-sm"
              onClick={handleAddCollection}
              disabled={addingCollection || !newCollectionName.trim()}
            >
              {addingCollection ? <><span className="spinner" /> Creating…</> : "✅ Create"}
            </button>
            <button className="btn btn-cancel btn-sm" onClick={() => { setShowAddForm(false); setNewCollectionName(""); }}>
              ✖ Cancel
            </button>
          </div>
        )}

        {/* ── Delete Confirm Bar ─────────────────────────────────────────── */}
        {confirmDelete && selectedProduct && (
          <div className="inline-form danger-form">
            <span className="danger-msg">Delete collection <strong>"{selectedProduct}"</strong> and all its data?</span>
            <button
              className="btn btn-danger btn-sm"
              onClick={handleDeleteCollection}
              disabled={deletingCollection}
            >
              {deletingCollection ? <><span className="spinner" /> Deleting…</> : "Yes, Delete"}
            </button>
            <button className="btn btn-cancel btn-sm" onClick={() => setConfirmDelete(false)}>✖ Cancel</button>
          </div>
        )}

        {/* ── Main Grid ──────────────────────────────────────────────────── */}
        {selectedProduct ? (
          <div className="grid">
            {/* Upload Card */}
            <div className="card">
              <div className="card-header">
                <span className="card-icon">📤</span>
                <div>
                  <h2 className="card-title">Upload Issues</h2>
                  <p className="card-sub">→ <strong>{selectedProduct}</strong></p>
                </div>
              </div>
              <p className="card-desc">Upload an Excel or CSV file to append issues to this collection.</p>

              <div className="field">
                <label className="label">Excel / CSV File</label>
                <div
                  className={`dropzone ${dragOver ? "dragover" : ""} ${file ? "has-file" : ""}`}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input ref={fileInputRef} type="file" accept=".xlsx,.xls,.csv" onChange={handleFileChange} style={{ display: "none" }} />
                  {file ? (
                    <>
                      <span className="drop-file-icon">📄</span>
                      <p className="drop-filename">{file.name}</p>
                      <p className="drop-size">{(file.size / 1024).toFixed(1)} KB</p>
                    </>
                  ) : (
                    <>
                      <span className="drop-icon">☁️</span>
                      <p className="drop-text">Drag & drop or <span className="drop-link">browse</span></p>
                      <p className="drop-hint">.xlsx, .xls, .csv supported</p>
                    </>
                  )}
                </div>
              </div>

              <button
                className={`btn btn-primary ${uploading ? "btn-loading" : ""}`}
                onClick={handleUpload}
                disabled={uploading || !file}
              >
                {uploading ? <><span className="spinner" /> Uploading…</> : "⬆️ Upload to Vector Store"}
              </button>
            </div>

            {/* Collection Info + Danger Card */}
            <div className="card">
              <div className="card-header">
                <span className="card-icon">🗄️</span>
                <div>
                  <h2 className="card-title">{selectedProduct}</h2>
                  <p className="card-sub">Collection Details</p>
                </div>
              </div>

              {/* Status Info */}
              <div className="info-grid">
                {loadingStatus ? (
                  [1, 2, 3].map((i) => <div key={i} className="skeleton info-skeleton" />)
                ) : collectionStatus ? (
                  <>
                    <div className="info-item">
                      <span className="info-label">Vectors Stored</span>
                      <span className="info-val accent">{collectionStatus.total_issues}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Index Built</span>
                      <span className={`info-val ${collectionStatus.index_built ? "green" : "muted"}`}>
                        {collectionStatus.index_built ? "Yes" : "No"}
                      </span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Last Updated</span>
                      <span className="info-val muted">
                        {collectionStatus.last_updated_utc === "Never"
                          ? "Never"
                          : new Date(collectionStatus.last_updated_utc).toLocaleString()}
                      </span>
                    </div>
                  </>
                ) : (
                  <p className="muted-msg">No status available.</p>
                )}
              </div>

              <div className="divider" />

              {/* Danger Zone */}
              <div className="danger-zone">
                <p className="danger-zone-title">⚠️ Danger Zone</p>
                {!confirmClear ? (
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => setConfirmClear(true)}
                  >
                    🧹 Clear All Data
                  </button>
                ) : (
                  <div className="confirm-row">
                    <span className="danger-msg">Remove all vectors from <strong>"{selectedProduct}"</strong>?</span>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={handleClear}
                      disabled={clearing}
                    >
                      {clearing ? <><span className="spinner" /> Clearing…</> : "✅ Yes, Clear"}
                    </button>
                    <button className="btn btn-cancel btn-sm" onClick={() => setConfirmClear(false)}>✖ Cancel</button>
                  </div>
                )}
                <p className="danger-hint">This removes all vectors. The collection itself is preserved.</p>
              </div>
            </div>
          </div>
        ) : (
          /* Empty state when no collections */
          <div className="empty-page">
            <span>📭</span>
            <h3>No Collection Selected</h3>
            <p>Create a new collection using the <strong>+ Add</strong> button above.</p>
          </div>
        )}
      </main>
    </div>
  );
}
