import React, { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  FileText,
  ShieldCheck,
  HelpCircle,
  Clock,
  User,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import { api } from '../api/client';

export default function Chatbot() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'bot',
      text: "Hello! I am the official Al-Noor Academy Policy Assistant. I am grounded directly in our school's official regulations, examination criteria, fee schedules, admissions, and academic calendars. How can I assist you today?",
      sources: ['Al-Noor Knowledge Base'],
      grounded: true,
      time: 'Just now'
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [topics, setTopics] = useState([]);
  const messagesEndRef = useRef(null);
  const requestControllerRef = useRef(null);

  useEffect(() => {
    fetchTopics();
    return () => requestControllerRef.current?.abort();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchTopics = async () => {
    try {
      const res = await api.getChatbotTopics();
      setTopics(res.data.topics || []);
    } catch (err) {
      console.error('Error fetching chatbot topics:', err);
    }
  };

  const handleSend = async (queryText) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim()) return;

    const userMessage = {
      id: Date.now(),
      sender: 'user',
      text: textToSend,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setLoading(true);
    const controller = new AbortController();
    requestControllerRef.current = controller;

    try {
      const res = await api.askChatbot(textToSend, { signal: controller.signal });
      const botMessage = {
        id: Date.now() + 1,
        sender: 'bot',
        text: res.data.answer,
        sources: res.data.sources || [],
        grounded: res.data.grounded,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      if (err.code === 'ERR_CANCELED') return;
      const errorMessage = {
        id: Date.now() + 1,
        sender: 'bot',
        text: 'An error occurred while consulting the school policy knowledge base. Please check backend connectivity.',
        sources: [],
        grounded: false,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      if (requestControllerRef.current === controller) {
        requestControllerRef.current = null;
        setLoading(false);
      }
    }
  };

  const handleTopicClick = (prompt) => {
    handleSend(prompt);
  };

  return (
    <div className="h-[calc(100vh-8.5rem)] flex flex-col md:flex-row gap-6">
      {/* Left Column: Topics & Knowledge Info */}
      <div className="hidden md:flex flex-col w-80 shrink-0 gap-4">
        {/* Knowledge Base Status Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">RAG Knowledge Engine</h3>
              <p className="text-[11px] text-slate-400">FAISS + Groq LLaMA 3</p>
            </div>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed mb-3">
            All responses are retrieved and verified from 5 school policy documents to prevent AI hallucinations.
          </p>
          <div className="space-y-1 text-[11px] font-medium text-slate-600">
            <div className="flex items-center gap-1.5 text-emerald-700">
              <CheckCircle2 className="w-3.5 h-3.5" /> <span>fee_policy.txt</span>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-700">
              <CheckCircle2 className="w-3.5 h-3.5" /> <span>exam_policy.txt</span>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-700">
              <CheckCircle2 className="w-3.5 h-3.5" /> <span>admission_policy.txt</span>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-700">
              <CheckCircle2 className="w-3.5 h-3.5" /> <span>conduct_rules.txt</span>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-700">
              <CheckCircle2 className="w-3.5 h-3.5" /> <span>academic_calendar.txt</span>
            </div>
          </div>
        </div>

        {/* Quick Suggested Prompts */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex-1 overflow-y-auto">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5 text-blue-600" />
            <span>Frequently Asked Inquiries</span>
          </h3>
          <div className="space-y-2">
            {topics.map((t, idx) => (
              <button
                key={idx}
                onClick={() => handleTopicClick(t.prompt)}
                disabled={loading}
                className="w-full text-left p-2.5 rounded-xl text-xs bg-slate-50 hover:bg-blue-50/80 hover:text-blue-700 text-slate-700 font-medium transition-colors border border-slate-200/60 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <div className="font-bold text-[11px] text-slate-900 mb-0.5">{t.topic}</div>
                <div className="text-[11px] text-slate-500 line-clamp-1">"{t.prompt}"</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right Column: Chat Window */}
      <div className="flex-1 bg-white rounded-2xl border border-slate-200/80 shadow-xs flex flex-col overflow-hidden">
        {/* Chat Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-xs">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Al-Noor Academy Policy Assistant</h2>
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Grounded RAG Active</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => setMessages((currentMessages) => [currentMessages[0]])}
            title="Clear Chat History"
            aria-label="Clear chat history"
            disabled={loading}
            className="min-h-11 min-w-11 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4" role="log" aria-live="polite" aria-relevant="additions text" aria-label="Policy assistant conversation">
          {messages.map((m) => {
            const isBot = m.sender === 'bot';
            return (
              <div
                key={m.id}
                className={`flex gap-3 max-w-2xl ${isBot ? 'mr-auto' : 'ml-auto flex-row-reverse'}`}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${
                    isBot ? 'bg-indigo-600 text-white shadow-xs' : 'bg-slate-900 text-white'
                  }`}
                >
                  {isBot ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>

                {/* Message Bubble */}
                <div className="space-y-1.5">
                  <div
                    className={`p-4 rounded-2xl text-xs leading-relaxed ${
                      isBot
                        ? 'bg-slate-100 text-slate-800 rounded-tl-none border border-slate-200/60'
                        : 'bg-blue-600 text-white rounded-tr-none shadow-sm'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{m.text}</p>

                    {/* Sources Badge */}
                    {isBot && m.sources && m.sources.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-200/80 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-500">
                        <span className="font-bold uppercase tracking-wider text-slate-400">Sources:</span>
                        {m.sources.map((src, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 font-semibold"
                          >
                            <FileText className="w-2.5 h-2.5 text-blue-600" />
                            <span>{src}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <p className={`text-[10px] text-slate-400 ${isBot ? 'text-left' : 'text-right'}`}>
                    {m.time}
                  </p>
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex gap-3 max-w-xl mr-auto" role="status">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-3.5 rounded-2xl rounded-tl-none bg-slate-100 border border-slate-200 text-xs text-slate-600 flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-bounce"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-bounce [animation-delay:0.2s]"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-bounce [animation-delay:0.4s]"></span>
                </div>
                <span>Searching policy documents & synthesizing grounded response...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="p-3.5 border-t border-slate-100 bg-white flex items-center gap-2"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask anything about fees, exams, admissions, or rules (e.g. 'What is the fee refund policy?')"
            disabled={loading}
            aria-label="Ask the policy assistant a question"
            className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !inputQuery.trim()}
            aria-label="Send policy question"
            className="min-h-11 min-w-11 p-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-xs transition-colors disabled:opacity-40"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
