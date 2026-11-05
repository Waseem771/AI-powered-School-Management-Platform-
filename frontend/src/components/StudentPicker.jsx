import React, { useEffect, useId, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { api } from '../api/client';
import { apiErrorMessage } from '../lib/errors';
import { nextActiveIndex, studentLabel } from '../lib/uiState';
import { INPUT_CLASS } from './ui/Field';

const SEARCH_DELAY_MS = 250;
const MAX_SHOWN = 20;

/**
 * Finds a student by typing, in place of a dropdown holding the whole school.
 * Searches current students on the server, so it stays quick at any school size.
 */
export default function StudentPicker({ label = 'Student', student, onChange, autoFocus = false }) {
  const id = useId();
  const listId = `${id}-list`;
  const inputRef = useRef(null);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [matches, setMatches] = useState([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setSearching(true);
      setError('');
      try {
        const params = query.trim() ? { search: query.trim() } : {};
        const res = await api.getStudents(params, { signal: controller.signal });
        setMatches(res.data);
        setActiveIndex(-1);
      } catch (err) {
        if (err.code === 'ERR_CANCELED') return;
        setMatches([]);
        setError(apiErrorMessage(err, 'Could not search students.'));
      }
      setSearching(false);
    }, SEARCH_DELAY_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, open]);

  const shown = matches.slice(0, MAX_SHOWN);

  const choose = (chosen) => {
    onChange(chosen);
    setOpen(false);
    setQuery('');
  };

  const clear = () => {
    onChange(null);
    setQuery('');
    setOpen(true);
    inputRef.current?.focus();
  };

  const handleKeyDown = (event) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) => nextActiveIndex(current, event.key === 'ArrowDown' ? 1 : -1, shown.length));
    } else if (event.key === 'Enter' && open) {
      event.preventDefault();
      if (shown[activeIndex]) choose(shown[activeIndex]);
    } else if (event.key === 'Escape' && open) {
      event.stopPropagation();
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <label htmlFor={id} className="mb-1 block text-sm font-semibold text-slate-700">{label}</label>
      <div className="relative">
        <input
          id={id}
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
          autoComplete="off"
          autoFocus={autoFocus}
          placeholder="Type a name or roll number"
          value={student ? studentLabel(student) : query}
          readOnly={Boolean(student)}
          onChange={(event) => { setQuery(event.target.value); setOpen(true); }}
          onFocus={() => { if (!student) setOpen(true); }}
          onBlur={() => setOpen(false)}
          onKeyDown={handleKeyDown}
          className={`${INPUT_CLASS} ${student ? 'pr-11 font-semibold' : ''}`}
        />
        {student && (
          <button
            type="button"
            aria-label="Choose a different student"
            onClick={clear}
            className="absolute right-0 top-0 flex min-h-11 min-w-11 items-center justify-center rounded-xl text-slate-500 hover:text-slate-800"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {open && !student && (
        // Part of the page's flow, so a dialog's scrolling can never cut it off.
        // Keeps focus in the field while an option is pressed, so the press is not lost to blur.
        <ul
          id={listId}
          role="listbox"
          aria-label={label}
          onMouseDown={(event) => event.preventDefault()}
          className="mt-1 max-h-56 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white py-1"
        >
          {error && <li role="alert" className="px-3 py-2.5 text-sm text-rose-800">{error}</li>}
          {!error && searching && shown.length === 0 && <li className="px-3 py-2.5 text-sm text-slate-600">Searching…</li>}
          {!error && !searching && shown.length === 0 && <li className="px-3 py-2.5 text-sm text-slate-600">No current student matches that.</li>}
          {shown.map((option, index) => (
            <li
              key={option.id}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              onClick={() => choose(option)}
              className={`flex min-h-11 cursor-pointer items-center px-3 text-sm text-slate-800 ${index === activeIndex ? 'bg-brand-50' : 'hover:bg-slate-50'}`}
            >
              {studentLabel(option)}
            </li>
          ))}
          {matches.length > MAX_SHOWN && <li className="px-3 py-2 text-xs text-slate-600">Showing the first {MAX_SHOWN}. Keep typing to narrow this down.</li>}
        </ul>
      )}
    </div>
  );
}
