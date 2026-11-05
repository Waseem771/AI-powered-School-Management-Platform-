import React, { useState } from 'react';
import { openPdf, pdfErrorMessage } from '../lib/pdf';
import { buttonClass } from './ui/Button';
import { useToast } from './ui/Toast';

export default function PdfButton({ fetchPdf, variant = 'secondary', className = '', title, children }) {
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const handleClick = async () => {
    setLoading(true);
    let failure = null;
    const opened = await openPdf(() =>
      fetchPdf().catch((error) => {
        failure = error;
        throw error;
      })
    );
    setLoading(false);
    if (!opened) toast.error(await pdfErrorMessage(failure));
  };

  return (
    <button type="button" onClick={handleClick} disabled={loading} aria-busy={loading} title={title} className={buttonClass(variant, className)}>
      {children}
    </button>
  );
}
