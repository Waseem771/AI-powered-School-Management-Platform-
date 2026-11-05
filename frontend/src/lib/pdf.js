const OBJECT_URL_LIFETIME_MS = 60_000;

function saveAsDownload(url) {
  const link = document.createElement('a');
  link.href = url;
  link.download = 'EduCore-document.pdf';
  link.click();
}

/**
 * Fetches a PDF with the login token and shows it in a new tab.
 *
 * Plain links cannot send the bearer token. The tab must be opened before the first
 * await, while still inside the click, or browsers treat it as an unwanted popup.
 * Returns true on success, false if the PDF could not be loaded.
 */
export async function openPdf(fetchPdfBlob, browser = {}) {
  const {
    openTab = () => window.open('', '_blank'),
    createUrl = (blob) => URL.createObjectURL(blob),
    revokeUrl = (url) => URL.revokeObjectURL(url),
    download = saveAsDownload,
    schedule = setTimeout,
  } = browser;

  const tab = openTab();
  try {
    const url = createUrl(await fetchPdfBlob());
    if (tab) {
      tab.location.href = url;
    } else {
      download(url);
    }
    schedule(() => revokeUrl(url), OBJECT_URL_LIFETIME_MS);
    return true;
  } catch {
    tab?.close();
    return false;
  }
}
