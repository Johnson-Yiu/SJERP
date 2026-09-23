import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("startup applies migrations before it starts Django", async () => {
  const source = await readFile(new URL("../start-main-worktree.ps1", import.meta.url), "utf8");
  const managePathAt = source.indexOf('Join-Path $BackendDir "manage.py"');
  const migrateAt = source.indexOf("& $VenvPython $ManagePy migrate --noinput");
  const serverAt = source.indexOf("manage.py runserver");

  assert.ok(managePathAt >= 0, "migration must use backend/manage.py");
  assert.ok(migrateAt >= 0, "startup script must run migrations");
  assert.ok(migrateAt < serverAt, "migrations must complete before Django starts");
  assert.match(source, /function Stop-BackendServer/, "startup must replace an old Django process after migrations");
  assert.match(source, /function Wait-ForBackendHealth/, "startup must verify that the API responds, not only that a port is open");
  assert.doesNotMatch(source, /runserver[^\n]*--noreload/, "Django reload must remain enabled for backend changes");
});
