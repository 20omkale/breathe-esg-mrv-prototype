import { useState, useEffect } from 'react';
import axios from 'axios';

export default function Dashboard() {
  const [records, setRecords] = useState([]);
  const [sourceType, setSourceType] = useState('SAP');
  const [loading, setLoading] = useState(false);

  // Hardcoded for the prototype. In a real app, this comes from the authenticated user.
  const COMPANY_ID = 1; 

  const fetchPendingRecords = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/pending-reviews/');
      setRecords(response.data);
    } catch (error) {
      console.error("Error fetching records", error);
    }
  };

  useEffect(() => {
    fetchPendingRecords();
  }, []);

  const handleFileUpload = (e) => {
    const uploadedFile = e.target.files[0];
    if (uploadedFile) {
      const reader = new FileReader();
      reader.onload = async (event) => {
        setLoading(true);
        const csvData = event.target.result;
        
        try {
          await axios.post('http://localhost:8000/api/ingest/', {
            company_id: COMPANY_ID,
            source_type: sourceType,
            csv_data: csvData
          });
          alert('Data ingested successfully');
          fetchPendingRecords();
        } catch (error) {
          alert('Upload failed. Did you create a Company in the Django admin panel?');
        } finally {
          setLoading(false);
          e.target.value = null; // reset the input
        }
      };
      reader.readAsText(uploadedFile);
    }
  };

  const handleReview = async (id, status) => {
    try {
      await axios.patch(`http://localhost:8000/api/review/${id}/`, { status });
      fetchPendingRecords(); // refresh the table
    } catch (error) {
      console.error("Error updating record", error);
    }
  };

  return (
    <div style={{ padding: '40px', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Breathe ESG - Analyst Dashboard</h1>
      
      <div style={{ background: '#f5f5f5', padding: '20px', borderRadius: '8px', marginBottom: '40px' }}>
        <h2>Ingest Data</h2>
        <select 
          value={sourceType} 
          onChange={(e) => setSourceType(e.target.value)}
          style={{ padding: '8px', marginRight: '20px', borderRadius: '4px' }}
        >
          <option value="SAP">SAP Fuel & Procurement (CSV)</option>
          <option value="UTILITY">Utility Electricity Data (CSV)</option>
          <option value="TRAVEL">Corporate Travel (CSV)</option>
        </select>
        
        <input 
          type="file" 
          accept=".csv" 
          onChange={handleFileUpload} 
          disabled={loading}
        />
        {loading && <span style={{ marginLeft: '10px' }}>Processing...</span>}
      </div>

      <h2>Pending Audit Reviews</h2>
      <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ccc' }}>
            <th style={{ paddingBottom: '10px' }}>Category</th>
            <th>Scope</th>
            <th>Raw Input</th>
            <th>Normalized (kgCO2e)</th>
            <th>Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {records.map(record => (
            <tr key={record.id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '15px 0' }}>{record.category}</td>
              <td>{record.scope}</td>
              <td>{record.raw_quantity} {record.raw_unit}</td>
              <td>{record.normalized_quantity}</td>
              <td>{record.date_of_activity}</td>
              <td>
                <button 
                  onClick={() => handleReview(record.id, 'APPROVED')}
                  style={{ background: '#16a34a', color: 'white', marginRight: '10px', padding: '6px 12px', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  Approve
                </button>
                <button 
                  onClick={() => handleReview(record.id, 'REJECTED')}
                  style={{ background: '#dc2626', color: 'white', padding: '6px 12px', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  Reject
                </button>
              </td>
            </tr>
          ))}
          {records.length === 0 && (
            <tr>
              <td colSpan="6" style={{ padding: '20px 0', textAlign: 'center', color: '#666' }}>
                No records pending review.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}