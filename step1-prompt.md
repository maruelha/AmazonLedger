# Claude Code Prompt — Step 1: Schema + Parser + Automated Test

I'm building a small Flask + SQLite tool to capture my Amazon order history for my tax return. I want to build it in steps. **This is Step 1 only.**

Step 1 scope — build exactly these three things, nothing more:
1. The SQLite schema (create the tables, empty).
2. A standalone parser function that turns pasted Amazon order text into structured data.
3. An automated test that runs my real pasted examples through the parser and asserts the output is correct, runnable with a single command.

**Do NOT build in this step:** no Flask routes, no UI/screens, no logic that inserts parsed data into the database. The tables stay empty. Saving comes in a later step.

---

## Context: what the input looks like

I copy order blocks from the Amazon.de "Meine Bestellungen" pages. The copied text is Markdown-ish: product names appear as `[name](url)` links, with noise links (buyagain, reviews, etc.) mixed in. There are two views I might paste:

- **Order-summary view** — has date, order total, order number, and items, but **no per-item prices**.
- **Bestelldetails view** — additionally has **per-item price** (e.g. `9,90€` on its own line) and a **seller** line (`Verkauf durch: [name](url)`).

The parser must handle both, and must handle **several orders pasted at once**.

### Things the parser must get right (edge cases)

- **Order boundaries:** a new order starts at a line beginning with `Bestellung aufgegeben` OR `Abonnement abgerechnet am`.
- **Date:** German format like `9. Januar 2024` → normalise to ISO `2024-01-09`. Month names are German (Januar…Dezember, incl. `März`).
- **Order total:** the amount on the line after `Summe`, e.g. `49,41 €`. Keep the German decimal comma as-is in storage (string `"49,41"`), do not convert to a float/period.
- **Order number:** after `Bestellnr.`, format like `304-5999696-6159543` or `D01-8912984-6191037`.
- **Type:** `physisch` normally; `digital` if the order started with `Abonnement abgerechnet am` **OR** the order number starts with `D0` (digital orders like Audible/Prime Video use `D01-…`).
- **Items:** a product is a Markdown link `[name](url)` where the url contains `/dp/<ASIN>` (ASIN = 10 alphanumeric chars, NOT always starting with B — e.g. a book is `3837164764`) **OR** is a Prime Video link containing `/gp/video/detail/` (these have no ASIN — leave asin empty).
- **Noise links to SKIP** (not items): any link whose text contains `Nochmals kaufen`, `Deinen Artikel anzeigen`, `Schreib eine Produktrezension`, `Bestelldetails anzeigen`, `Rechnung`, `Problem bei Bestellung`, `Eine Frage zum Produkt stellen`, `Meine Video-Bibliothek`. Also skip `Zeitraum für Produkt-Support …` lines.
- **Quantity:** a line that is just a number (e.g. `2` or `3`) appearing right before an item link is that item's quantity. Default quantity = 1 when absent.
- **Shipment / package grouping:** each item's `Deinen Artikel anzeigen` link contains `shipmentId=XXXX`. Items sharing a shipmentId are in the same package. The parser must capture each item's `shipment_id` so items can be grouped into packages per order. (In a Bestelldetails paste the shipmentId may instead appear in the `Deinen Artikel anzeigen` link too — capture it wherever present; if truly absent, leave shipment_id empty.)
- **Seller:** in Bestelldetails view, a line `Verkauf durch: [name](url)` gives the seller for the item it follows.
- **Per-item price:** in Bestelldetails view, a standalone line like `9,90€` gives the price of the item it follows. Keep the comma decimal as string.
- **Money fields are otherwise left empty/null** — the parser never invents amounts.

---

## Schema (create these tables, empty)

Use integer autoincrement primary keys. Keep the natural IDs as UNIQUE columns for later dedupe, not as PKs.

