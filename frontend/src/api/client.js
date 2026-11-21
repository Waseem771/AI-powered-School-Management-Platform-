import axios from 'axios';
import { sessionEndedPath } from '../lib/access';
import { CHANGE_PASSWORD_PATH, PASSWORD_CHANGE_REQUIRED, clearSession, setPasswordChangeRequired } from '../lib/session';

// Production builds get this from VITE_API_URL (see frontend/.env.production).
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Automatically attach Bearer token from localStorage for cross-domain auth
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('educore_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercept 401s and redirect to login if session expires
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // If unauthorized on protected route, redirect to login
      if (window.location.pathname !== '/login') {
        clearSession();
        window.location.href = sessionEndedPath();
      }
    }
    // After an administrator's reset the server refuses everything but choosing a new password.
    if (error.response?.status === 403 && error.response.data?.detail === PASSWORD_CHANGE_REQUIRED) {
      setPasswordChangeRequired(true);
      if (window.location.pathname !== CHANGE_PASSWORD_PATH) window.location.href = CHANGE_PASSWORD_PATH;
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Auth
  login: (username, password) => client.post('/auth/login', { username, password }),
  logout: () => client.post('/auth/logout'),
  changePassword: (currentPassword, newPassword) =>
    client.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),
  getMe: () => client.get('/auth/me'),
  // Self-service password reset by emailed link (teachers and parents)
  forgotPassword: (email) => client.post('/auth/forgot-password', { email }),
  checkResetLink: (token) => client.post('/auth/reset-password/check', { token }),
  resetPasswordWithLink: (token, newPassword) => client.post('/auth/reset-password', { token, new_password: newPassword }),

  // Teacher accounts (administrators) and the teacher's own portal
  getTeachers: (options) => client.get('/teachers', options),
  createTeacher: (data) => client.post('/teachers', data),
  resetTeacherPassword: (id, newPassword) => client.post(`/teachers/${id}/reset-password`, { new_password: newPassword }),
  updateTeacherEmail: (id, email, adminPassword) => client.put(`/teachers/${id}/email`, { email, admin_password: adminPassword }),
  activateTeacher: (id) => client.post(`/teachers/${id}/activate`),
  deactivateTeacher: (id) => client.post(`/teachers/${id}/deactivate`),
  getTeacherProfile: (options) => client.get('/teacher/profile', options),

  // Parent accounts and result publishing (administrators)
  getParents: (options) => client.get('/parents', options),
  createParent: (data) => client.post('/parents', data),
  resetParentPassword: (id, newPassword) => client.post(`/parents/${id}/reset-password`, { new_password: newPassword }),
  updateParentEmail: (id, email, adminPassword) => client.put(`/parents/${id}/email`, { email, admin_password: adminPassword }),
  activateParent: (id) => client.post(`/parents/${id}/activate`),
  deactivateParent: (id) => client.post(`/parents/${id}/deactivate`),
  linkParentChild: (parentId, data) => client.post(`/parents/${parentId}/children`, data),
  unlinkParentChild: (parentId, studentId) => client.delete(`/parents/${parentId}/children/${studentId}`),
  getResultPublishing: (options) => client.get('/result-publishing', options),
  setResultPublished: (data) => client.put('/result-publishing', data),

  // The parent's own portal
  getParentProfile: (options) => client.get('/parent/profile', options),
  getParentChildren: (options) => client.get('/parent/children', options),
  getParentChildAttendance: (id, params, options) => client.get(`/parent/children/${id}/attendance`, { params, ...options }),
  getParentChildResults: (id, params, options) => client.get(`/parent/children/${id}/results`, { params, ...options }),
  getParentChildFees: (id, options) => client.get(`/parent/children/${id}/fees`, options),
  getParentReportCardPdf: (id, params) =>
    client.get(`/parent/children/${id}/report-card/pdf`, { params, responseType: 'blob' }).then((response) => response.data),
  getParentChallanPdf: (id, invoiceId) =>
    client.get(`/parent/children/${id}/invoices/${invoiceId}/challan/pdf`, { responseType: 'blob' }).then((response) => response.data),
  getParentReceiptPdf: (id, paymentId) =>
    client.get(`/parent/children/${id}/payments/${paymentId}/receipt`, { responseType: 'blob' }).then((response) => response.data),

  // Teacher assignments (administrators)
  getAssignmentOptions: (options) => client.get('/teacher-assignments/options', options),
  getAssignments: (params, options) => client.get('/teacher-assignments', { params, ...options }),
  createAssignment: (data) => client.post('/teacher-assignments', data),
  updateAssignment: (id, data) => client.put(`/teacher-assignments/${id}`, data),
  deleteAssignment: (id) => client.delete(`/teacher-assignments/${id}`),

  // Teacher classes and attendance
  getMyClasses: (options) => client.get('/teacher/classes', options),
  getMyClass: (id, options) => client.get(`/teacher/classes/${id}`, options),
  getClassAttendance: (id, date, options) => client.get(`/teacher/classes/${id}/attendance`, { params: { date }, ...options }),
  saveClassAttendance: (id, data) => client.put(`/teacher/classes/${id}/attendance`, data),
  getClassHistory: (id, params, options) => client.get(`/teacher/classes/${id}/history`, { params, ...options }),

  // Attendance (administrators)
  getAttendanceOverview: (params, options) => client.get('/attendance/overview', { params, ...options }),
  getAttendanceClassDay: (params, options) => client.get('/attendance/class-day', { params, ...options }),
  correctAttendanceClassDay: (data) => client.put('/attendance/class-day', data),
  getAttendanceMonthly: (params, options) => client.get('/attendance/monthly', { params, ...options }),
  getFrequentAbsentees: (params, options) => client.get('/attendance/frequent-absentees', { params, ...options }),
  getStudentAttendance: (id, params, options) => client.get(`/attendance/students/${id}/history`, { params, ...options }),
  getAttendanceChanges: (params, options) => client.get('/attendance/changes', { params, ...options }),
  getAttendanceReport: (params, options) => client.get('/attendance/report', { params, ...options }),
  getAttendanceCsv: (params) => client.get('/attendance/export.csv', { params, responseType: 'blob' }).then((r) => r.data),

  // Students
  getStudents: (params, options) => client.get('/students', { params, ...options }),
  getStudent: (id, options) => client.get(`/students/${id}`, options),
  createStudent: (data) => client.post('/students', data),
  updateStudent: (id, data) => client.put(`/students/${id}`, data),
  deleteStudent: (id) => client.delete(`/students/${id}`),
  archiveStudent: (id) => client.post(`/students/${id}/archive`),
  restoreStudent: (id) => client.post(`/students/${id}/restore`),

  // Fees
  getFees: (params, options) => client.get('/fees', { params, ...options }),
  getStudentFeeSummary: (studentId, options) => client.get(`/fees/student/${studentId}/summary`, options),
  getReceiptPdf: (paymentId) =>
    client.get(`/fees/payments/${paymentId}/receipt`, { responseType: 'blob' }).then((response) => response.data),
  getFeeSummary: () => client.get('/fees/summary'),
  getInvoicePayments: (invoiceId, options) => client.get(`/fees/${invoiceId}/payments`, options),
  generateChallan: (data) => client.post('/fees/generate', data),
  payInvoice: (id, data) => client.post(`/fees/${id}/pay`, data),
  getChallanPdf: (invoiceId) =>
    client.get(`/fees/${invoiceId}/pdf`, { responseType: 'blob' }).then((response) => response.data),

  // Results
  getStudentResults: (studentId, params, options) => client.get(`/results/${studentId}`, { params, ...options }),
  getClassMarks: (params, options) => client.get('/results/class', { params, ...options }),
  saveClassMarks: (data) => client.post('/results/class', data),
  enterMarks: (data) => client.post('/results', data),
  getReportCardPdf: (studentId, params) =>
    client
      .get(`/results/${studentId}/report-card/pdf`, { params, responseType: 'blob' })
      .then((response) => response.data),

  // Dashboard
  getDashboardStats: (options) => client.get('/dashboard/stats', options),
  getSchoolInfo: (options) => client.get('/school/info', options),
  getPublicSchool: (options) => client.get('/school/public', options),
  getRecentActivity: (options) => client.get('/dashboard/activity', options),

  // AI At-Risk
  getAtRiskStudents: (params) => client.get('/ai/at-risk', { params }),
  getStudentRiskDetail: (studentId, options) => client.get(`/ai/at-risk/${studentId}`, options),
  simulateRisk: (payload, options) => client.post('/ai/simulate', payload, options),

  // Admissions (new students)
  getAdmissionOptions: (options) => client.get('/admissions/options', options),
  getAdmissionStats: (options) => client.get('/admissions/stats', options),
  getApplications: (params, options) => client.get('/admissions', { params, ...options }),
  getApplication: (id, options) => client.get(`/admissions/${id}`, options),
  createApplication: (data) => client.post('/admissions', data),
  updateApplication: (id, data) => client.put(`/admissions/${id}`, data),
  changeApplicationStatus: (id, data) => client.post(`/admissions/${id}/status`, data),
  setApplicationDocument: (id, data) => client.put(`/admissions/${id}/documents`, data),
  addApplicationAssessment: (id, data) => client.post(`/admissions/${id}/assessments`, data),
  getNextRollNumber: (options) => client.get('/admissions/next-roll-number', options),
  enrollApplicant: (id, data) => client.post(`/admissions/${id}/enroll`, data),
  getApplicationFeePolicy: (id, options) => client.get(`/admissions/${id}/fee-policy`, options),
  getAdmissionReminder: (id, language) => client.post(`/admissions/${id}/assistant/reminder`, { language }),
  getAdmissionSummary: (id) => client.get(`/admissions/${id}/assistant/summary`),
  askAdmissionPolicy: (question) => client.post('/admissions/assistant/policy', { question }),

  // Chatbot
  askChatbot: (payload, options) => {
    const body = typeof payload === 'string' ? { question: payload } : payload;
    return client.post('/chatbot/ask', body, options);
  },
  getChatHistory: (sessionId) => client.get(`/chatbot/history/${sessionId}`),
  clearChatHistory: (sessionId) => client.delete(`/chatbot/history/${sessionId}`),
  getChatbotTopics: () => client.get('/chatbot/topics'),
  getChatbotStatus: () => client.get('/chatbot/status'),
};

export default client;
