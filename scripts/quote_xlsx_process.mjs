// Dynamic import reports initialization and rendering failures to the
// supervisor before native teardown can hang.
try {
  await import('./quote_xlsx_worker.mjs');
} catch (error) {
  if (process.send) process.send({ type: 'failed', error: error?.stack || String(error) });
  else throw error;
}
