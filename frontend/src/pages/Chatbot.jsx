import React, { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  FileText,
  HelpCircle,
  User,
  CheckCircle2,
  Database,
  Search,
  DollarSign,
  BarChart2,
  GraduationCap,
  TrendingUp,
  AlertCircle,
  Brain,
  Trash2,
} from 'lucide-react';
import { api } from '../api/client';
import StructuredData from '../components/ChatCards';
import { chatStatusSummary, describeChatStatus } from '../lib/chatStatus';
import { apiErrorMessage } from '../lib/errors';

/* ─────────── Tool badge config ─────────────────────────────────────── */
const TOOL_META = {
  find_students:                  { icon: Search,       color: 'text-violet-700 bg-violet-50 border-violet-200',   label: 'Student Search'        },
  get_student_profile:            { icon: GraduationCap,color: 'text-blue-700   bg-blue-50   border-blue-200',     label: 'Student Profile'       },
  get_student_fee_summary:        { icon: DollarSign,   color: 'text-emerald-700 bg-emerald-50 border-emerald-200',label: 'Fee Records'           },
  get_student_results:            { icon: BarChart2,    color: 'text-amber-700  bg-amber-50  border-amber-200',    label: 'Results & Marks'       },
  get_collection_summary:         { icon: TrendingUp,   color: 'text-rose-700   bg-rose-50   border-rose-200',     label: 'Collection Summary'    },
  get_students_with_pending_fees: { icon: AlertCircle,  color: 'text-red-700    bg-red-50    border-red-200',      label: 'Pending Fees List'     },
  get_students_by_grade:          { icon: GraduationCap,color: 'text-cyan-700   bg-cyan-50   border-cyan-200',     label: 'Grade Student List'    },
  get_student_counts:             { icon: GraduationCap,color: 'text-slate-700  bg-slate-50  border-slate-200',    label: 'Student Counts'        },
  get_top_students:               { icon: BarChart2,    color: 'text-amber-700  bg-amber-50  border-amber-200',    label: 'Top Students'          },
  get_subject_averages:           { icon: BarChart2,    color: 'text-amber-700  bg-amber-50  border-amber-200',    label: 'Subject Averages'      },
  get_at_risk_students:           { icon: AlertCircle,  color: 'text-orange-700 bg-orange-50 border-orange-200',   label: 'Risk Estimates'        },
  get_student_risk:               { icon: AlertCircle,  color: 'text-orange-700 bg-orange-50 border-orange-200',   label: 'Risk Estimate'         },
  get_monthly_collection:         { icon: TrendingUp,   color: 'text-rose-700   bg-rose-50   border-rose-200',     label: 'Monthly Collection'    },
  school_data:                    { icon: Database,     color: 'text-slate-700  bg-slate-50  border-slate-200',    label: 'School Database'       },
  policy_rag:                     { icon: FileText,     color: 'text-indigo-700 bg-indigo-50 border-indigo-200',   label: 'Policy Documents'      },
  groq_tool_calling:              { icon: Sparkles,     color: 'text-purple-700 bg-purple-50 border-purple-200',   label: 'AI + School Database'  },
};