**orders**
- `id` INTEGER PK autoincrement
- `order_no` TEXT UNIQUE NOT NULL
- `order_date` TEXT            -- ISO yyyy-mm-dd
- `order_total` TEXT           -- e.g. "49,41" (German comma kept as string)
- `type` TEXT                  -- 'physisch' | 'digital'
- `invoice_name` TEXT          -- nullable, filled by hand later
- created/updated timestamps if you like

**packages**
- `id` INTEGER PK autoincrement
- `order_id` INTEGER NOT NULL  -- FK -> orders.id
- `shipment_id` TEXT UNIQUE    -- nullable if absent
- `shipment_amount` TEXT       -- nullable, optional, filled by hand later

**items**
- `id` INTEGER PK autoincrement
- `order_id` INTEGER NOT NULL  -- FK -> orders.id
- `package_id` INTEGER         -- FK -> packages.id (nullable if no shipment)
- `name` TEXT NOT NULL
- `asin` TEXT                  -- nullable (Prime Video has none)
- `qty` INTEGER DEFAULT 1
- `seller` TEXT                -- nullable
- `item_amount` TEXT           -- nullable, filled by hand later
- `tax_relevant` INTEGER DEFAULT 0   -- boolean flag, set later
- `tax_tag` TEXT               -- nullable, set later

Provide a single command/script to create the database (e.g. `python init_db.py`) that creates these tables if they don't exist.

---

## Parser output shape

The parser function takes the pasted text (string, possibly many orders) and returns a list of orders, each like:

```python
{
  "order_no": "304-5999696-6159543",
  "order_date": "2024-01-09",
  "order_total": "49,41",
  "type": "physisch",
  "packages": [
    {
      "shipment_id": "UJxfPvsSv",
      "items": [
        {"name": "...", "asin": "B0CG638LRS", "qty": 1, "seller": None, "price": None},
        ...
      ]
    },
    ...
  ]
}
```

Items with the same shipment_id go in the same package; items without a shipment_id can go in a package with `shipment_id = None`.

---

## Automated test (must run with one command)

Write a test (pytest is fine) that includes the **real pasted fixtures below** and asserts the parser extracts them correctly. The test must be runnable with a single command (e.g. `pytest` or `python -m pytest`) and should be the thing I re-run after any future change.

At minimum, assert:
- correct number of orders parsed from a multi-order paste,
- dates normalised to ISO,
- order totals and order numbers correct,
- `type` correctly `digital` for the Audible (`Abonnement abgerechnet am`) and the `D01-` Prime Video order, `physisch` otherwise,
- items grouped into the correct packages by shipment_id (the 3-package order below),
- quantity `2` captured for the Aigostar item,
- ASINs captured incl. the non-B book ASIN `3837164764`, and Prime Video item has empty asin,
- noise links excluded (no "Nochmals kaufen" etc. as items),
- in the Bestelldetails fixture, per-item prices (`9,90`, `6,99`) and sellers captured.

### Fixture A — multiple orders, order-summary view (incl. multi-package, quantity, digital)

