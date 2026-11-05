import { useCallback, useEffect, useState } from 'react';
import { apiErrorMessage } from './errors';

/**
 * Loads data when `key` changes, and cancels what is out of date.
 * `load` receives request options holding the cancel signal, and returns the axios promise.
 */
export function useLoad(load, key, failureMessage) {
  const [state, setState] = useState({ data: null, loading: true, error: '' });
  const [attempt, setAttempt] = useState(0);
  const reload = useCallback(() => setAttempt((current) => current + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true, error: '' }));
    load({ signal: controller.signal })
      .then((res) => setState({ data: res.data, loading: false, error: '' }))
      .catch((err) => {
        if (err.code === 'ERR_CANCELED') return;
        setState({ data: null, loading: false, error: apiErrorMessage(err, failureMessage) });
      });
    return () => controller.abort();
    // `load` is a new function on each render; `key` says when the request really changes.
  }, [key, attempt]);

  return { ...state, reload };
}
