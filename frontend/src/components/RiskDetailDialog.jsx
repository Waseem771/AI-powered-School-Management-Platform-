import React from 'react';
import { Lightbulb, Receipt } from 'lucide-react';
import { bandLabel, explanationTitle, feeFollowUpText, scoreText, trendText } from '../lib/risk';
import Button from './ui/Button';
import Modal from './ui/Modal';

export default function RiskDetailDialog({ detail, onClose }) {
  const { student, risk_assessment: assessment, recommended_interventions: steps, fee_follow_up: followUp, note } = detail;
  const feeText = feeFollowUpText(followUp);
  const hasScore = assessment.risk_score !== null;

  return (
    <Modal
      title={student.name}
      description={`Roll #${student.roll_number}, ${student.grade}-${student.section}`}
      size="lg"
      onClose={onClose}
      footer={<Button variant="secondary" onClick={onClose}>Close</Button>}
    >
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
        <p className="text-sm text-slate-600">{hasScore ? bandLabel(assessment.risk_category) : assessment.risk_category}</p>
        <p className="text-lg font-bold text-navy-900">{scoreText(assessment.risk_score)}</p>
      </div>

      {hasScore && (
        <div>
          <h3 className="mb-2 text-sm font-bold text-slate-800">{explanationTitle(assessment.explanation_method)}</h3>
          <ul className="space-y-1.5">
            {assessment.top_reasons.map((reason) => (
              <li key={reason} className="rounded-lg border border-slate-200 p-2.5 text-sm text-slate-800">{reason}</li>
            ))}
          </ul>
          <p className="mt-2 text-sm text-slate-600">{trendText(assessment.metrics)}</p>
        </div>
      )}

      <div>
        <h3 className="mb-2 flex items-center gap-1.5 text-sm font-bold text-slate-800">
          <Lightbulb className="h-4 w-4 text-amber-600" aria-hidden="true" />
          <span>Steps to consider</span>
        </h3>
        <ul className="space-y-1.5">
          {steps.map((step) => (
            <li key={step} className="rounded-lg border border-brand-200 bg-brand-50 p-2.5 text-sm text-navy-900">{step}</li>
          ))}
        </ul>
      </div>

      <div className="text-sm text-slate-700">
        <p className="font-semibold">Guardian</p>
        <p>{student.guardian_name} &bull; {student.phone}</p>
      </div>

      {feeText && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <Receipt className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p><b>{feeText}.</b> For the accounts office. This does not affect the academic estimate.</p>
        </div>
      )}

      <p className="text-xs text-slate-600">{note}</p>
    </Modal>
  );
}