```
Bestellung aufgegeben
10. Januar 2024

* Summe
2,39 €
* Versandadresse
 Marina Haase
* Bestellnr. 305-7591774-5703526
* [Bestelldetails anzeigen ](https://www.amazon.de/your-orders/order-details?orderID=305-7591774-5703526)[Rechnung](https://www.amazon.de/your-orders/invoice/popover?orderId=305-7591774-5703526)

* [Oblique-Unique Paper Confetti Colourful Table Decoration](https://www.amazon.de/dp/B07DRMVV26?ref=x)
 Zeitraum für Produkt-Support endet am 13. Januar 2026
[Nochmals kaufen](https://www.amazon.de/gp/buyagain?ats=x)
[ Deinen Artikel anzeigen](https://www.amazon.de/your-orders/pop?orderId=305-7591774-5703526&shipmentId=DKHqm9zdr&asin=B07DRMVV26)

* Bestellung aufgegeben
9. Januar 2024
* Summe
49,41 €
* Versandadresse
 Marina Haase
* Bestellnr. 304-5999696-6159543
* [Bestelldetails anzeigen ](https://www.amazon.de/your-orders/order-details?orderID=304-5999696-6159543)[Rechnung](https://www.amazon.de/your-orders/invoice/popover?orderId=304-5999696-6159543)

* [4 Stück STECKEL schwarz 26.B4 Staubschutz Deckel](https://www.amazon.de/dp/B0CG638LRS?ref=x)
[Nochmals kaufen](https://www.amazon.de/gp/buyagain?ats=x)
[ Deinen Artikel anzeigen](https://www.amazon.de/your-orders/pop?orderId=304-5999696-6159543&shipmentId=UJxfPvsSv&asin=B0CG638LRS)
* [tesa extra Power Universal Gewebeband Weiss 50 m x 50 mm](https://www.amazon.de/dp/B000KTBE9M?ref=x)
 Zeitraum für Produkt-Support endet am 10. Januar 2026
[Nochmals kaufen](https://www.amazon.de/gp/buyagain?ats=x)
[ Deinen Artikel anzeigen](https://www.amazon.de/your-orders/pop?orderId=304-5999696-6159543&shipmentId=UJxfPvsSv&asin=B000KTBE9M)

* [Schreib eine Produktrezension](https://www.amazon.de/review/review-your-purchases?asins=B000KTBE9M)

* 2
[ Aigostar Steckdosenleiste 3-Fach mit Schalter Kindersicherung 3m Schwarz](https://www.amazon.de/dp/B08J7JDGKL?ref=x)
 Zeitraum für Produkt-Support endet am 10. Januar 2026
[Nochmals kaufen](https://www.amazon.de/gp/buyagain?ats=x)
[ Deinen Artikel anzeigen](https://www.amazon.de/your-orders/pop?orderId=304-5999696-6159543&shipmentId=U1YGxTsPv&asin=B08J7JDGKL)
* [tesa extra Power Universal Gewebeband Schwarz 10 m x 50 mm](https://www.amazon.de/dp/B0001M0H3M?ref=x)
 Zeitraum für Produkt-Support endet am 10. Januar 2026
[Nochmals kaufen](https://www.amazon.de/gp/buyagain?ats=x)
[ Deinen Artikel anzeigen](https://www.amazon.de/your-orders/pop?orderId=304-5999696-6159543&shipmentId=U1YGxTsPv&asin=B0001M0H3M)

* [Schreib eine Produktrezension](https://www.amazon.de/review/review-your-purchases?asins=B0001M0H3M)

* Abonnement abgerechnet am
9. Januar 2024
* Summe
9,95 €
* Bestellnr. D01-8912984-6191037
* [Bestelldetails anzeigen ](https://www.amazon.de/gp/css/order-details?orderID=D01-8912984-6191037)[Rechnung](https://www.amazon.de/your-orders/invoice/popover?orderId=D01-8912984-6191037)

* [Audible-Abo](https://www.amazon.de/dp/B08H5XW8SJ?ref=x)
Hörbuch

* [Schreib eine Produktrezension](https://www.amazon.de/review/review-your-purchases?asins=B08H5XW8SJ)

* Bestellung aufgegeben
7. Januar 2024
* Summe
19,45 €
* Versandadresse
 Marina Haase
* Bestellnr. 306-4726240-6689959
* [Bestelldetails anzeigen ](https://www.amazon.de/your-orders/order-details?orderID=306-4726240-6689959)[Rechnung](https://www.amazon.de/your-orders/invoice/popover?orderId=306-4726240-6689959)

* [Achtsam morden durch bewusste Ernährung (Achtsam morden-Reihe, Band 5)](https://www.amazon.de/dp/3837164764?ref=x)
[Nochmals kaufen](https://www.amazon.de/gp/buyagain?ats=x)
[ Deinen Artikel anzeigen](https://www.amazon.de/your-orders/pop?orderId=306-4726240-6689959&shipmentId=Ug274YdXv&asin=3837164764)

* [Schreib eine Produktrezension](https://www.amazon.de/review/review-your-purchases?asins=3837164764)

* Bestellung aufgegeben
7. Januar 2024
* Summe
12,50 €
* Bestellnr. D01-9216861-8357444
* [Bestelldetails anzeigen ](https://www.amazon.de/gp/css/order-details?orderID=D01-9216861-8357444)[Rechnung](https://www.amazon.de/your-orders/invoice/popover?orderId=D01-9216861-8357444)

* [Castle - Staffel 1](https://www.amazon.de/gp/video/detail/amzn1.dv.gti.32a9f6e0?ref=x)
Prime Video

* [Schreib eine Produktrezension](https://www.amazon.de/review/review-your-purchases?asins=B00ERN2U2M)
* [Meine Video-Bibliothek](https://www.amazon.de/gp/video/mystuff?ref=x)
```

