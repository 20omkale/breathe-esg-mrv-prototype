import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './index.css';

const API = import.meta.env.VITE_API_URL || 'https://breathe-esg-backend-nnxo.onrender.com/api';

const SCOPE_LABELS = {
  SCOPE_1: 'Scope 1 — Direct',
  SCOPE_2: 'Scope 2 — Indirect',
  SCOPE_3: 'Scope 3 — Value Chain',
};

const SOURCE_LABELS = {
  SAP:     'SAP (MB51)',
  UTILITY: 'Utility Portal',
  TRAVEL:  'Concur Travel',
};

export default function App() {
  const [tab, setTab] = useState('review');

  // ── Shared state ──────────────────────────────────────────────────────────
  const [company, setCompany] = useState(null);
  const [records, setRecords] = useState([]);
  const [batches, setBatches] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [backendMsg, setBackendMsg] = useState('');

  // ── Filter state ──────────────────────────────────────────────────────────
  const [filterScope, setFilterScope] = useState('');
  const [filterStatus, setFilterStatus] = useState('PENDING');
  const [filterSource, setFilterSource] = useState('');
  const [filterFlag, setFilterFlag] = useState('');

  // ── Upload state ──────────────────────────────────────────────────────────
  const [sourceType, setSourceType] = useState('SAP');
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [batchResult, setBatchResult] = useState(null);
  const fileRef = useRef();

  // ── Modal state ───────────────────────────────────────────────────────────
  const [modal, setModal] = useState(null); // the record being reviewed
  const [auditNote, setAuditNote] = useState('');

  // ── Initial load ──────────────────────────────────────────────────────────
  useEffect(() => {
    fetchAll();
  }, []);

  // Re-fetch records when filters change
  useEffect(() => {
    if (company) fetchRecords(company.id);
  }, [filterScope, filterStatus, filterSource, filterFlag, company]);

  async function fetchAll() {
    setLoading(true);
    try {
      const [cRes] = await Promise.all([axios.get(`${API}/companies/`)]);
      if (cRes.data.length === 0) {
        setBackendMsg('No company found. Run seed_db.py on the backend first.');
        setLoading(false);
        return;
      }
      const co = cRes.data[0];
      setCompany(co);
      setBackendMsg('');
      await Promise.all([fetchRecords(co.id), fetchStats(co.id), fetchBatches(co.id)]);
    } catch {
      setBackendMsg('Backend is starting up — this can take up to 30 seconds on the free tier. Refresh in a moment.');
    } finally {
      setLoading(false);
    }
  }

  async function fetchRecords(companyId) {
    const params = { company_id: companyId };
    if (filterScope)  params.scope = filterScope;
    if (filterStatus) params.status = filterStatus;
    if (filterSource) params.source_type = filterSource;
    if (filterFlag)   params.flag = filterFlag;
    const res = await axios.get(`${API}/records/`, { params });
    setRecords(res.data);
  }

  async function fetchStats(companyId) {
    const res = await axios.get(`${API}/stats/`, { params: { company_id: companyId } });
    setStats(res.data);
  }

  async function fetchBatches(companyId) {
    const res = await axios.get(`${API}/batches/`, { params: { company_id: companyId } });
    setBatches(res.data);
  }

  // ── Upload ────────────────────────────────────────────────────────────────
  async function handleUpload() {
    if (!selectedFile || !company) return;
    setUploading(true);
    setBatchResult(null);
    try {
      const form = new FormData();
      form.append('file', selectedFile);
      form.append('company_id', company.id);
      form.append('source_type', sourceType);
      const res = await axios.post(`${API}/ingest/`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setBatchResult({ ok: true, data: res.data });
      setSelectedFile(null);
      if (fileRef.current) fileRef.current.value = '';
      await Promise.all([fetchRecords(company.id), fetchStats(company.id), fetchBatches(company.id)]);
    } catch (err) {
      setBatchResult({ ok: false, error: err.response?.data?.error || 'Upload failed' });
    } finally {
      setUploading(false);
    }
  }

  // ── Review ────────────────────────────────────────────────────────────────
  async function handleReview(status) {
    if (!modal) return;
    try {
      await axios.patch(`${API}/review/${modal.id}/`, { status, audit_notes: auditNote });
      setModal(null);
      setAuditNote('');
      await Promise.all([fetchRecords(company.id), fetchStats(company.id)]);
    } catch {
      alert('Review action failed. Please try again.');
    }
  }

  function openModal(record) {
    setModal(record);
    setAuditNote(record.audit_notes || '');
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function scopeBadge(scope) {
    const cls = { SCOPE_1: 'badge-scope1', SCOPE_2: 'badge-scope2', SCOPE_3: 'badge-scope3' };
    return <span className={`badge ${cls[scope] || ''}`}>{SCOPE_LABELS[scope] || scope}</span>;
  }

  function statusBadge(status) {
    const cls = { PENDING: 'badge-pending', APPROVED: 'badge-approved', REJECTED: 'badge-rejected' };
    return <span className={`badge ${cls[status] || ''}`}>{status}</span>;
  }

  function sourceBadge(type) {
    const cls = { SAP: 'badge-sap', UTILITY: 'badge-utility', TRAVEL: 'badge-travel' };
    return <span className={`badge ${cls[type] || ''}`}>{SOURCE_LABELS[type] || type}</span>;
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="app-shell">

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="sidebar-logo">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{color: 'var(--green)'}}>
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            Breathe <span>ESG</span>
          </div>
          
          <nav className="sidebar-nav">
            <button 
              className={`nav-btn ${tab === 'review' ? 'active' : ''}`} 
              onClick={() => setTab('review')}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              Review Queue
            </button>
            
            <button 
              className={`nav-btn ${tab === 'ingest' ? 'active' : ''}`} 
              onClick={() => setTab('ingest')}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Ingest Data
            </button>
            
            <button 
              className={`nav-btn ${tab === 'batches' ? 'active' : ''}`} 
              onClick={() => setTab('batches')}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Upload History
            </button>
          </nav>
        </div>

        {/* Human Signature: Analyst Profile footer in the sidebar */}
        <div className="sidebar-profile">
          <div className="avatar">OK</div>
          <div className="profile-info">
            <span className="profile-name">Om Kale</span>
            <span className="profile-role">ESG Lead Analyst</span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="main">

        {backendMsg && (
          <div className="banner">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {backendMsg}
          </div>
        )}

        {/* Header Section */}
        <div className="header-row">
          <div>
            <h1 className="page-title">
              {tab === 'review' && 'Data Audit & Review Queue'}
              {tab === 'ingest' && 'Ingest External Datasets'}
              {tab === 'batches' && 'Ingestion History'}
            </h1>
            <p className="page-subtitle">
              {company ? `${company.name} • Scope 1, 2 & 3 Emissions Audit` : 'Loading ESG Data Environment...'}
            </p>
          </div>
        </div>

        {/* KPI cards — always visible */}
        {stats && (
          <div className="kpi-grid">
            <div className="kpi-card scope1">
              <div className="kpi-label">Scope 1 — Combustion</div>
              <div className="kpi-value-row">
                <span className="kpi-value">{stats.scope_totals_tco2e?.SCOPE_1 ?? '0'}</span>
                <span className="kpi-unit">tCO₂e</span>
              </div>
              <div className="kpi-desc">Approved corporate fuel footprint</div>
            </div>
            <div className="kpi-card scope2">
              <div className="kpi-label">Scope 2 — Electricity</div>
              <div className="kpi-value-row">
                <span className="kpi-value">{stats.scope_totals_tco2e?.SCOPE_2 ?? '0'}</span>
                <span className="kpi-unit">tCO₂e</span>
              </div>
              <div className="kpi-desc">Approved grid power footprint</div>
            </div>
            <div className="kpi-card scope3">
              <div className="kpi-label">Scope 3 — Business Travel</div>
              <div className="kpi-value-row">
                <span className="kpi-value">{stats.scope_totals_tco2e?.SCOPE_3 ?? '0'}</span>
                <span className="kpi-unit">tCO₂e</span>
              </div>
              <div className="kpi-desc">Approved travel, rail, & hotel factors</div>
            </div>
            <div className="kpi-card pending">
              <div className="kpi-label">Awaiting Sign-off</div>
              <div className="kpi-value-row">
                <span className="kpi-value">{stats.pending ?? '0'}</span>
                <span className="kpi-unit">items</span>
              </div>
              <div className="kpi-desc">Requires analyst review</div>
            </div>
            <div className="kpi-card flagged">
              <div className="kpi-label">Flagged Anomalies</div>
              <div className="kpi-value-row">
                <span className="kpi-value">{stats.flagged ?? '0'}</span>
                <span className="kpi-unit">flagged</span>
              </div>
              <div className="kpi-desc">Outliers or estimated values</div>
            </div>
          </div>
        )}

        {/* ── TAB: Review ────────────────────────────────────────────────── */}
        {tab === 'review' && (
          <>
            {/* Filters */}
            <div className="control-bar">
              <div className="filter-row">
                <div className="filter-group">
                  <span className="filter-label">Status</span>
                  <select className="select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
                    <option value="">All Statuses</option>
                    <option value="PENDING">Pending Approval</option>
                    <option value="APPROVED">Approved</option>
                    <option value="REJECTED">Rejected</option>
                  </select>
                </div>
                <div className="filter-group">
                  <span className="filter-label">Scope</span>
                  <select className="select" value={filterScope} onChange={e => setFilterScope(e.target.value)}>
                    <option value="">All Scopes</option>
                    <option value="SCOPE_1">Scope 1 (Direct)</option>
                    <option value="SCOPE_2">Scope 2 (Electricity)</option>
                    <option value="SCOPE_3">Scope 3 (Travel)</option>
                  </select>
                </div>
                <div className="filter-group">
                  <span className="filter-label">Source</span>
                  <select className="select" value={filterSource} onChange={e => setFilterSource(e.target.value)}>
                    <option value="">All Sources</option>
                    <option value="SAP">SAP ERP</option>
                    <option value="UTILITY">Utility Portals</option>
                    <option value="TRAVEL">Concur Travel</option>
                  </select>
                </div>
                <div className="filter-group">
                  <span className="filter-label">Auditing</span>
                  <select className="select" value={filterFlag} onChange={e => setFilterFlag(e.target.value)}>
                    <option value="">All Integrity Checks</option>
                    <option value="SUSPICIOUS">Flagged Anomalies Only</option>
                    <option value="NONE">Clear Records Only</option>
                  </select>
                </div>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>
                Showing {records.length} records
              </div>
            </div>

            {records.length === 0 ? (
              <div className="empty-queue">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
                <div style={{ fontWeight: 600, color: 'var(--text)' }}>Review queue clear</div>
                <div style={{ fontSize: 13 }}>There are no records matching your current filter.</div>
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Scope</th>
                      <th>Source Type</th>
                      <th>Raw Quantity</th>
                      <th>Calculated CO₂e</th>
                      <th>Factor Applied</th>
                      <th>Activity Date</th>
                      <th>Review Status</th>
                      <th>Integrity Checks</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map(r => (
                      <tr key={r.id} className={r.flag === 'SUSPICIOUS' ? 'flag-row' : ''}>
                        <td style={{ fontWeight: 600 }}>{r.category}</td>
                        <td>{scopeBadge(r.scope)}</td>
                        <td>{r.source_type ? sourceBadge(r.source_type) : '—'}</td>
                        <td style={{ color: 'var(--text-muted)' }}>{r.raw_quantity} {r.raw_unit}</td>
                        <td style={{ fontWeight: 700, color: 'var(--text)' }}>
                          {r.co2e_kg != null ? `${Number(r.co2e_kg / 1000).toFixed(3)} t` : '—'}
                        </td>
                        <td style={{ color: 'var(--text-dim)', fontSize: 12 }}>
                          {r.emission_factor_used != null ? `${r.emission_factor_used} kg/unit` : '—'}
                        </td>
                        <td style={{ color: 'var(--text-muted)' }}>{r.date_of_activity}</td>
                        <td>{statusBadge(r.status)}</td>
                        <td>
                          {r.flag === 'SUSPICIOUS' ? (
                            <span className="badge badge-flag" title={r.flag_reason}>⚠ Flagged</span>
                          ) : (
                            <span style={{color: 'var(--green)', fontSize: 12, fontWeight: 500}}>✓ Clean</span>
                          )}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button className="row-action-btn" onClick={() => openModal(r)}>
                            Audit Record
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* ── TAB: Ingest ────────────────────────────────────────────────── */}
        {tab === 'ingest' && (
          <>
            <div className="upload-card">
              <svg className="upload-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <div className="upload-details">
                <div className="upload-title">Drag & drop export file here, or browse local folders</div>
                <div className="upload-desc">Supports CSV exports from SAP MM/MB51, Concur SAE, or Utility Portals</div>
              </div>
              
              <div className="upload-actions">
                <select
                  className="select"
                  value={sourceType}
                  onChange={e => { setSourceType(e.target.value); setSelectedFile(null); setBatchResult(null); }}
                >
                  <option value="SAP">SAP ERP (MB51 Fuel Logs)</option>
                  <option value="UTILITY">Utility Portals (Electricity Bills)</option>
                  <option value="TRAVEL">Concur Travel (Trip Expenses)</option>
                </select>

                <label className="file-label-btn" htmlFor="file-upload">
                  {selectedFile ? `Selected: ${selectedFile.name}` : 'Select File'}
                </label>
                <input
                  id="file-upload"
                  ref={fileRef}
                  type="file"
                  accept=".csv"
                  className="file-input"
                  onChange={e => { setSelectedFile(e.target.files[0]); setBatchResult(null); }}
                />

                <button
                  className="ingest-submit-btn"
                  onClick={handleUpload}
                  disabled={!selectedFile || uploading || !company}
                >
                  {uploading ? 'Parsing CSV...' : 'Ingest Dataset'}
                </button>
              </div>

              {batchResult && (
                <div className={`batch-result ${batchResult.data?.rows_failed > 0 ? 'has-errors' : ''}`} style={{width: '100%', maxWidth: 600, textAlign: 'left', background: 'var(--surface-2)'}}>
                  {batchResult.ok ? (
                    <>
                      <div style={{fontWeight: 600}}>✓ Ingest Process Completed</div>
                      <div>Successfully ingested <strong>{batchResult.data.rows_ingested}</strong> rows as normalized records.</div>
                      {batchResult.data.rows_flagged > 0 && (
                        <div style={{ color: 'var(--amber)', fontWeight: 500 }}>
                          ⚠ {batchResult.data.rows_flagged} rows were automatically flagged as suspicious (check review queue).
                        </div>
                      )}
                      {batchResult.data.rows_failed > 0 && (
                        <>
                          <div style={{ color: 'var(--red)', fontWeight: 500, marginTop: 8 }}>
                            ✗ {batchResult.data.rows_failed} rows failed validation rules:
                          </div>
                          <div className="error-list">
                            {batchResult.data.errors.map((e, i) => (
                              <div key={i}>Row {e.row}: {e.error}</div>
                            ))}
                          </div>
                        </>
                      )}
                    </>
                  ) : (
                    <div style={{ color: 'var(--red)' }}>✗ Ingestion Failure: {batchResult.error}</div>
                  )}
                </div>
              )}
            </div>

            {/* Explanatory cards */}
            <div className="info-card-grid">
              <div className="info-card">
                <div className="info-card-title" style={{color: 'var(--amber)'}}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  SAP ERP Normalization
                </div>
                <div className="info-card-desc">
                  Supports German logistics layouts (headers like BUDAT, Menge, MEINS, MAKTX) or standard exports. Maps volumetric metrics (e.g. m³) to liters automatically.
                </div>
              </div>
              <div className="info-card">
                <div className="info-card-title" style={{color: 'var(--blue)'}}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Utility Portal Scrapes
                </div>
                <div className="info-card-desc">
                  Splits non-calendar monthly cycles into appropriate activity midpoints. Automatically flags estimated meter readings to prevent reporting duplicates.
                </div>
              </div>
              <div className="info-card">
                <div className="info-card-title" style={{color: 'var(--purple)'}}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Concur Travel Extracts
                </div>
                <div className="info-card-desc">
                  Resolves flight airport coordinates (IATA origin/dest pairs) using a built-in Great Circle distance calculation database, flagging multi-leg travels.
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── TAB: Batch History ─────────────────────────────────────────── */}
        {tab === 'batches' && (
          <>
            {batches.length === 0 ? (
              <div className="empty-queue">
                <div style={{ fontWeight: 600, color: 'var(--text)' }}>No ingestion batches recorded</div>
                <div style={{ fontSize: 13 }}>Upload your first dataset file in the Ingest tab.</div>
              </div>
            ) : (
              batches.map(b => (
                <div key={b.id} className="batch-row">
                  <div>
                    {sourceBadge(b.source_type)}
                  </div>
                  <div className="batch-filename" style={{color: 'var(--text)'}}>{b.original_filename || 'unnamed_export.csv'}</div>
                  <div className="batch-meta">Uploaded on {new Date(b.uploaded_at).toLocaleString('en-IN')}</div>
                  <div className="batch-stats">
                    <span className="batch-ok">✓ {b.rows_ingested} ingested</span>
                    {b.rows_failed > 0 && <span className="batch-fail">✗ {b.rows_failed} failed</span>}
                    {b.rows_flagged > 0 && <span className="batch-warn">⚠ {b.rows_flagged} flagged</span>}
                  </div>
                  <div>
                    <span className={`badge ${b.status === 'COMPLETE' ? 'badge-approved' : b.status === 'FAILED' ? 'badge-rejected' : 'badge-pending'}`}>
                      {b.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </>
        )}
      </main>

      {/* ── Side-By-Side Audit Modal ────────────────────────────────────────── */}
      {modal && (
        <div className="modal-bg" onClick={e => e.target === e.currentTarget && setModal(null)}>
          <div className="modal-container">
            <div className="modal-header">
              <div className="modal-title-text">Audit Record #{modal.id}</div>
              <button 
                style={{background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer'}} 
                onClick={() => setModal(null)}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="modal-body">
              {/* Left Side: Normalized calculations */}
              <div className="modal-left">
                <span className="section-label">Normalized Carbon Activity</span>
                
                {modal.flag === 'SUSPICIOUS' && (
                  <div className="banner" style={{background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', color: 'var(--red)', marginBottom: 8}}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span>Integrity Alert: {modal.flag_reason || 'Outlier warning'}</span>
                  </div>
                )}

                <div className="modal-row">
                  <span className="modal-key">Category</span>
                  <span className="modal-val">{modal.category}</span>
                </div>
                <div className="modal-row">
                  <span className="modal-key">Emission Scope</span>
                  <span className="modal-val">{scopeBadge(modal.scope)}</span>
                </div>
                <div className="modal-row">
                  <span className="modal-key">Ingested From</span>
                  <span className="modal-val">{modal.source_type ? SOURCE_LABELS[modal.source_type] : '—'}</span>
                </div>
                <div className="modal-row">
                  <span className="modal-key">Reported Input</span>
                  <span className="modal-val">{modal.raw_quantity} {modal.raw_unit}</span>
                </div>
                <div className="modal-row">
                  <span className="modal-key">Normalized Quantity</span>
                  <span className="modal-val">{modal.normalized_quantity} {modal.normalized_unit}</span>
                </div>
                <div className="modal-row">
                  <span className="modal-key">Calculated footprint</span>
                  <span className="modal-val" style={{ color: 'var(--text)', fontWeight: 700 }}>
                    {modal.co2e_kg != null ? `${Number(modal.co2e_kg).toLocaleString()} kg CO₂e` : '—'}
                  </span>
                </div>
                <div className="modal-row">
                  <span className="modal-key">Conversion Factor</span>
                  <span className="modal-val">{modal.emission_factor_used ?? '—'} kg CO₂e per {modal.raw_unit}</span>
                </div>
                <div className="modal-row">
                  <span className="modal-key">Activity Date</span>
                  <span className="modal-val">{modal.date_of_activity}</span>
                </div>

                {modal.reviewed_at && (
                  <div className="modal-row" style={{borderBottom: 'none'}}>
                    <span className="modal-key">Audit Status</span>
                    <span className="modal-val" style={{color: modal.status === 'APPROVED' ? 'var(--green)' : 'var(--red)'}}>
                      {modal.status} on {new Date(modal.reviewed_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>

              {/* Right Side: Raw record dictionary from source CSV */}
              <div className="modal-right">
                <span className="section-label">Raw Line Source Data</span>
                <div style={{color: 'var(--text-dim)', fontSize: 12, marginBottom: 8}}>
                  Below is the original row fields extracted directly from the uploaded file prior to normalization:
                </div>
                <pre className="json-viewer">
                  {JSON.stringify(modal.raw_row_data, null, 2)}
                </pre>
              </div>
            </div>

            <div className="modal-footer">
              <textarea
                className="modal-notes-area"
                placeholder="Attach audit notes, reason for flagging, or review notes..."
                value={auditNote}
                onChange={e => setAuditNote(e.target.value)}
              />
              <div style={{display: 'flex', gap: 10, alignSelf: 'flex-end', marginLeft: 16}}>
                <button className="btn-base btn-secondary" onClick={() => setModal(null)}>Cancel</button>
                <button className="btn-base btn-reject" onClick={() => handleReview('REJECTED')}>Reject</button>
                <button className="btn-base btn-approve" onClick={() => handleReview('APPROVED')}>Approve & Sign-off</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}