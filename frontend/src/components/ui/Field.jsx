import React, { useId } from 'react';
import { Search } from 'lucide-react';

// 16px on phones, because iPhones zoom the whole page when a smaller field is tapped.
export const INPUT_CLASS = 'min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600 sm:text-sm';

/** A label, its control, and an optional hint. `children` receives the id and description to apply. */
export function Field({ label, hint, children }) {
  const id = useId();
  const hintId = `${id}-hint`;
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-semibold text-slate-700">{label}</label>
      {children({ id, 'aria-describedby': hint ? hintId : undefined })}
      {hint && <p id={hintId} className="mt-1 text-xs text-slate-600">{hint}</p>}
    </div>
  );
}

export function TextField({ label, hint, inputRef, className = '', ...props }) {
  return (
    <Field label={label} hint={hint}>
      {(field) => <input ref={inputRef} type="text" className={`${INPUT_CLASS} ${className}`} {...field} {...props} />}
    </Field>
  );
}

export function SelectField({ label, hint, options, ...props }) {
  return (
    <Field label={label} hint={hint}>
      {(field) => (
        <select className={INPUT_CLASS} {...field} {...props}>
          {options.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      )}
    </Field>
  );
}

export function SearchInput({ label, className = '', ...props }) {
  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
      <input type="search" aria-label={label} placeholder={label} className={`${INPUT_CLASS} pl-10`} {...props} />
    </div>
  );
}
