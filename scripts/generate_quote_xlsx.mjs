// Keep the CLI supervisor free of native rendering libraries. Some native
// runtimes hang during teardown on Windows even after all writes complete.
import { fork } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const child = fork(fileURLToPath(new URL('./quote_xlsx_process.mjs', import.meta.url)), process.argv.slice(2), {
  stdio: ['ignore', 'inherit', 'inherit', 'ipc'],
  windowsHide: true,
});
let result = null;
const finish = (code) => {
  if (result !== null) return;
  result = code;
  // Only this supervisor's own child is terminated, after receiving its result.
  child.kill('SIGKILL');
};
child.on('message', message => {
  if (message?.type === 'complete') finish(0);
  if (message?.type === 'failed') {
    process.stderr.write(`${message.error}\n`);
    finish(1);
  }
});
child.on('error', error => {
  process.stderr.write(`${error.message}\n`);
  finish(1);
});
const timeout = setTimeout(() => {
  process.stderr.write('Quotation renderer exceeded its 110-second deadline.\n');
  finish(1);
}, 110_000);
child.on('close', code => {
  clearTimeout(timeout);
  // An exit without the explicit completion signal is never a successful export.
  process.exitCode = result ?? (code || 1);
});
