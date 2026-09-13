import React, { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  FileText,
  HelpCircle,
  User,
  CheckCircle2,
  RefreshCw,
  Database,
  Search,
  DollarSign,
  BarChart2,
  GraduationCap,
  TrendingUp,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Brain,
  Trash2,
} from 'lucide-react';
import { api } from '../api/client';

/* ─────────── Tool badge config ─────────────────────────────────────── */
const TOOL_META = {
  find_students:                  { icon: Search,       color: 'text-violet-700 bg-violet-50 border-violet-200',   label: 'Student Search'        },
  get_student_profile:            { icon: GraduationCap,color: 'text-blue-700   bg-blue-50   border-blue-200',     label: 'Student Profile'       },
  get_student_fee_summary:        { icon: DollarSign,   color: 'text-emerald-700 bg-emerald-50 border-emerald-200',label: 'Fee Records'           },
  get_student_results:            { icon: BarChart2,    color: 'text-amber-700  bg-amber-50  border-amber-200',    label: 'Results & Marks'       },
  get_collection_summary:         { icon: TrendingUp,   color: 'text-rose-700   bg-rose-50   border-rose-200',     label: 'Collection Summary'    },
  get_students_with_pending_fees: { icon: AlertCircle,  color: 'text-red-700    bg-red-50    border-red-200',      label: 'Pending Fees List'     },
  get_students_by_grade:          { icon: GraduationCap,color: 'text-cyan-700   bg-cyan-50   border-cyan-200',     label: 'Grade Student List'    },
  school_data:                    { icon: Database,     color: 'text-slate-700  bg-slate-50  border-slate-200',    label: 'School Database'       },
  policy_rag:                     { icon: FileText,     color: 'text-indigo-700 bg-indigo-50 border-indigo-200',   label: 'Policy RAG'            },
  groq_tool_calling:              { icon: Sparkles,     color: 'text-purple-700 bg-purple-50 border-purple-200',   label: 'Groq AI + Tools'       },
};

/* ─────────── Grade colour helper ────────────────────────────────────── */
function gradeColor(g) {
  const map = { 'A+': 'text-emerald-700 bg-emerald-50', A: 'text-green-700 bg-green-50', 'B+': 'text-teal-700 bg-teal-50', B: 'text-cyan-700 bg-cyan-50', C: 'text-yellow-700 bg-yellow-50', D: 'text-orange-700 bg-orange-50', F: 'text-red-700 bg-red-50' };
  return map[g] || 'text-slate-600 bg-slate-100';
}

/* ─────────── Data query quick-start prompts ─────────────────────────── */
const DATA_PROMPTS = [
  { label: '⚠️ Pending fees list',   prompt: 'List me all students whose fees are pending'           },
  { label: '👤 Student lookup',      prompt: 'Show me the profile of Ahmed Khan'                     },
  { label: '🧠 Memory follow-up',    prompt: 'What are his pending fees?'                            },
  { label: '📋 Grade 8 students',    prompt: 'List all students in Grade 8'                          },
  { label: '💰 Student fees',        prompt: 'What are the pending dues for roll number 5?'          },
  { label: '📊 Marks & results',     prompt: 'Show results for Ahmed Khan'                           },
  { label: '📈 Collection report',   prompt: 'What is the overall fee collection summary?'           },
  { label: '🔍 Search student',      prompt: 'Find student Bilal Tariq'                              },
];

/* ─────────── Rich structured-data card components ───────────────────── */
function StudentProfileCard({ data }) {
  if (!data?.found) return null;
  const s = data.student;
  return (
    <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center gap-2 font-bold text-blue-800 text-xs">
        <GraduationCap className="w-3.5 h-3.5" />
        Student Profile
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-slate-700">
        <span className="font-semibold text-slate-500">Name</span>       <span>{s.name}</span>
        <span className="font-semibold text-slate-500">Roll #</span>     <span>{s.roll_number}</span>
        <span className="font-semibold text-slate-500">Grade</span>      <span>{s.grade} – {s.section}</span>
        {s.guardian_name && <><span className="font-semibold text-slate-500">Guardian</span><span>{s.guardian_name}</span></>}
        {s.phone         && <><span className="font-semibold text-slate-500">Phone</span>   <span>{s.phone}</span></>}
        {s.date_of_birth && <><span className="font-semibold text-slate-500">DOB</span>     <span>{s.date_of_birth}</span></>}
      </div>
    </div>
  );
}

