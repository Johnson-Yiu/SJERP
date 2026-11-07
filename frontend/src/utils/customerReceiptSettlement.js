export async function saveOrVerifyCustomerReceipt({ outcome, lookup, save }) {
  if (outcome === 'unknown') {
    try {
      const receipt = await lookup()
      return receipt ? { status: 'found', receipt } : { status: 'missing' }
    } catch (error) {
      return { status: 'lookup-failed', error }
    }
  }

  try {
    return { status: 'saved', receipt: await save() }
  } catch (error) {
    const statusCode = error?.status || error?.response?.status
    const duplicateNumber = Boolean(error?.response?.data?.transaction_no)
    const ambiguous = !statusCode || statusCode >= 500 || statusCode === 408 || duplicateNumber
    return { status: ambiguous ? 'unknown' : 'rejected', error }
  }
}
