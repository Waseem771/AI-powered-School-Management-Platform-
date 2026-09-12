import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Students from './pages/Students';
import Fees from './pages/Fees';
import Results from './pages/Results';
import AtRisk from './pages/AtRisk';
import Chatbot from './pages/Chatbot';

// Route protector checking token in localStorage
function ProtectedRoute({ children }) {
  const token = localStorage.getItem('educore_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />

        {/* Protected Admin Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="students" element={<Students />} />
          <Route path="fees" element={<Fees />} />
          <Route path="results" element={<Results />} />
          <Route path="at-risk" element={<AtRisk />} />
          <Route path="chatbot" element={<Chatbot />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}
