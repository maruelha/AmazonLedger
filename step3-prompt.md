# Claude Code Prompt — Step 3: Browse/Edit Screen + CSV Export

This continues the Amazon-orders-for-tax project. **Steps 1 and 2 are done and their tests pass**: there is a SQLite schema (orders / packages / items), a standalone parser, and a Flask paste→parse→review→save screen that persists orders with per-item tax-relevant flags and amounts.

**Important:** reuse what already exists in this repo — the existing schema, DB, models/queries, parser, routes, templates, and styling. Read the repo to get the real names and structure. Do **not** rewrite the parser, redefine the schema, or duplicate existing save logic.

**This is Step 3, the final step.** It has two parts: a browse/edit screen, and CSV export.

---

## Part A — Browse / Edit screen

A page that lists orders already saved in the database (not the paste screen — this works on persisted data).

- Show saved orders with their packages and items, grouped so the package structure is visible (items under their package, as in the review screen).
- **Inline editing in the list:** each item is editable in place — no separate edit page. Editable per item: `tax_relevant` (checkbox), `item_amount` (text, German comma kept), `tax_tag` (text or simple select), `invoice_name` (text). Per package: `shipment_amount` (text, optional). Saving an edit persists to the DB (inline save / save-per-row / a save button — your choice, but it must be easy to edit many items without losing work).
- Keep amounts as text with comma decimals; do not coerce to float.
- **Filters** (this matters — there will be ~180 orders):
  - filter to **tax-relevant only** (show only items/orders marked tax_relevant), and
  - filter by **year** (based on order_date).
  - Filters should be combinable. Keep the UI simple.
- This screen is for revisiting orders over time to correct flags and fill in amounts for the tax-relevant items.

## Part B — CSV export

A way to export to CSV (button on the browse screen is fine).

- **Granularity: one row per item.**
- **Include tax-relevant rows only** (only items where tax_relevant is set).
- If the current filters are applied, it's fine for the export to respect them (e.g. export the selected year's tax-relevant items) — but make the behaviour clear in the UI (e.g. "Export tax-relevant items (current filter)").
- **If a tax-relevant item has no item_amount entered, export it anyway with the amount cell blank — no warning, no blocking.**
- **Columns, in this order:**
  `order_date, order_no, type, shipment_id, item_name, asin, qty, seller, item_amount, shipment_amount, tax_tag, order_total, invoice_name`
- **German-Excel-safe formatting (required):** semicolon (`;`) as the field separator, UTF-8 **with BOM**, and keep the comma as the decimal separator (e.g. `9,90`). Quote fields containing `;`, `"`, or newlines, escaping inner quotes by doubling. This must open cleanly in German Excel on a double-click without mangled columns or broken umlauts.
- Note for me in the README: when summing in Excel, sum the **item_amount** column only — `order_total` and `shipment_amount` repeat across the rows of an order/package and would double-count if summed.

---

## Scope guards

- Reuse existing schema, queries, parser, and styling; match the look of the existing screens.
- No auth, accounts, or deployment config — local single-user tool.
- Don't change the paste/save screen's behaviour except as needed to share code (e.g. a common rendering partial for the package/item grouping is welcome).

## Tests

- Keep all existing tests passing.
- Add tests for export: given saved data with a mix of tax-relevant and non-relevant items (including at least one tax-relevant item with a blank amount), assert the CSV contains exactly the tax-relevant rows, one row per item, in the column order above, with `;` separators and a UTF-8 BOM, and that the blank-amount item is present with an empty amount cell.
- Add a test (or at least a query-level test) that the year filter and tax-relevant filter select the right rows.
- Full suite runs with the existing single command.

## Deliverables for Step 3

- Browse/edit route + template with inline editing and the tax-relevant + year filters.
- CSV export (respecting tax-relevant-only, one-row-per-item, German-Excel-safe format, blank amounts allowed).
- Added tests; full suite green.
- README note: how to open the browse screen, how to export, and the "sum item_amount only" caveat.

Read the repo and reuse real names. When done, show me: the browse/edit route, the export function, a sample of the generated CSV (a few rows), and a passing test run.
