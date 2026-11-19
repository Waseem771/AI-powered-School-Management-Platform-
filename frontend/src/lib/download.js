/** Saves a fetched file (such as a CSV) using a temporary link, because plain links cannot send the login token. */
export function saveBlob(blob, filename, browser = {}) {
  const { createUrl = (file) => URL.createObjectURL(file), revokeUrl = (url) => URL.revokeObjectURL(url) } = browser;
  const url = createUrl(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => revokeUrl(url), 30_000);
}
