// PI display amounts use the same cent-level line rounding as the saved
// quotation export. This does not change the server's source calculations.
export function roundPiMoney(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return 0
  return Math.round((amount + Number.EPSILON * Math.abs(amount)) * 100) / 100
}