Expected for Fixture A: 5 orders. Order `304-5999696-6159543` has 4 items across **2 packages** (`UJxfPvsSv`: STECKEL + tesa weiss; `U1YGxTsPv`: Aigostar qty 2 + tesa schwarz). The Audible order and the `D01-9216861-…` Castle order are `digital`. Castle item has empty asin. Book ASIN is `3837164764`.

### Fixture B — Bestelldetails view (per-item price + seller)

```
Bestellung aufgegeben
3. Januar 2024
* Summe
16,89 €
* Bestellnr. 303-7326140-5220339
* [Bestelldetails anzeigen ](https://www.amazon.de/your-orders/order-details?orderID=303-7326140-5220339)[Rechnung](https://www.amazon.de/your-orders/invoice/popover?orderId=303-7326140-5220339)

* [Baehr Handcreme Maracuja mit Passionsblumenöl und Urea 75 ml](https://www.amazon.de/dp/B00BYRMMCW?ref_=x)
Verkauf durch: [FISH SPA & MORE](https://www.amazon.de/gp/aag/main?seller=A14RX3M6ECFU5W)
9,90€
[Nochmals kaufen](https://www.amazon.de/gp/buyagain?ats=x)
[ Deinen Artikel anzeigen](https://www.amazon.de/your-orders/pop?orderId=303-7326140-5220339&shipmentId=U1qYPH4xv&asin=B00BYRMMCW)
[Deutsche Post - Packpapier 5 Bogen - 70 x 100 cm](https://www.amazon.de/dp/B00EJBP6A0?ref_=x)
Verkauf durch: [HeiTrade GmbH](https://www.amazon.de/gp/aag/main?seller=A71MIBP6Z4N8L)
 Zeitraum für Produkt-Support endet am 30. Januar 2026
6,99€
[Nochmals kaufen](https://www.amazon.de/gp/buyagain?ats=x)
[ Deinen Artikel anzeigen](https://www.amazon.de/your-orders/pop?orderId=303-7326140-5220339&shipmentId=DKHqm9zdr&asin=B00EJBP6A0)
```

Expected for Fixture B: 1 order, 2 items. Baehr Handcreme: price `9,90`, seller `FISH SPA & MORE`, asin `B00BYRMMCW`. Deutsche Post Packpapier: price `6,99`, seller `HeiTrade GmbH`, asin `B00EJBP6A0`.

---

## Deliverables for Step 1

- `init_db.py` (or similar) — creates the SQLite schema above.
- the parser as a clean, importable, standalone function (no UI, no DB writes).
- a test file with Fixtures A and B embedded, asserting the above.
- a one-line command to run the tests.
- a short README note on how to run init + tests.

Keep it simple and readable. Stop after Step 1 — do not start on the UI or any saving logic. When done, show me the parser output for both fixtures and the passing test run.
