import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from './api';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const statsRes = await api.get('reports/dashboard/');
        setStats(statsRes.data);

        const ticketsRes = await api.get('itsm/tickets/');
        setTickets(ticketsRes.data);
      } catch (err) {
        if (err.response && err.response.status === 401) {
          navigate('/login');
        } else {
          setError('Failed to load dashboard data.');
        }
      }
    };
    fetchData();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    navigate('/login');
  };

  return (
    <div style={{ padding: '20px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>ITSM Dashboard</h1>
        <button onClick={handleLogout}>Logout</button>
      </header>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {stats ? (
        <div>
          <h2>Statistics</h2>
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '30px' }}>
            <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', minWidth: '200px' }}>
              <h3>Tickets by Status</h3>
              <ul>
                {stats.status_counts.map(s => (
                  <li key={s.status}>{s.status}: {s.count}</li>
                ))}
              </ul>
            </div>

            <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', minWidth: '200px' }}>
              <h3>Performance</h3>
              <p>Average Resolution Time: {stats.average_resolution_time || 'N/A'}</p>
              <p>SLA Violations: {stats.sla_violation_percentage}%</p>
              <p>Average Client Rating: {stats.average_rating || 'N/A'}/5</p>
            </div>

            {stats.workload && stats.workload.length > 0 && (
              <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', minWidth: '200px' }}>
                <h3>IT Staff Workload</h3>
                <ul>
                  {stats.workload.map(w => (
                    <li key={w.assignee__email}>{w.assignee__email || 'Unassigned'}: {w.count} open</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <h2>Recent Tickets</h2>
          {tickets.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f5f5f5', textAlign: 'left' }}>
                  <th style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>ID</th>
                  <th style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>Title</th>
                  <th style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>Status</th>
                  <th style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>Priority</th>
                  <th style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>Created At</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map(ticket => (
                  <tr key={ticket.id}>
                    <td style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>{ticket.id}</td>
                    <td style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>{ticket.title}</td>
                    <td style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>{ticket.status}</td>
                    <td style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>{ticket.priority}</td>
                    <td style={{ padding: '10px', borderBottom: '1px solid #ddd' }}>{new Date(ticket.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
             <p>No tickets found.</p>
          )}
        </div>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}

export default Dashboard;
