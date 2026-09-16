import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from './api';

function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = { email, password, first_name: firstName, last_name: lastName };
      if (companyName) {
        data.company_name = companyName;
      }
      await api.post('register/', data);
      navigate('/login');
    } catch (err) {
      setError('Registration failed. Email might be in use.');
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '50px auto', padding: '20px', border: '1px solid #ccc' }}>
      <h2>Register</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '10px' }}>
          <label>First Name:</label><br />
          <input type="text" value={firstName} onChange={e => setFirstName(e.target.value)} required style={{ width: '100%' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Last Name:</label><br />
          <input type="text" value={lastName} onChange={e => setLastName(e.target.value)} required style={{ width: '100%' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Email:</label><br />
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} required style={{ width: '100%' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Password:</label><br />
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} required style={{ width: '100%' }} />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label>Company Name (Optional):</label><br />
          <input type="text" value={companyName} onChange={e => setCompanyName(e.target.value)} style={{ width: '100%' }} placeholder="Creates a new company" />
        </div>
        <button type="submit">Register</button>
      </form>
      <p style={{ marginTop: '10px' }}>
        Already have an account? <Link to="/login">Login here</Link>
      </p>
    </div>
  );
}

export default Register;
