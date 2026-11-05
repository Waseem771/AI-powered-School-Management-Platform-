import React from 'react';

const BASE = 'inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60';

const VARIANTS = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700',
  secondary: 'border border-slate-300 bg-white text-slate-800 hover:bg-slate-50',
  ghost: 'text-slate-700 hover:bg-slate-100',
  success: 'bg-emerald-700 text-white hover:bg-emerald-800',
  danger: 'bg-rose-700 text-white hover:bg-rose-800',
};

/** The classes for anything that looks like a button, such as a link. */
export function buttonClass(variant = 'primary', extra = '') {
  return `${BASE} ${VARIANTS[variant]} ${extra}`.trim();
}

export default function Button({ variant = 'primary', className = '', type = 'button', children, ...props }) {
  return (
    <button type={type} className={buttonClass(variant, className)} {...props}>
      {children}
    </button>
  );
}

/** A button showing only an icon. It must say what it does, because it shows no words. */
export function IconButton({ label, className = '', children, ...props }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={`inline-flex min-h-11 min-w-11 items-center justify-center rounded-xl text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 disabled:opacity-60 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