/* ─────────── Data query quick-start prompts ─────────────────────────── */
const DATA_PROMPTS = [
  { label: '⚠️ Pending fees list',   prompt: 'List me all students whose fees are pending'           },
  { label: '👤 Student lookup',      prompt: 'Show me the profile of Ahmed Khan'                     },
  { label: '🧠 Memory follow-up',    prompt: 'What are his pending fees?'                            },
  { label: '📋 Grade 8 students',    prompt: 'List all students in Grade 8'                          },
  { label: '💰 Student fees',        prompt: 'What are the pending dues for roll number 045?'        },
  { label: '👥 Student count',       prompt: 'How many students are there?'                          },
  { label: '🏆 Top students',        prompt: 'Who are the top students?'                             },
  { label: '📚 Subject averages',    prompt: 'Show the subject averages'                             },
  { label: '🗓️ Monthly fees',        prompt: 'Show the monthly fee collection'                       },
  { label: '🔎 Risk estimates',      prompt: 'Which students are at risk?'                           },
  { label: '📊 Marks & results',     prompt: 'Show results for Ahmed Khan'                           },
  { label: '📈 Collection report',   prompt: 'What is the overall fee collection summary?'           },
  { label: '🔍 Search student',      prompt: 'Find student Bilal Tariq'                              },
];

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
const MAX_HISTORY_MESSAGE_LENGTH = 4000;
const DEFAULT_GREETING = {
  id: 1,
  sender: 'bot',
  text: "Hello! I am the school assistant. I can:\n\n• Answer policy questions (fees, exams, admissions, rules) from official school documents\n• Look up live student records, fee status, marks, and collection reports\n• Maintain conversation memory across questions (e.g. ask \"Show roll number 045\", then follow up with \"What are his pending fees?\")\n\nHow can I help you today?",
  sources: [],
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
  const [status, setStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('policy'); // 'policy' | 'data'
  const messagesEndRef = useRef(null);
  const requestControllerRef = useRef(null);

  useEffect(() => {
    fetchTopics();
    fetchStatus();
    return () => requestControllerRef.current?.abort();
  }, []);
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

  const fetchStatus = async () => {
    try { const res = await api.getChatbotStatus(); setStatus(res.data); }
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
      .filter((m) => m.text && m.id !== DEFAULT_GREETING.id)
      .slice(-8)
      .map((m) => ({
        role: m.sender === 'bot' ? 'assistant' : 'user',
        content: m.text.slice(0, MAX_HISTORY_MESSAGE_LENGTH),
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
      fetchStatus();
    } catch (err) {
      if (err.code === 'ERR_CANCELED') return;
      setMessages(prev => [...prev, { id: Date.now() + 1, sender: 'bot', text: apiErrorMessage(err), sources: [], grounded: false, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
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
            <div className="w-8 h-8 rounded-lg bg-navy-800 text-white flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">What is running</h3>
              <p className="text-xs text-slate-600">Checked with the server</p>
            </div>
          </div>
          <div className="space-y-1.5 text-xs">
            {describeChatStatus(status).map(({ label, tone }) => {
              const color = { ok: 'text-emerald-600', warn: 'text-amber-600', off: 'text-slate-500' }[tone];
              const Icon = tone === 'ok' ? CheckCircle2 : AlertCircle;
              return (
                <div key={label} className={`flex items-center gap-1.5 font-medium ${color}`}>
                  <Icon className="w-3.5 h-3.5 shrink-0" /> <span>{label}</span>
                </div>
              );
            })}
            <div className={`flex items-center gap-1.5 font-medium ${useMemory ? 'text-purple-600' : 'text-slate-400'}`}>
              <Brain className="w-3.5 h-3.5 shrink-0" /> <span>Conversation memory: {useMemory ? 'on' : 'off'}</span>
            </div>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs flex-1 overflow-hidden flex flex-col">
          <div className="flex border-b border-slate-100">
            {[['policy', 'Policy FAQs', FileText], ['data', 'Data Queries', Database]].map(([key, label, Icon]) => (
              <button key={key} onClick={() => setActiveTab(key)}
                className={`flex-1 flex min-h-11 items-center justify-center gap-1.5 text-sm font-semibold transition-colors ${activeTab === key ? 'text-blue-700 border-b-2 border-blue-600 bg-blue-50/60' : 'text-slate-500 hover:text-slate-700'}`}>
                <Icon className="w-3.5 h-3.5" />{label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
            {activeTab === 'policy' && topics.map((t, i) => (
              <button key={i} onClick={() => handleSend(t.prompt)} disabled={loading}
                className="w-full text-left p-2.5 rounded-xl text-xs bg-slate-50 hover:bg-indigo-50/80 hover:text-indigo-700 text-slate-700 font-medium transition-colors border border-slate-200/60 disabled:opacity-50">
                <div className="font-bold text-xs text-slate-900 mb-0.5">{t.topic}</div>
                <div className="text-xs text-slate-600 line-clamp-1">"{t.prompt}"</div>
              </button>
            ))}

            {activeTab === 'data' && DATA_PROMPTS.map((p, i) => (
              <button key={i} onClick={() => handleSend(p.prompt)} disabled={loading}
                className="w-full text-left p-2.5 rounded-xl text-xs bg-slate-50 hover:bg-violet-50/80 hover:text-violet-700 text-slate-700 font-medium transition-colors border border-slate-200/60 disabled:opacity-50">
                <div className="flex items-center gap-1.5 font-bold text-xs text-slate-900 mb-0.5">
                  <Database className="w-3 h-3 text-violet-500" />{p.label}
                </div>
                <div className="text-xs text-slate-600 line-clamp-1">"{p.prompt}"</div>
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
            <div className="w-9 h-9 shrink-0 rounded-xl bg-navy-800 flex items-center justify-center text-white">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-900">{status?.school ? `${status.school} Assistant` : 'School Assistant'}</h2>
                {/* Memory Toggle Button */}
                <button
                  onClick={() => setUseMemory(!useMemory)}
                  title={useMemory ? "Memory is ON: assistant remembers previous questions in this conversation. Click to toggle OFF." : "Memory is OFF: each question is isolated. Click to toggle ON."}
                  className={`inline-flex min-h-11 items-center gap-1 rounded-xl border px-3 text-xs font-semibold transition-colors ${
                    useMemory
                      ? 'bg-purple-100 text-purple-700 border-purple-300 hover:bg-purple-200'
                      : 'bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200'
                  }`}
                >
                  <Brain className={`w-3.5 h-3.5 ${useMemory ? 'text-purple-600' : 'text-slate-500'}`} />
                  <span>Memory: {useMemory ? 'ON' : 'OFF'}</span>
                  {useMemory && historyLength > 0 && (
                    <span className="ml-0.5 px-1 py-0.2 rounded-full bg-purple-200 text-purple-800 text-[9px]">
                      {Math.floor(historyLength / 2)} turns
                    </span>
                  )}
                </button>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-medium mt-0.5">
                <span>{chatStatusSummary(status)}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={handleClearChat}
              disabled={loading}
              title="Clear conversation history & reset memory"
              className="flex min-h-11 items-center gap-1 px-3 rounded-xl text-sm text-slate-700 hover:text-rose-800 hover:bg-rose-50 border border-slate-300 transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline font-medium">Clear Chat</span>
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
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${isBot ? 'bg-navy-800 text-white' : 'bg-brand-600 text-white'}`}>
                  {isBot ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>

                {/* Bubble */}
                <div className="space-y-1.5 min-w-0">
                  <div className={`p-4 rounded-2xl text-sm leading-relaxed ${isBot ? 'bg-slate-100 text-slate-800 rounded-tl-none border border-slate-200/60' : 'bg-blue-600 text-white rounded-tr-none shadow-sm'}`}>
                    <p className="whitespace-pre-wrap">{m.text}</p>

                    {/* Tool badges */}
                    {isBot && <ToolBadges mode={m.mode} toolsUsed={m.toolsUsed} />}

                    {/* Structured data cards */}
                    {isBot && <StructuredData structuredData={m.structuredData} />}

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
                        <AlertCircle className="w-3 h-3" /> Not answered from school records or policies
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
              <div className="w-8 h-8 rounded-lg bg-navy-800 text-white flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-3.5 rounded-2xl rounded-tl-none bg-slate-100 border border-slate-200 text-xs text-slate-600 flex items-center gap-2">
                <div className="flex gap-1">
                  {[0, 0.15, 0.3].map((delay, i) => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-bounce" style={{ animationDelay: `${delay}s` }} />
                  ))}
                </div>
                <span>Checking school records and policies…</span>
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
            maxLength={1000}
            disabled={loading}
            className="min-h-11 flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-base text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-600 disabled:opacity-50 sm:text-sm"
          />
          <button type="submit" disabled={loading || !inputQuery.trim()}
            aria-label="Send" className="min-h-11 min-w-11 flex items-center justify-center bg-brand-600 hover:bg-brand-700 text-white rounded-xl transition-colors disabled:opacity-40">
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
