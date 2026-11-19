import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import { ToastProvider } from './components/ui/Toast';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Students from './pages/Students';
import StudentProfile from './pages/StudentProfile';
import Fees from './pages/Fees';
import Results from './pages/Results';
import AtRisk from './pages/AtRisk';
import Chatbot from './pages/Chatbot';
import Admissions from './pages/Admissions';
import AdmissionForm from './pages/AdmissionForm';
import AdmissionDetail from './pages/AdmissionDetail';
import Teachers from './pages/Teachers';
import TeacherDashboard from './pages/TeacherDashboard';
import TeacherProfile from './pages/TeacherProfile';
import TeacherClasses from './pages/TeacherClasses';
import TeacherClassDetail from './pages/TeacherClassDetail';
import TeacherAttendance from './pages/TeacherAttendance';
import TeacherAttendanceHistory from './pages/TeacherAttendanceHistory';
import TeacherAssignments from './pages/TeacherAssignments';
import Attendance from './pages/Attendance';
import AttendanceReport from './pages/AttendanceReport';
import { canAccessPath, homePathFor } from './lib/access';
import { getStoredUser } from './lib/session';

// The backend enforces access on every request. This only keeps the client from
// rendering private navigation before a user signs in.
function ProtectedRoute({ children }) {
  const user = localStorage.getItem('educore_user');
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

// Sends each role to its own home, and away from screens it has no use for. Backend still decides.
function RequireAccess() {
  const { pathname } = useLocation();
  const user = getStoredUser();
  if (!canAccessPath(user, pathname)) {
    return <Navigate to={homePathFor(user)} replace />;
  }
  return <Outlet />;
}

function HomeRedirect() {
  return <Navigate to={homePathFor(getStoredUser())} replace />;
}

export default function App() {
  return (
    <ToastProvider>
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
          <Route index element={<HomeRedirect />} />
          <Route element={<RequireAccess />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="students" element={<Students />} />
          <Route path="students/:id" element={<StudentProfile />} />
          <Route path="fees" element={<Fees />} />
          <Route path="results" element={<Results />} />
          <Route path="at-risk" element={<AtRisk />} />
          <Route path="chatbot" element={<Chatbot />} />
          <Route path="admissions" element={<Admissions />} />
          <Route path="admissions/new" element={<AdmissionForm />} />
          <Route path="admissions/:id" element={<AdmissionDetail />} />
          <Route path="admissions/:id/edit" element={<AdmissionForm />} />
          <Route path="teachers" element={<Teachers />} />
          <Route path="teacher/dashboard" element={<TeacherDashboard />} />
          <Route path="teacher/profile" element={<TeacherProfile />} />
          <Route path="teacher/classes" element={<TeacherClasses />} />
          <Route path="teacher/classes/:id" element={<TeacherClassDetail />} />
          <Route path="teacher/classes/:id/attendance" element={<TeacherAttendance />} />
          <Route path="teacher/classes/:id/history" element={<TeacherAttendanceHistory />} />
          <Route path="teacher-assignments" element={<TeacherAssignments />} />
          <Route path="attendance" element={<Attendance />} />
          <Route path="attendance/report" element={<AttendanceReport />} />
          </Route>
        </Route>

        <Route path="*" element={<HomeRedirect />} />
      </Routes>
    </Router>
    </ToastProvider>
  );
}
