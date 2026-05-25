import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './index.css';

const API = import.meta.env.VITE_API_URL || 'https://breathe-esg-backend-nnxo.onrender.com/api';

const SCOPE_LABELS = {
  SCOPE_1: 'Scope 1',
  SCOPE_2: 'Scope 2',
  SCOPE_3: 'Scope 3',
};

const SOURCE_LABELS = {
  SAP:     'SAP (MB51)',
  UTILITY: 'Utility',
  TRAVEL:  'Travel',
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
        <div className="sidebar-logo">Breathe <span>ESG</span></div>
        <button className={`nav-btn ${tab === 'review' ? 'active' : ''}`} onClick={() => setTab('review')}>
          Review Queue
        </button>
        <button className={`nav-btn ${tab === 'ingest' ? 'active' : ''}`} onClick={() => setTab('ingest')}>
          Ingest Data
        </button>
        <button className={`nav-btn ${tab === 'batches' ? 'active' : ''}`} onClick={() => setTab('batches')}>
          Upload History
        </button>
      </aside>

      {/* Main content */}
      <main className="main">

        {backendMsg && (
          <div className="banner">{backendMsg}</div>
        )}

        {/* KPI cards — always visible */}
        {stats && (
          <div className="kpi-grid" style={{ marginBottom: 32 }}>
            <div className="kpi-card scope1">
              <div className="kpi-label">Scope 1 — Fuel</div>
              <div className="kpi-value">{stats.scope_totals_tco2e?.SCOPE_1 ?? '—'}</div>
              <div className="kpi-unit">tCO₂e approved</div>
            </div>
            <div className="kpi-card scope2">
              <div className="kpi-label">Scope 2 — Electricity</div>
              <div className="kpi-value">{stats.scope_totals_tco2e?.SCOPE_2 ?? '—'}</div>
              <div className="kpi-unit">tCO₂e approved</div>
            </div>
            <div className="kpi-card scope3">
              <div className="kpi-label">Scope 3 — Travel</div>
              <div className="kpi-value">{stats.scope_totals_tco2e?.SCOPE_3 ?? '—'}</div>
              <div className="kpi-unit">tCO₂e approved</div>
            </div>
            <div className="kpi-card pending">
              <div className="kpi-label">Pending Review</div>
              <div className="kpi-value">{stats.pending ?? '—'}</div>
              <div className="kpi-unit">records</div>
            </div>
            <div className="kpi-card flagged">
              <div className="kpi-label">Flagged</div>
              <div className="kpi-value">{stats.flagged ?? '—'}</div>
              <div className="kpi-unit">need attention</div>
            </div>
          </div>
        )}

        {/* ── TAB: Review ────────────────────────────────────────────────── */}
        {tab === 'review' && (
          <>
            <h1 className="page-title">
              Review Queue
              <span>{records.length} records shown</span>
            </h1>

            {/* Filters */}
            <div className="filter-row">
              <span className="filter-label">Filter:</span>
              <select className="select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
                <option value="">All Statuses</option>
                <option value="PENDING">Pending</option>
                <option value="APPROVED">Approved</option>
                <option value="REJECTED">Rejected</option>
              </select>
              <select className="select" value={filterScope} onChange={e => setFilterScope(e.target.value)}>
                <option value="">All Scopes</option>
                <option value="SCOPE_1">Scope 1</option>
                <option value="SCOPE_2">Scope 2</option>
                <option value="SCOPE_3">Scope 3</option>
              </select>
              <select className="select" value={filterSource} onChange={e => setFilterSource(e.target.value)}>
                <option value="">All Sources</option>
                <option value="SAP">SAP</option>
                <option value="UTILITY">Utility</option>
                <option value="TRAVEL">Travel</option>
              </select>
              <select className="select" value={filterFlag} onChange={e => setFilterFlag(e.target.value)}>
                <option value="">All Flags</option>
                <option value="SUSPICIOUS">Flagged Only</option>
                <option value="NONE">No Flag</option>
              </select>
            </div>

            {records.length === 0 ? (
              <div className="empty">No records match the current filters.</div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Scope</th>
                      <th>Source</th>
                      <th>Raw Input</th>
                      <th>CO₂e (kg)</th>
                      <th>Factor Used</th>
                      <th>Date</th>
                      <th>Status</th>
                      <th>Flag</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map(r => (
                      <tr key={r.id} className={r.flag === 'SUSPICIOUS' ? 'flag-row' : ''}>
                        <td>{r.category}</td>
                        <td>{scopeBadge(r.scope)}</td>
                        <td>{r.source_type ? sourceBadge(r.source_type) : '—'}</td>
                        <td style={{ color: 'var(--text-muted)' }}>{r.raw_quantity} {r.raw_unit}</td>
                        <td style={{ fontWeight: 600 }}>{r.co2e_kg != null ? Number(r.co2e_kg).toFixed(2) : '—'}</td>
                        <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                          {r.emission_factor_used != null ? r.emission_factor_used : '—'}
                        </td>
                        <td style={{ color: 'var(--text-muted)' }}>{r.date_of_activity}</td>
                        <td>{statusBadge(r.status)}</td>
                        <td>
                          {r.flag === 'SUSPICIOUS' && (
                            <span className="badge badge-flag" title={r.flag_reason}>⚠ Flagged</span>
                          )}
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: 6 }}>
                            <button className="btn btn-detail" onClick={() => openModal(r)}>Review</button>
                          </div>
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
            <h1 className="page-title">Ingest Data</h1>

            <div className="panel">
              <div className="panel-title">Upload a source file</div>
              <div className="upload-row">
                <select
                  className="select"
                  value={sourceType}
                  onChange={e => { setSourceType(e.target.value); setSelectedFile(null); setBatchResult(null); }}
                >
                  <option value="SAP">SAP Fuel — MB51 Flat File</option>
                  <option value="UTILITY">Utility Electricity — Portal CSV</option>
                  <option value="TRAVEL">Corporate Travel — Concur SAE</option>
                </select>

                <label className="file-label" htmlFor="file-upload">
                  {selectedFile ? selectedFile.name : 'Choose CSV file'}
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
                  className="upload-btn"
                  onClick={handleUpload}
                  disabled={!selectedFile || uploading || !company}
                >
                  {uploading ? 'Processing…' : 'Ingest'}
                </button>

                {!company && !loading && (
                  <span className="status-msg error">No company found — backend may still be seeding.</span>
                )}
              </div>

              {batchResult && (
                <div className={`batch-result ${batchResult.data?.rows_failed > 0 ? 'has-errors' : ''}`}>
                  {batchResult.ok ? (
                    <>
                      <div>✓ Ingested <strong>{batchResult.data.rows_ingested}</strong> records</div>
                      {batchResult.data.rows_flagged > 0 && (
                        <div style={{ color: 'var(--amber)' }}>
                          ⚠ {batchResult.data.rows_flagged} rows flagged as suspicious — check the Review Queue
                        </div>
                      )}
                      {batchResult.data.rows_failed > 0 && (
                        <>
                          <div style={{ color: 'var(--red)' }}>
                            ✗ {batchResult.data.rows_failed} rows failed to parse
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
                    <div style={{ color: 'var(--red)' }}>✗ {batchResult.error}</div>
                  )}
                </div>
              )}
            </div>

            <div className="panel">
              <div className="panel-title">What each source expects</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.8 }}>
                <div style={{ marginBottom: 10 }}>
                  <strong style={{ color: 'var(--amber)' }}>SAP (MB51):</strong> Flat file from the Material Document List transaction.
                  Accepts German column names (Menge, MEINS, BUDAT, MAKTX) or English equivalents.
                  Dates in DD.MM.YYYY or YYYY-MM-DD. Units: L, KG, M3.
                  Sample file: <code>Test_Data/sap_fuel.csv</code>
                </div>
                <div style={{ marginBottom: 10 }}>
                  <strong style={{ color: 'var(--blue)' }}>Utility:</strong> Portal CSV with Period_Start and Period_End dates
                  (billing periods don't align with calendar months). Estimated reads are flagged automatically.
                  Sample file: <code>Test_Data/utility_electricity.csv</code>
                </div>
                <div>
                  <strong style={{ color: 'var(--purple)' }}>Travel (Concur):</strong> Standard Accounting Extract format.
                  Flights use Origin_IATA and Dest_IATA codes — distance is computed from a lookup table,
                  not from the file itself. Multi-leg journeys are flagged.
                  Sample file: <code>Test_Data/corporate_travel.csv</code>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── TAB: Batch History ─────────────────────────────────────────── */}
        {tab === 'batches' && (
          <>
            <h1 className="page-title">Upload History</h1>
            {batches.length === 0 ? (
              <div className="empty">No uploads yet. Go to Ingest Data to upload a file.</div>
            ) : (
              batches.map(b => (
                <div key={b.id} className="batch-row">
                  <div>
                    {sourceBadge(b.source_type)}
                  </div>
                  <div className="batch-filename">{b.original_filename || 'unnamed'}</div>
                  <div className="batch-meta">{new Date(b.uploaded_at).toLocaleString('en-IN')}</div>
                  <div className="batch-stats">
                    <span className="batch-ok">✓ {b.rows_ingested}</span>
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

      {/* ── Review Modal ──────────────────────────────────────────────────── */}
      {modal && (
        <div className="modal-bg" onClick={e => e.target === e.currentTarget && setModal(null)}>
          <div className="modal">
            <div className="modal-title">Review Record #{modal.id}</div>

            {modal.flag === 'SUSPICIOUS' && (
              <div className="banner" style={{ marginBottom: 16 }}>
                ⚠ {modal.flag_reason || 'This record has been flagged for attention.'}
              </div>
            )}

            <div className="modal-row">
              <span className="modal-key">Category</span>
              <span className="modal-val">{modal.category}</span>
            </div>
            <div className="modal-row">
              <span className="modal-key">Scope</span>
              <span className="modal-val">{scopeBadge(modal.scope)}</span>
            </div>
            <div className="modal-row">
              <span className="modal-key">Source</span>
              <span className="modal-val">{modal.source_type ? sourceBadge(modal.source_type) : '—'}</span>
            </div>
            <div className="modal-row">
              <span className="modal-key">Raw Input</span>
              <span className="modal-val">{modal.raw_quantity} {modal.raw_unit}</span>
            </div>
            <div className="modal-row">
              <span className="modal-key">CO₂e</span>
              <span className="modal-val" style={{ fontWeight: 700 }}>
                {modal.co2e_kg != null ? `${Number(modal.co2e_kg).toFixed(2)} kg` : '—'}
              </span>
            </div>
            <div className="modal-row">
              <span className="modal-key">Emission Factor</span>
              <span className="modal-val">{modal.emission_factor_used ?? '—'} kgCO₂e/{modal.raw_unit}</span>
            </div>
            <div className="modal-row">
              <span className="modal-key">Date of Activity</span>
              <span className="modal-val">{modal.date_of_activity}</span>
            </div>
            <div className="modal-row">
              <span className="modal-key">File</span>
              <span className="modal-val" style={{ color: 'var(--text-muted)' }}>
                {modal.batch_filename || '—'}
              </span>
            </div>
            {modal.audit_notes && (
              <div className="modal-row">
                <span className="modal-key">Previous Note</span>
                <span className="modal-val" style={{ color: 'var(--text-muted)' }}>{modal.audit_notes}</span>
              </div>
            )}

            <textarea
              className="modal-notes"
              placeholder="Add an audit note (optional)…"
              value={auditNote}
              onChange={e => setAuditNote(e.target.value)}
            />

            <div className="modal-actions">
              <button className="btn btn-detail" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-reject" onClick={() => handleReview('REJECTED')}>Reject</button>
              <button className="btn btn-approve" onClick={() => handleReview('APPROVED')}>Approve</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}