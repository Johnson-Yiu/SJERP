export function resolveDetailForPreview(details, preview, previewCount, createDetail) {
  const matching = details.find(detail => detail.preview_key === preview.key)
  if (matching) return matching

  // An edited single SKU can be loaded before its generated preview key settles.
  // Re-key its only detail row instead of silently returning a fresh empty row.
  if (previewCount === 1 && details.length === 1) {
    details[0].preview_key = preview.key
    return details[0]
  }

  return createDetail()
}
