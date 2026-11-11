export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  // Chrome may start reading the Blob after the current navigation task.
  setTimeout(() => URL.revokeObjectURL(url), 30_000)
}
