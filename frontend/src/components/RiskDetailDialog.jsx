import React from 'react';
import { Lightbulb, Receipt, ShieldAlert, X } from 'lucide-react';
import { bandLabel, explanationTitle, feeFollowUpText, scoreText, trendText } from '../lib/risk';

export default function RiskDetailDialog({ detail, onClose }) {
  const { student, risk_assessment: assessment, recommended_interventions: steps, fee_follow_up: followUp, note } = detail;
  const feeText = feeFollowUpText(followUp);
  const hasScore = assessment.risk_score !== null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div role="dialog" aria-modal="true" aria-label={`Estimate for ${student.name}`} className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl border border-slate-100">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-slate-600" />
            <h3 className="text-base font-bold text-slate-900">{student.name}</h3>
          </div>
          <button onClick={onClose} aria-label="Close" className="min-h-9 min-w-9 flex items-center justify-center text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs text-slate-500">{hasScore ? bandLabel(assessment.risk_category) : assessment.risk_category}</p>
              <h4 className="text-lg font-black text-slate-900">{scoreText(assessment.risk_score)}</h4>
            </div>
            <div className="text-right text-xs">
              <span className="text-slate-500">Roll number</span>
              <p className="font-mono font-bold text-blue-700">#{student.roll_number}</p>
            </div>
          </div>

          {hasScore && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">{explanationTitle(assessment.explanation_method)}</h4>
              <div className="space-y-1.5">
                {assessment.top_reasons.map((reason) => (
                  <div key={reason} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-medium text-slate-800">{reason}</div>
                ))}
              </div>
              <p className="text-xs text-slate-500 mt-2">{trendText(assessment.metrics)}</p>
            </div>
          )}

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
              <span>Steps to consider</span>
            </h4>
            <ul className="space-y-2">
              {steps.map((step) => (
                <li key={step} className="p-2.5 rounded-lg bg-indigo-50/70 border border-indigo-200 text-xs font-medium text-indigo-950">{step}</li>
              ))}
            </ul>
          </div>

          <div className="p-3 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1">
            <p className="font-bold">Guardian</p>
            <p>{student.guardian_name} &bull; {student.phone}</p>
          </div>

          {feeText && (
            <div className="p-3 rounded-xl border border-amber-200 bg-amber-50 text-xs text-amber-900 flex items-start gap-2">
              <Receipt className="w-4 h-4 shrink-0" />
              <p><b>{feeText}.</b> For the accounts office. This does not affect the academic estimate.</p>
            </div>
          )}

          <p className="text-[11px] text-slate-500">{note}</p>

          <div className="pt-3 border-t border-slate-100 text-right">
            <button onClick={onClose} className="min-h-11 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold">Close</button>
          </div>
        </div>
      </div>
    </div>
  );
}
