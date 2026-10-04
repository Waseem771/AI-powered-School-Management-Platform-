import React, { useState } from 'react';
import { Bot, Sparkles, CheckCircle2, XCircle } from 'lucide-react';
import client from '../api/client';

export default function Admissions() {
  const [rollNumber, setRollNumber] = useState('');
  const [program, setProgram] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      // Connect to the backend using the configured Axios client
      // This will automatically switch between localhost and Modal depending on the environment
      const response = await client.post('/admissions-crew/evaluate', {
        student_roll_number: rollNumber,
        desired_program: program,
      });

      const data = response.data;
      
      // CrewAI sometimes returns an object with a 'raw' property instead of a plain string.
      const recommendationText = data.recommendation?.raw || data.recommendation || "No recommendation provided.";
      const studentName = data.student_name || rollNumber;

      setResult(`Evaluating Student: ${studentName}\n\n${recommendationText}`);
      
    } catch (error) {
      console.error('Error fetching admission evaluation:', error);
      setResult(`Error: ${error.response?.data?.detail || 'Could not connect to AI Admissions Agent. Please make sure the backend is running.'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 tracking-tight">AI Admissions Agent</h1>
        <p className="text-slate-500 text-sm mt-1">Multi-Agent System (CrewAI) for evaluating student eligibility using database records.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Form */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
              <Bot className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-800">New Application</h2>
              <p className="text-xs text-slate-500">Enter student Roll Number</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Desired Grade for Admission</label>
              <select
                required
                value={program}
                onChange={(e) => setProgram(e.target.value)}
                className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-2.5 text-sm focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select a grade...</option>
                <option value="Grade 6">Grade 6</option>
                <option value="Grade 7">Grade 7</option>
                <option value="Grade 8">Grade 8</option>
                <option value="Grade 9">Grade 9</option>
                <option value="Grade 10">Grade 10</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Student Roll Number (from Database)</label>
              <input
                type="text"
                required
                value={rollNumber}
                onChange={(e) => setRollNumber(e.target.value)}
                className="w-full rounded-xl border-slate-200 bg-slate-50 px-4 py-3 text-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g. STU001"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 animate-spin" /> Analyzing via CrewAI...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4" /> Evaluate Eligibility
                </span>
              )}
            </button>
          </form>
        </div>

        {/* Output Result */}
        <div className="bg-slate-900 rounded-2xl p-6 border border-slate-800 shadow-sm flex flex-col h-full min-h-[400px]">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-900/50 border border-emerald-800/50 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h2 className="font-semibold text-white">AI Decision</h2>
                <p className="text-xs text-slate-400">Agent Recommendation</p>
              </div>
            </div>
            {result && <span className="bg-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2.5 py-1 rounded-full border border-emerald-500/20">COMPLETED</span>}
          </div>

          <div className="flex-1 text-slate-300 text-sm overflow-y-auto whitespace-pre-wrap">
            {result ? (
              result
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-500">
                <Bot className="w-12 h-12 mb-3 opacity-20" />
                <p>Awaiting application submission...</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
