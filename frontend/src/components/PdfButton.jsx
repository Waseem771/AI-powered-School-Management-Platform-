import React, { useState } from 'react';
import { openPdf, pdfErrorMessage } from '../lib/pdf';

export default function PdfButton({ fetchPdf, className, title, children }) {
  const [loading, setLoading] = useState(false);

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
    if (!opened) window.alert(await pdfErrorMessage(failure));
  };

  return (
    <button type="button" onClick={handleClick} disabled={loading} title={title} className={`${className} disabled:opacity-60`}>
      {children}
    </button>
  );
}
