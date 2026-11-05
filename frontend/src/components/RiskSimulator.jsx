import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { apiErrorMessage } from '../lib/errors';
import { MODEL_NOTE, bandLabel, bandStyle, explanationTitle, scoreText } from '../lib/risk';
import Modal from './ui/Modal';

const REQUEST_DELAY_MS = 250;

function Slider({ label, value, shown, min, max, onChange }) {
  return (
    <label className="block space-y-1">
      <span className="flex justify-between">
        <span className="text-slate-500">{label}</span>
        <span className="font-bold text-slate-800">{shown}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-6 w-full cursor-pointer"
      />
    </label>
  );
}

/** Sends made-up numbers to the real model. Nothing is read from or saved to any student's record. */
export default function RiskSimulator({ onClose }) {
  const [marks, setMarks] = useState(55);
  const [failing, setFailing] = useState(1);
  const [compareExams, setCompareExams] = useState(false);
  const [trend, setTrend] = useState(-10);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const res = await api.simulateRisk(
          { avg_marks_pct: marks, failing_subjects: failing, grade_trend: compareExams ? trend : null },
          { signal: controller.signal },
        );
        setResult(res.data);
        setError('');
      } catch (err) {
        if (err.code !== 'ERR_CANCELED') setError(apiErrorMessage(err));
      }
    }, REQUEST_DELAY_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [marks, failing, compareExams, trend]);

  return (
    <Modal title="Try the model" description="Made-up numbers, not a student's record. Nothing is saved." size="xl" onClose={onClose}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-sm">
            <Slider label="Average marks" value={marks} shown={`${marks}%`} min={0} max={100} onChange={setMarks} />
            <Slider label="Failed subjects" value={failing} shown={failing} min={0} max={6} onChange={setFailing} />
            <label className="flex items-center gap-2 text-slate-700 min-h-11">
              <input type="checkbox" checked={compareExams} onChange={(event) => setCompareExams(event.target.checked)} />
              <span>Has a midterm and final to compare</span>
            </label>
            {compareExams && (
              <Slider label="Change, midterm to final" value={trend} shown={`${trend > 0 ? '+' : ''}${trend} points`} min={-50} max={50} onChange={setTrend} />
            )}
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 min-h-48" aria-live="polite">
            {error && <p className="text-xs text-rose-700">{error}</p>}
            {!error && !result && <p className="text-xs text-slate-500">Asking the model…</p>}
            {!error && result && (
              <div className="space-y-3">
                <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${bandStyle(result.risk_category).badge}`}>
                  {bandLabel(result.risk_category)}
                </span>
                <p className="text-2xl font-black text-slate-900">{scoreText(result.risk_score)}</p>
                <div className="space-y-1.5">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{explanationTitle(result.explanation_method)}</p>
                  {result.top_reasons.map((reason) => (
                    <div key={reason} className="p-2 rounded-lg bg-white border border-slate-200 text-sm text-slate-800">{reason}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <p className="text-xs text-slate-600">{MODEL_NOTE}</p>
    </Modal>
  );
}
