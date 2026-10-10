import React, { useState, useEffect } from 'react';
import { Activity, Server, RefreshCw, CheckCircle2, ShieldCheck, Zap } from 'lucide-react';
import './App.css';

function App() {
  const [stats, setStats] = useState({
    total_requests: 0,
    backend_requests: { backend1: 0, backend2: 0, backend3: 0 },
    active_connections: 0,
    last_updated: 'N/A'
  });
  const [health, setHealth] = useState('Checking...');
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8080/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch('http://localhost:8080/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data.status);
      } else {
        setHealth('Unhealthy');
      }
    } catch (err) {
      setHealth('Offline');
    }
  };

  useEffect(() => {
    fetchStats();
    fetchHealth();
    const interval = setInterval(() => {
      fetchStats();
      fetchHealth();
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const triggerRequest = async () => {
    setLoading(true);
    try {
      await fetch('http://localhost:8080/');
      await fetchStats();
    } catch (err) {
      console.error('Request failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header>
        <div className="header-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Zap style={{ width: '2rem', height: '2rem', color: '#22d3ee' }} />
            <h1>Synapse Dashboard</h1>
          </div>
          <p>Layer 7 Load Balancer Monitoring & Telemetry</p>
        </div>
        <div className="header-actions">
          <div className="health-badge">
            <ShieldCheck style={{ width: '1rem', height: '1rem', color: health === 'healthy' ? '#34d399' : '#fb7185' }} />
            <span>LB Status: {health}</span>
          </div>
          <button
            onClick={triggerRequest}
            disabled={loading}
            className="test-btn"
          >
            <RefreshCw style={{ width: '1rem', height: '1rem', animation: loading ? 'spin 1s linear infinite' : 'none', display: 'inline', marginRight: '6px' }} />
            Send Test Request
          </button>
        </div>
      </header>

      {/* Global Metrics Grid */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span>Total Requests</span>
            <Activity style={{ width: '1.25rem', height: '1.25rem', color: '#22d3ee' }} />
          </div>
          <div className="metric-value">{stats.total_requests}</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Active Connections</span>
            <Server style={{ width: '1.25rem', height: '1.25rem', color: '#34d399' }} />
          </div>
          <div className="metric-value">{stats.active_connections}</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Last Updated (UTC)</span>
            <RefreshCw style={{ width: '1.25rem', height: '1.25rem', color: '#818cf8' }} />
          </div>
          <div className="metric-sub">{stats.last_updated}</div>
        </div>
      </div>

      {/* Backend Node Distribution */}
      <section>
        <h2 className="section-title">Backend Nodes Distribution</h2>
        <div className="backends-grid">
          {Object.entries(stats.backend_requests || {}).map(([name, count]) => {
            const percentage = stats.total_requests > 0 
              ? ((count / stats.total_requests) * 100).toFixed(1) 
              : 0;

            return (
              <div key={name} className="backend-card">
                <div>
                  <div className="backend-top">
                    <span className="backend-name">{name}</span>
                    <CheckCircle2 style={{ width: '1.25rem', height: '1.25rem', color: '#34d399' }} />
                  </div>
                  <div className="backend-count">{count} <span>requests</span></div>
                </div>

                <div style={{ marginTop: '1.5rem' }}>
                  <div className="progress-info">
                    <span>Traffic Share</span>
                    <span>{percentage}%</span>
                  </div>
                  <div className="progress-bar-bg">
                    <div 
                      className="progress-bar-fill"
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export default App;