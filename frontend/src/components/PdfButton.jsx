import React, { useState } from 'react';
import { openPdf } from '../lib/pdf';

const PDF_ERROR_MESSAGE = 'Could not open the PDF. Please try again.';

export default function PdfButton({ fetchPdf, className, title, children }) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    const opened = await openPdf(fetchPdf);
    setLoading(false);
    if (!opened) window.alert(PDF_ERROR_MESSAGE);
  };

  return (
    <button type="button" onClick={handleClick} disabled={loading} title={title} className={`${className} disabled:opacity-60`}>
      {children}
    </button>
  );
}
