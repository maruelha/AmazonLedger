# Claude Code Prompt — Step 2: Paste & Review Screen + Save

This continues the Amazon-orders-for-tax project. **Step 1 is done and its tests pass**: there is already a SQLite schema (orders / packages / items), a standalone parser function, and a passing test suite.

**Important:** reuse what already exists in this repo. Use the existing parser function, the existing schema, the existing DB, and the existing module/file layout. Do **not** rewrite the parser or redefine the schema — import and call what's there. If you need to know exact names or the parser's output shape, read the existing code first.

**This is Step 2 only.** Do not build the browse/edit screen or CSV export yet — those are Step 3+.

---

## Goal of Step 2

A single screen where I can:
1. Paste raw Amazon order text into a textarea and click **Parse**.
2. See the parsed result rendered as a list of orders, each showing its packages and the items grouped under each package.
3. For each item, set **tax-relevant** (checkbox) and optionally type an **item amount**. Optionally set a **shipment amount** per package. (Money fields are German-style, e.g. `9,90` — keep the comma; store as text.)
4. Click **Save**, which writes the orders/packages/items into the existing SQLite tables.

So Step 2 = the existing parser, wired to a Flask page, plus the ability to mark/enter and persist.

---

## Behaviour details

**Parsing**
- The Parse button runs the existing parser on the textarea content (many orders at once is allowed) and renders the structured result. Parsing alone does not save anything.
- Render so the structure is obvious: each order as a card/section (showing order date, order number, order total, type), then its packages, with items listed under the package they belong to (grouped by shipment_id). Show each item's name, asin, qty, and (if the paste was a Bestelldetails view) the parsed per-item price and seller.

**Editing before save**
- Each item row has: a **tax-relevant** checkbox (default off) and an **item amount** text input (pre-filled with the parsed price if one exists, otherwise empty).
- Each package has an optional **shipment amount** text input.
- Keep amounts as text with the comma decimal; do not coerce to float on input. (If you want to validate, accept both `9,90` and `9.90` but store consistently as the comma form.)

**Saving (dedupe matters)**
- On Save, insert into the existing tables. Map the parser output to orders → packages → items using the existing schema's keys and foreign keys.
- **Dedupe on `order_no`** (it is UNIQUE): if an order with that order_no already exists, do **not** create a duplicate. For Step 2 keep the dedupe rule simple and predictable — pick ONE of these and tell me which you implemented:
  - (a) skip orders whose order_no already exists (report how many skipped), or
  - (b) update the existing order's items/flags/amounts from this paste.
  I slightly prefer (a) skip-and-report for now (safer, no accidental overwrites), but use your judgement and state clearly what you did.
- Persist the tax-relevant flags, item amounts, and shipment amounts I entered, alongside the parsed fields.
- After saving, show a clear confirmation: how many orders/packages/items were saved, and how many were skipped as duplicates.

**Scope guards**
- Do not build a page to view/edit already-saved orders (that's Step 3).
- Do not build CSV export yet (Step 3).
- Don't add auth, accounts, or deployment config — this runs locally for me only.

---

## UI / tech notes

- Plain Flask + server-rendered HTML is fine; a little vanilla JS for the parse-then-show interaction is fine. No heavy frontend framework needed.
- It must be usable: when I paste a big block with many orders, the rendered review list should be readable and the checkboxes/inputs easy to use. Group items visibly under packages so the package structure is clear (this matters to me).
- Keep styling clean and simple; function over polish at this stage.
- Everything stays local; nothing is uploaded anywhere.

---

## Tests

- Keep the existing Step 1 tests passing.
- Add a test for the save logic: parse one of the existing fixtures, save it, assert the rows landed in orders/packages/items with the correct relationships and counts, and assert that saving the **same** paste again does not create duplicates (per the dedupe rule you chose).
- The whole suite must still run with the existing single command.

---

## Deliverables for Step 2

- A Flask route + template for the paste/parse/review/save screen.
- Save logic that maps parser output into the existing schema, with dedupe on order_no and persistence of my tax-relevant flags and amounts.
- Added save-logic test(s); full suite green.
- A short note on how to run the app and which dedupe behaviour you implemented.

Reuse existing code wherever it exists; read the repo to get the real names. Stop after Step 2 — do not start the browse/edit screen or export. When done, show me: the new route(s), the save function, and a passing test run.
