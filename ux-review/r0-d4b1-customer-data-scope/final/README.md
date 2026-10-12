# R0-D4B1 Final Focused Repair — Visual Evidence

All screenshots were captured from the Codex In-app Browser against the isolated R0-D4B1 UAT database.

- `R0D4B1_FINAL_01_self_scope_customer.jpg` — Sales A opens Customer A; the self scope lists only the assigned customer.
- `R0D4B1_FINAL_02_self_scope_denied_other_customer.jpg` — Sales A directly opens an out-of-scope customer edit URL; the request is rejected and the UI reports that no matching customer is available.
- `R0D4B1_FINAL_03_department_scope_customers.jpg` — Department manager sees both department customers and not the customer owned by another department.
- `R0D4B1_FINAL_04_all_scope_owner_modified.jpg` — All-scope user reopens Customer A after assigning Sales B; Sales B remains selected.
- `R0D4B1_FINAL_05_all_scope_owner_cleared_reopened.jpg` — All-scope user clears Customer A's owner, saves, and reopens the editor; the empty selection matches the saved state.
