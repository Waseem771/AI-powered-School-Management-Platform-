import React, { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';
import { IconButton } from './Button';
import { focusTrapTarget } from '../../lib/uiState';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])';
const WIDTHS = { sm: 'sm:max-w-sm', md: 'sm:max-w-md', lg: 'sm:max-w-lg', xl: 'sm:max-w-2xl' };

/**
 * The one dialog: keeps focus inside, closes on Escape, returns focus to where it came from.
 * On a phone it rises from the bottom and scrolls within the screen.
 * Set `busy` while saving, so it cannot be closed halfway through.
 */
export default function Modal({ title, description, size = 'md', busy = false, onClose, children, footer }) {
  const titleId = useId();
  const panelRef = useRef(null);
  const closeRef = useRef(onClose);
  const busyRef = useRef(busy);
  closeRef.current = onClose;
  busyRef.current = busy;

  useEffect(() => {
    const cameFrom = document.activeElement;
    const panel = panelRef.current;
    const firstField = panel.querySelector('input, select, textarea');
    (firstField || panel.querySelector(FOCUSABLE) || panel).focus();

    const { overflow } = document.body.style;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = overflow;
      if (cameFrom instanceof HTMLElement) cameFrom.focus();
    };
  }, []);

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      if (!busyRef.current) closeRef.current();
      return;
    }
    if (event.key !== 'Tab') return;
    const target = focusTrapTarget([...panelRef.current.querySelectorAll(FOCUSABLE)], document.activeElement, event.shiftKey);
    if (target) {
      event.preventDefault();
      target.focus();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy-950/60 sm:items-center sm:p-4">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={`flex max-h-[92dvh] w-full flex-col rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl ${WIDTHS[size]}`}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-3">
          <div className="min-w-0 py-1.5">
            <h2 id={titleId} className="text-base font-bold text-slate-900">{title}</h2>
            {description && <p className="mt-0.5 text-sm text-slate-600">{description}</p>}
          </div>
          <IconButton label="Close" onClick={onClose} disabled={busy} className="-mr-2 shrink-0">
            <X className="h-5 w-5" />
          </IconButton>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}