function FeeSummaryCard({ data }) {
  if (!data?.found) return null;
  const [expanded, setExpanded] = useState(false);
  const t = data.totals;
  const pct = t.invoiced > 0 ? Math.round((t.paid / t.invoiced) * 100) : 0;
  return (
    <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center gap-2 font-bold text-emerald-800 text-xs">
        <DollarSign className="w-3.5 h-3.5" />
        Fee Summary — {data.student.name}
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        {[['Invoiced', t.invoiced, 'text-slate-700'], ['Paid', t.paid, 'text-emerald-700'], ['Pending', t.pending, t.pending > 0 ? 'text-red-600' : 'text-emerald-600']].map(([l, v, cls]) => (
          <div key={l} className="rounded-lg bg-white border border-slate-200 py-1.5 px-1">
            <div className={`font-bold text-sm ${cls}`}>Rs {v.toLocaleString()}</div>
            <div className="text-slate-400 text-[10px]">{l}</div>
          </div>
        ))}
      </div>
      {/* progress bar */}
      <div className="space-y-0.5">
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>Collection Rate</span><span className="font-bold">{pct}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden">
          <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${pct}%` }} />
        </div>
      </div>
      {data.invoices?.length > 0 && (
        <>
          <button onClick={() => setExpanded(e => !e)} className="flex items-center gap-1 text-[10px] text-emerald-700 font-semibold hover:underline">
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {expanded ? 'Hide' : 'Show'} {data.invoices.length} invoice(s)
          </button>
          {expanded && (
            <div className="overflow-x-auto">
              <table className="w-full text-[10px] text-slate-700 border-collapse">
                <thead>
                  <tr className="border-b border-emerald-200 text-slate-500">
                    <th className="text-left py-1 pr-2">Challan</th>
                    <th className="text-left py-1 pr-2">Month</th>
                    <th className="text-right py-1 pr-2">Amount</th>
                    <th className="text-left py-1">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.invoices.map((inv, i) => (
                    <tr key={i} className="border-b border-emerald-100/60">
                      <td className="py-0.5 pr-2 font-mono">{inv.challan_number}</td>
                      <td className="py-0.5 pr-2">{inv.month}</td>
                      <td className="py-0.5 pr-2 text-right">Rs {inv.amount.toLocaleString()}</td>
                      <td className="py-0.5">
                        <span className={`px-1.5 py-0.5 rounded-md font-semibold ${inv.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                          {inv.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ResultsCard({ data }) {
  if (!data?.found || !data.results?.length) return null;
  return (
    <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-amber-800 text-xs">
          <BarChart2 className="w-3.5 h-3.5" />
          Results — {data.student.name}
        </div>
        {data.average_percentage != null && (
          <span className="text-[10px] font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-lg border border-amber-200">
            Avg {data.average_percentage}%
          </span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] text-slate-700 border-collapse">
          <thead>
            <tr className="border-b border-amber-200 text-slate-500">
              <th className="text-left py-1 pr-2">Subject</th>
              <th className="text-right py-1 pr-2">Marks</th>
              <th className="text-right py-1 pr-2">%</th>
              <th className="text-left py-1">Grade</th>
              <th className="text-left py-1">Type</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r, i) => {
              const pct = Math.round((r.marks_obtained / r.total_marks) * 100);
              return (
                <tr key={i} className="border-b border-amber-100/60">
                  <td className="py-0.5 pr-2 font-medium">{r.subject}</td>
                  <td className="py-0.5 pr-2 text-right">{r.marks_obtained}/{r.total_marks}</td>
                  <td className="py-0.5 pr-2 text-right">{pct}%</td>
                  <td className="py-0.5">
                    <span className={`px-1.5 py-0.5 rounded-md font-bold text-[9px] ${gradeColor(r.grade)}`}>{r.grade}</span>
                  </td>
                  <td className="py-0.5 text-slate-400 capitalize">{r.exam_type}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CollectionSummaryCard({ data }) {
  if (!data?.invoices) return null;
  const pct = data.collection_rate;
  return (
    <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center gap-2 font-bold text-rose-800 text-xs">
        <TrendingUp className="w-3.5 h-3.5" />
        School-wide Fee Collection
      </div>
      <div className="grid grid-cols-2 gap-2">
        {[['Total Invoiced', `Rs ${data.invoiced.toLocaleString()}`, 'text-slate-700'], ['Total Collected', `Rs ${data.paid.toLocaleString()}`, 'text-emerald-700'], ['Total Pending', `Rs ${data.pending.toLocaleString()}`, 'text-red-600'], ['Invoices', data.invoices, 'text-slate-700']].map(([l, v, cls]) => (
          <div key={l} className="rounded-lg bg-white border border-slate-200 py-2 px-2">
            <div className={`font-bold text-sm ${cls}`}>{v}</div>
            <div className="text-slate-400 text-[10px]">{l}</div>
          </div>
        ))}
      </div>
      <div className="space-y-0.5">
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>Recovery Rate</span><span className="font-bold">{pct}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: pct > 80 ? '#22c55e' : pct > 50 ? '#f59e0b' : '#ef4444' }} />
        </div>
      </div>
    </div>
  );
}

function FindStudentsCard({ data }) {
  if (!Array.isArray(data) || data.length === 0) return null;
  return (
    <div className="mt-3 rounded-xl border border-violet-200 bg-violet-50/60 p-3 text-[11px] space-y-1.5">
      <div className="flex items-center gap-2 font-bold text-violet-800 text-xs">
        <Search className="w-3.5 h-3.5" />
        {data.length} Student(s) Found
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] text-slate-700 border-collapse">
          <thead>
            <tr className="border-b border-violet-200 text-slate-500">
              <th className="text-left py-1 pr-2">Name</th>
              <th className="text-left py-1 pr-2">Roll #</th>
              <th className="text-left py-1 pr-2">Grade</th>
              <th className="text-left py-1">Section</th>
            </tr>
          </thead>
          <tbody>
            {data.map((s, i) => (
              <tr key={i} className="border-b border-violet-100/60">
                <td className="py-0.5 pr-2 font-medium">{s.name}</td>
                <td className="py-0.5 pr-2 font-mono">{s.roll_number}</td>
                <td className="py-0.5 pr-2">{s.grade}</td>
                <td className="py-0.5">{s.section}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PendingStudentsCard({ data }) {
  if (!data || data.count === 0) return (
    <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-[11px] text-emerald-700 font-semibold">
      ✅ All students are up to date — no pending fees found.
    </div>
  );
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? data.students : data.students.slice(0, 8);
  return (
    <div className="mt-3 rounded-xl border border-red-200 bg-red-50/60 p-3 text-[11px] space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-red-800 text-xs">
          <AlertCircle className="w-3.5 h-3.5" />
          {data.count} Student(s) with Pending Fees
          {data.grade_filter && <span className="font-normal text-red-600"> — {data.grade_filter}</span>}
        </div>
        <span className="text-[10px] font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded-lg border border-red-200">
          Total Rs {data.total_pending.toLocaleString()} due
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] text-slate-700 border-collapse">
          <thead>
            <tr className="border-b border-red-200 text-slate-500">
              <th className="text-left py-1 pr-2">#</th>
              <th className="text-left py-1 pr-2">Name</th>
              <th className="text-left py-1 pr-2">Roll #</th>
              <th className="text-left py-1 pr-2">Grade</th>
              <th className="text-left py-1 pr-2">Guardian</th>
              <th className="text-left py-1 pr-2">Phone</th>
              <th className="text-right py-1 pr-2">Invoices</th>
              <th className="text-right py-1">Pending (Rs)</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((s, i) => (
              <tr key={i} className="border-b border-red-100/60 hover:bg-red-50">
                <td className="py-1 pr-2 text-slate-400">{i + 1}</td>
                <td className="py-1 pr-2 font-semibold text-slate-800">{s.name}</td>
                <td className="py-1 pr-2 font-mono text-slate-600">{s.roll_number}</td>
                <td className="py-1 pr-2">{s.grade}</td>
                <td className="py-1 pr-2 text-slate-500">{s.guardian_name || '—'}</td>
                <td className="py-1 pr-2 text-slate-500">{s.phone || '—'}</td>
                <td className="py-1 pr-2 text-right">
                  <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-bold">{s.pending_invoices}</span>
                </td>
                <td className="py-1 text-right font-bold text-red-700">
                  {s.pending_amount.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
          {data.students.length > 0 && (
            <tfoot>
              <tr className="border-t-2 border-red-300 bg-red-100/40 font-bold">
                <td colSpan={7} className="py-1 pr-2 text-right text-red-700 text-[10px]">Total Outstanding:</td>
                <td className="py-1 text-right text-red-800">Rs {data.total_pending.toLocaleString()}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      {/* Expand/collapse */}
      {data.students.length > 8 && (
        <button onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-1 text-[10px] text-red-700 font-semibold hover:underline">
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? 'Show less' : `Show all ${data.students.length} students`}
        </button>
      )}
    </div>
  );
}

function GradeStudentsCard({ data }) {
  if (!data || data.count === 0) return null;
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? data.students : data.students.slice(0, 8);
  return (
    <div className="mt-3 rounded-xl border border-cyan-200 bg-cyan-50/60 p-3 text-[11px] space-y-2">
      <div className="flex items-center gap-2 font-bold text-cyan-800 text-xs">
        <GraduationCap className="w-3.5 h-3.5" />
        {data.count} Student(s) in {data.grade}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] text-slate-700 border-collapse">
          <thead>
            <tr className="border-b border-cyan-200 text-slate-500">
              <th className="text-left py-1 pr-2">#</th>
              <th className="text-left py-1 pr-2">Name</th>
              <th className="text-left py-1 pr-2">Roll #</th>
              <th className="text-left py-1 pr-2">Section</th>
              <th className="text-left py-1 pr-2">Guardian</th>
              <th className="text-left py-1">Phone</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((s, i) => (
              <tr key={i} className="border-b border-cyan-100/60 hover:bg-cyan-50">
                <td className="py-1 pr-2 text-slate-400">{i + 1}</td>
                <td className="py-1 pr-2 font-semibold text-slate-800">{s.name}</td>
                <td className="py-1 pr-2 font-mono text-slate-600">{s.roll_number}</td>
                <td className="py-1 pr-2">{s.section}</td>
                <td className="py-1 pr-2 text-slate-500">{s.guardian_name || '—'}</td>
                <td className="py-1 text-slate-500">{s.phone || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.students.length > 8 && (
        <button onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-1 text-[10px] text-cyan-700 font-semibold hover:underline">
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? 'Show less' : `Show all ${data.students.length} students`}
        </button>
      )}
    </div>
  );
}

/* ─────────── StructuredData renderer ───────────────────────────────── */
function StructuredData({ toolsUsed, structuredData }) {
  if (!structuredData) return null;
  const tools = toolsUsed || [];

  if (tools.includes('get_students_with_pending_fees') && structuredData.pending_students)
    return <PendingStudentsCard data={structuredData.pending_students} />;
  if (tools.includes('get_students_by_grade') && structuredData.grade_students)
    return <GradeStudentsCard data={structuredData.grade_students} />;
  if (tools.includes('get_student_profile') && structuredData.profile)
    return <StudentProfileCard data={structuredData.profile} />;
  if (tools.includes('get_student_fee_summary') && structuredData.fees)
    return <FeeSummaryCard data={structuredData.fees} />;
  if (tools.includes('get_student_results') && structuredData.results)
    return <ResultsCard data={structuredData.results} />;
  if (tools.includes('get_collection_summary') && structuredData.collection)
    return <CollectionSummaryCard data={structuredData.collection} />;
  if (tools.includes('find_students') && structuredData.students)
    return <FindStudentsCard data={structuredData.students} />;
  return null;
}



/* ─────────── Tool badge ─────────────────────────────────────────────── */
function ToolBadges({ mode, toolsUsed }) {
  const show = [];
  if (toolsUsed?.length) toolsUsed.forEach(t => { if (TOOL_META[t]) show.push(t); });
  else if (mode && TOOL_META[mode]) show.push(mode);

  if (!show.length) return null;
  return (
    <div className="mt-2.5 flex flex-wrap gap-1.5">
      {show.map(key => {
        const meta = TOOL_META[key];
        const Icon = meta.icon;
        return (
          <span key={key} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold border ${meta.color}`}>
            <Icon className="w-3 h-3" />
            {meta.label}
          </span>
        );
      })}
    </div>
  );
}

/* ─────────── Default Initial Greeting ──────────────────────────────── */
const DEFAULT_GREETING = {
  id: 1,
  sender: 'bot',
  text: "Hello! I am the Al-Noor Academy AI Assistant. I can:\n\n• Answer policy questions (fees, exams, admissions, rules) from official school documents\n• Look up live student records, fee status, marks, and collection reports\n• Maintain conversation memory across questions (e.g. ask \"Show me Ahmed Khan\", then follow up with \"What are his pending fees?\")\n\nHow can I help you today?",
  sources: ['Al-Noor Knowledge Base'],
  grounded: true,
  time: 'Just now',
};

/* ─────────── Main component ─────────────────────────────────────────── */
export default function Chatbot() {
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem('educore_chat_history');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {
      console.error('Failed to restore chat history:', e);
    }
    return [DEFAULT_GREETING];
  });

  const [useMemory, setUseMemory] = useState(() => {
    return localStorage.getItem('educore_chat_memory_enabled') !== 'false';
  });

  const [sessionId, setSessionId] = useState(() => {
    let s = localStorage.getItem('educore_chat_session_id');
    if (!s) {
      s = 'sess_' + Math.random().toString(36).substring(2, 11);
      localStorage.setItem('educore_chat_session_id', s);
    }
    return s;
  });

  const [historyLength, setHistoryLength] = useState(0);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [topics, setTopics] = useState([]);
  const [activeTab, setActiveTab] = useState('policy'); // 'policy' | 'data'
  const messagesEndRef = useRef(null);
  const requestControllerRef = useRef(null);

  useEffect(() => { fetchTopics(); return () => requestControllerRef.current?.abort(); }, []);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  // Sync messages to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('educore_chat_history', JSON.stringify(messages));
    } catch (e) {
      console.warn('Failed to save chat to localStorage:', e);
    }
  }, [messages]);

  // Sync memory toggle preference to localStorage
  useEffect(() => {
    localStorage.setItem('educore_chat_memory_enabled', String(useMemory));
  }, [useMemory]);

  const fetchTopics = async () => {
    try { const res = await api.getChatbotTopics(); setTopics(res.data.topics || []); }
    catch (err) { console.error(err); }
  };

  const handleClearChat = async () => {
    const oldSessionId = sessionId;
    const newSessionId = 'sess_' + Math.random().toString(36).substring(2, 11);
    setSessionId(newSessionId);
    localStorage.setItem('educore_chat_session_id', newSessionId);
    setMessages([DEFAULT_GREETING]);
    localStorage.removeItem('educore_chat_history');
    setHistoryLength(0);
    try {
      await api.clearChatHistory(oldSessionId);
    } catch (err) {
      console.error('Error clearing backend session:', err);
    }
  };

  const handleSend = async (queryText) => {
    const text = (queryText || inputQuery).trim();
    if (!text) return;

    setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
    setInputQuery('');
    setLoading(true);

    const controller = new AbortController();
    requestControllerRef.current = controller;

    // Extract recent messages for contextual conversation memory
    const recentHistory = messages
      .filter((m) => m.text)
      .slice(-8)
      .map((m) => ({
        role: m.sender === 'bot' ? 'assistant' : 'user',
        content: m.text,
      }));

    try {
      const res = await api.askChatbot(
        {
          question: text,
          session_id: sessionId,
          use_memory: useMemory,
          history: recentHistory,
        },
        { signal: controller.signal }
      );
      const d = res.data;
      if (d.history_length !== undefined) {
        setHistoryLength(d.history_length);
      }
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: d.answer,
        sources: d.sources || [],
        grounded: d.grounded,
        mode: d.mode,
        toolsUsed: d.tools_used || [],
        structuredData: d.structured_data || null,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);
    } catch (err) {
      if (err.code === 'ERR_CANCELED') return;
      setMessages(prev => [...prev, { id: Date.now() + 1, sender: 'bot', text: 'An error occurred. Please check backend connectivity.', sources: [], grounded: false, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
    } finally {
      if (requestControllerRef.current === controller) { requestControllerRef.current = null; setLoading(false); }
    }
  };

  return (
    <div className="h-[calc(100vh-8.5rem)] flex flex-col md:flex-row gap-6">
      {/* ── Left Sidebar ── */}
      <div className="hidden md:flex flex-col w-80 shrink-0 gap-4">
        {/* AI Engine Status */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 text-white flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">AI Data + Policy Engine</h3>
              <p className="text-[11px] text-slate-400">FAISS RAG · Groq LLM · SQL Tools</p>
            </div>
          </div>
          <div className="space-y-1.5 text-[11px]">
            {[
              { Icon: CheckCircle2, label: 'Policy RAG (FAISS)',    color: 'text-emerald-600' },
              { Icon: CheckCircle2, label: 'Groq LLM tool-calling', color: 'text-emerald-600' },
              { Icon: CheckCircle2, label: 'Student DB queries',    color: 'text-emerald-600' },
              { Icon: CheckCircle2, label: 'Fee record lookups',    color: 'text-emerald-600' },
              { Icon: Brain,        label: `Memory: ${useMemory ? 'Active (Context Saved)' : 'Disabled'}`, color: useMemory ? 'text-purple-600 font-semibold' : 'text-slate-400' },
            ].map(({ Icon, label, color }) => (
              <div key={label} className={`flex items-center gap-1.5 font-medium ${color}`}>
                <Icon className="w-3.5 h-3.5" /> <span>{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Tab switcher */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs flex-1 overflow-hidden flex flex-col">
          <div className="flex border-b border-slate-100">
            {[['policy', 'Policy FAQs', FileText], ['data', 'Data Queries', Database]].map(([key, label, Icon]) => (
              <button key={key} onClick={() => setActiveTab(key)}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[11px] font-semibold transition-colors ${activeTab === key ? 'text-blue-700 border-b-2 border-blue-600 bg-blue-50/60' : 'text-slate-500 hover:text-slate-700'}`}>
                <Icon className="w-3.5 h-3.5" />{label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
            {activeTab === 'policy' && topics.map((t, i) => (
              <button key={i} onClick={() => handleSend(t.prompt)} disabled={loading}
                className="w-full text-left p-2.5 rounded-xl text-xs bg-slate-50 hover:bg-indigo-50/80 hover:text-indigo-700 text-slate-700 font-medium transition-colors border border-slate-200/60 disabled:opacity-50">
                <div className="font-bold text-[11px] text-slate-900 mb-0.5">{t.topic}</div>
                <div className="text-[10px] text-slate-500 line-clamp-1">"{t.prompt}"</div>
              </button>
            ))}

            {activeTab === 'data' && DATA_PROMPTS.map((p, i) => (
              <button key={i} onClick={() => handleSend(p.prompt)} disabled={loading}
                className="w-full text-left p-2.5 rounded-xl text-xs bg-slate-50 hover:bg-violet-50/80 hover:text-violet-700 text-slate-700 font-medium transition-colors border border-slate-200/60 disabled:opacity-50">
                <div className="flex items-center gap-1.5 font-bold text-[11px] text-slate-900 mb-0.5">
                  <Database className="w-3 h-3 text-violet-500" />{p.label}
                </div>
                <div className="text-[10px] text-slate-500 line-clamp-1">"{p.prompt}"</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Chat Window ── */}
      <div className="flex-1 bg-white rounded-2xl border border-slate-200/80 shadow-xs flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-xs">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-900">Al-Noor Academy AI Assistant</h2>
                {/* Memory Toggle Button */}
                <button
                  onClick={() => setUseMemory(!useMemory)}
                  title={useMemory ? "Memory is ON: assistant remembers previous questions in this conversation. Click to toggle OFF." : "Memory is OFF: each question is isolated. Click to toggle ON."}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border transition-all ${
                    useMemory
                      ? 'bg-purple-100 text-purple-700 border-purple-300 hover:bg-purple-200'
                      : 'bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200'
                  }`}
                >
                  <Brain className={`w-3 h-3 ${useMemory ? 'text-purple-600 animate-pulse' : 'text-slate-400'}`} />
                  <span>Memory: {useMemory ? 'ON' : 'OFF'}</span>
                  {useMemory && historyLength > 0 && (
                    <span className="ml-0.5 px-1 py-0.2 rounded-full bg-purple-200 text-purple-800 text-[9px]">
                      {Math.floor(historyLength / 2)} turns
                    </span>
                  )}
                </button>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium mt-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>Policy RAG + Live DB Tools Active</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={handleClearChat}
              disabled={loading}
              title="Clear conversation history & reset memory"
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-slate-500 hover:text-red-600 hover:bg-red-50 border border-slate-200/80 transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline font-medium text-[11px]">Clear Memory</span>
            </button>
            <button
              onClick={handleClearChat}
              disabled={loading}
              title="Reset Chat"
              className="min-h-9 min-w-9 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4" role="log" aria-live="polite">
          {messages.map((m) => {
            const isBot = m.sender === 'bot';
            return (
              <div key={m.id} className={`flex gap-3 ${isBot ? 'mr-auto max-w-2xl' : 'ml-auto max-w-xl flex-row-reverse'}`}>
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${isBot ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-xs' : 'bg-slate-900 text-white'}`}>
                  {isBot ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>

                {/* Bubble */}
                <div className="space-y-1.5 min-w-0">
                  <div className={`p-4 rounded-2xl text-xs leading-relaxed ${isBot ? 'bg-slate-100 text-slate-800 rounded-tl-none border border-slate-200/60' : 'bg-blue-600 text-white rounded-tr-none shadow-sm'}`}>
                    <p className="whitespace-pre-wrap">{m.text}</p>

                    {/* Tool badges */}
                    {isBot && <ToolBadges mode={m.mode} toolsUsed={m.toolsUsed} />}

                    {/* Structured data cards */}
                    {isBot && <StructuredData toolsUsed={m.toolsUsed} structuredData={m.structuredData} />}

                    {/* Sources */}
                    {isBot && m.sources?.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-200/80 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-500">
                        <span className="font-bold uppercase tracking-wider text-slate-400">Sources:</span>
                        {m.sources.map((src, i) => (
                          <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 font-semibold">
                            <FileText className="w-2.5 h-2.5 text-blue-600" />{src}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Grounding warning */}
                    {isBot && m.grounded === false && (
                      <div className="mt-2 flex items-center gap-1 text-[10px] text-amber-600 font-semibold">
                        <AlertCircle className="w-3 h-3" /> Response may be outside known school records
                      </div>
                    )}
                  </div>
                  <p className={`text-[10px] text-slate-400 ${isBot ? 'text-left' : 'text-right'}`}>{m.time}</p>
                </div>
              </div>
            );
          })}

          {/* Typing indicator */}
          {loading && (
            <div className="flex gap-3 max-w-xl mr-auto" role="status">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-3.5 rounded-2xl rounded-tl-none bg-slate-100 border border-slate-200 text-xs text-slate-600 flex items-center gap-2">
                <div className="flex gap-1">
                  {[0, 0.15, 0.3].map((delay, i) => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-bounce" style={{ animationDelay: `${delay}s` }} />
                  ))}
                </div>
                <span>Consulting knowledge base &amp; school database…</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={e => { e.preventDefault(); handleSend(); }}
          className="p-3.5 border-t border-slate-100 bg-white flex items-center gap-2">
          <input
            type="text"
            value={inputQuery}
            onChange={e => setInputQuery(e.target.value)}
            placeholder='Ask about students, fees, results, or school policies…'
            disabled={loading}
            className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white disabled:opacity-50"
          />
          <button type="submit" disabled={loading || !inputQuery.trim()}
            className="min-h-11 min-w-11 p-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-xs transition-colors disabled:opacity-40">
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
