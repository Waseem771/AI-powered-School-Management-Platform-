/**
 * What the chatbot page says is running, from GET /chatbot/status. It says nothing is working
 * until the server has confirmed it, so the page can never claim an AI service that is absent.
 *
 * @param {{ language_model?: { configured?: boolean, last_call_ok?: boolean|null },
 *           policy_search?: { engine?: string } } | null} status
 * @returns {{ label: string, tone: 'ok'|'warn'|'off' }[]}
 */
export function describeChatStatus(status) {
  if (!status) return [{ label: 'Checking what is available…', tone: 'off' }];
  return [languageModelLine(status.language_model), policySearchLine(status.policy_search), RECORDS_LINE];
}

const RECORDS_LINE = { label: 'Student, fee, and result lookups: on', tone: 'ok' };

function languageModelLine(model) {
  if (!model?.configured) return { label: 'AI language model: off, using built-in answers', tone: 'off' };
  if (model.last_call_ok === false) return { label: 'AI language model: last call failed, using built-in answers', tone: 'warn' };
  if (model.last_call_ok === true) return { label: 'AI language model: on', tone: 'ok' };
  return { label: 'AI language model: set up, not used yet', tone: 'off' };
}

function policySearchLine(search) {
  if (search?.engine === 'faiss') return { label: 'Policy search: on (meaning-based)', tone: 'ok' };
  if (search?.engine === 'tfidf') return { label: 'Policy search: on (keyword-based)', tone: 'ok' };
  return { label: 'Policy search: starts on the first policy question', tone: 'off' };
}

/** Where an answer came from, in words a school owner can check. Null when it was not answered. */
export function answerSource({ mode, grounded }) {
  if (!grounded) return null;
  if (mode === 'policy_rag') return 'From policy documents';
  if (mode === 'school_data') return 'From school records';
  if (mode === 'groq_tool_calling') return 'From school records, worded by AI';
  return null;
}

/** "fee_policy.txt" becomes "Fee policy". */
export function policyName(fileName) {
  const words = fileName.replace(/\.txt$/, '').replaceAll('_', ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** The short line under the chatbot's name. */
export function chatStatusSummary(status) {
  if (!status) return 'Checking…';
  const model = status.language_model;
  return model?.configured && model.last_call_ok !== false ? 'School records and policies, with AI' : 'School records and policies';
}
