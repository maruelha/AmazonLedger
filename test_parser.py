import os
import sqlite3
import tempfile

import pytest

from db import (EXPORT_COLUMNS, generate_csv, get_export_rows,
                get_filtered_orders, get_connection, save_orders)
from html_to_md import html_to_markdown
from init_db import init_db
from parser import parse_orders

FIXTURE_A = """\
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
"""

FIXTURE_B = """\
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
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _order(orders, order_no):
    return next(o for o in orders if o['order_no'] == order_no)

def _all_items(order):
    return [item for pkg in order['packages'] for item in pkg['items']]

def _pkg(order, shipment_id):
    return next(p for p in order['packages'] if p['shipment_id'] == shipment_id)


# ---------------------------------------------------------------------------
# Fixture A tests
# ---------------------------------------------------------------------------

def test_a_order_count():
    assert len(parse_orders(FIXTURE_A)) == 5


def test_a_dates():
    orders = parse_orders(FIXTURE_A)
    assert _order(orders, '305-7591774-5703526')['order_date'] == '2024-01-10'
    assert _order(orders, '304-5999696-6159543')['order_date'] == '2024-01-09'
    assert _order(orders, 'D01-8912984-6191037')['order_date'] == '2024-01-09'
    assert _order(orders, '306-4726240-6689959')['order_date'] == '2024-01-07'
    assert _order(orders, 'D01-9216861-8357444')['order_date'] == '2024-01-07'


def test_a_totals():
    orders = parse_orders(FIXTURE_A)
    assert _order(orders, '305-7591774-5703526')['order_total'] == '2,39'
    assert _order(orders, '304-5999696-6159543')['order_total'] == '49,41'
    assert _order(orders, 'D01-8912984-6191037')['order_total'] == '9,95'
    assert _order(orders, '306-4726240-6689959')['order_total'] == '19,45'
    assert _order(orders, 'D01-9216861-8357444')['order_total'] == '12,50'


def test_a_types():
    orders = parse_orders(FIXTURE_A)
    assert _order(orders, '305-7591774-5703526')['type'] == 'physisch'
    assert _order(orders, '304-5999696-6159543')['type'] == 'physisch'
    assert _order(orders, 'D01-8912984-6191037')['type'] == 'digital'   # Abonnement
    assert _order(orders, '306-4726240-6689959')['type'] == 'physisch'
    assert _order(orders, 'D01-9216861-8357444')['type'] == 'digital'   # D01- prefix


def test_a_packages_for_multi_package_order():
    order = _order(parse_orders(FIXTURE_A), '304-5999696-6159543')
    shipment_ids = {p['shipment_id'] for p in order['packages']}
    assert shipment_ids == {'UJxfPvsSv', 'U1YGxTsPv'}

    pkg1 = _pkg(order, 'UJxfPvsSv')
    assert len(pkg1['items']) == 2
    asins_pkg1 = {i['asin'] for i in pkg1['items']}
    assert asins_pkg1 == {'B0CG638LRS', 'B000KTBE9M'}

    pkg2 = _pkg(order, 'U1YGxTsPv')
    assert len(pkg2['items']) == 2
    asins_pkg2 = {i['asin'] for i in pkg2['items']}
    assert asins_pkg2 == {'B08J7JDGKL', 'B0001M0H3M'}


def test_a_aigostar_quantity():
    order = _order(parse_orders(FIXTURE_A), '304-5999696-6159543')
    aigostar = next(i for i in _all_items(order) if i['asin'] == 'B08J7JDGKL')
    assert aigostar['qty'] == 2


def test_a_book_asin():
    order = _order(parse_orders(FIXTURE_A), '306-4726240-6689959')
    items = _all_items(order)
    assert len(items) == 1
    assert items[0]['asin'] == '3837164764'


def test_a_prime_video_no_asin():
    order = _order(parse_orders(FIXTURE_A), 'D01-9216861-8357444')
    items = _all_items(order)
    assert len(items) == 1
    assert items[0]['asin'] is None


def test_a_noise_links_excluded():
    orders = parse_orders(FIXTURE_A)
    noise_phrases = [
        'Nochmals kaufen', 'Schreib eine Produktrezension',
        'Bestelldetails anzeigen', 'Meine Video-Bibliothek',
    ]
    for order in orders:
        for item in _all_items(order):
            for phrase in noise_phrases:
                assert phrase not in item['name']


# ---------------------------------------------------------------------------
# Fixture B tests
# ---------------------------------------------------------------------------

def test_b_order_count():
    assert len(parse_orders(FIXTURE_B)) == 1


def test_b_baehr_handcreme():
    order = parse_orders(FIXTURE_B)[0]
    baehr = next(i for i in _all_items(order) if i['asin'] == 'B00BYRMMCW')
    assert baehr['price'] == '9,90'
    assert baehr['seller'] == 'FISH SPA & MORE'


def test_b_deutsche_post():
    order = parse_orders(FIXTURE_B)[0]
    dp = next(i for i in _all_items(order) if i['asin'] == 'B00EJBP6A0')
    assert dp['price'] == '6,99'
    assert dp['seller'] == 'HeiTrade GmbH'


def test_b_two_separate_packages():
    order = parse_orders(FIXTURE_B)[0]
    shipment_ids = {p['shipment_id'] for p in order['packages']}
    assert shipment_ids == {'U1qYPH4xv', 'DKHqm9zdr'}


# ---------------------------------------------------------------------------
# Step 2 — save logic tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db():
    f = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    f.close()
    init_db(f.name)
    conn = get_connection(f.name)   # row_factory needed by get_filtered_orders / get_export_rows
    yield conn
    conn.close()
    os.unlink(f.name)


def test_save_inserts_correct_counts(tmp_db):
    orders = parse_orders(FIXTURE_A)
    result, skipped = save_orders(tmp_db, orders, {}, {}, {})

    assert skipped == 0
    assert result['orders'] == 5
    assert tmp_db.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 5


def test_save_correct_fk_relationships(tmp_db):
    orders = parse_orders(FIXTURE_A)
    save_orders(tmp_db, orders, {}, {}, {})

    row = tmp_db.execute(
        "SELECT id FROM orders WHERE order_no = '304-5999696-6159543'"
    ).fetchone()
    order_id = row[0]

    pkg_count = tmp_db.execute(
        'SELECT COUNT(*) FROM packages WHERE order_id = ?', (order_id,)
    ).fetchone()[0]
    item_count = tmp_db.execute(
        'SELECT COUNT(*) FROM items WHERE order_id = ?', (order_id,)
    ).fetchone()[0]

    assert pkg_count == 2
    assert item_count == 4


def test_save_persists_tax_flag_and_amount(tmp_db):
    orders = parse_orders(FIXTURE_A)
    # Mark first item of first package of first order as tax-relevant, give it an amount
    tax_flags = {'0__0__0': True}
    item_amounts = {'0__0__0': '2,39'}
    save_orders(tmp_db, orders, tax_flags, item_amounts, {})

    row = tmp_db.execute(
        'SELECT tax_relevant, item_amount FROM items WHERE order_id = '
        '(SELECT id FROM orders WHERE order_no = "305-7591774-5703526") LIMIT 1'
    ).fetchone()
    assert row[0] == 1
    assert row[1] == '2,39'


def test_save_dedupe_skips_existing(tmp_db):
    orders = parse_orders(FIXTURE_A)

    # First save
    result1, skipped1 = save_orders(tmp_db, orders, {}, {}, {})
    assert result1['orders'] == 5
    assert skipped1 == 0

    # Second save — all 5 orders already exist
    result2, skipped2 = save_orders(tmp_db, orders, {}, {}, {})
    assert result2['orders'] == 0
    assert skipped2 == 5

    # DB row count unchanged
    assert tmp_db.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 5
    assert tmp_db.execute('SELECT COUNT(*) FROM items').fetchone()[0] == \
           tmp_db.execute('SELECT COUNT(*) FROM items').fetchone()[0]


# ---------------------------------------------------------------------------
# Step 3 — filter + CSV export tests
# ---------------------------------------------------------------------------

def test_year_filter(tmp_db):
    save_orders(tmp_db, parse_orders(FIXTURE_A), {}, {}, {})
    assert len(get_filtered_orders(tmp_db, year='2024')) == 5
    assert len(get_filtered_orders(tmp_db, year='2023')) == 0


def test_tax_relevant_filter(tmp_db):
    save_orders(tmp_db, parse_orders(FIXTURE_A), {}, {}, {})
    tmp_db.execute('UPDATE items SET tax_relevant=1 WHERE id=(SELECT MIN(id) FROM items)')
    tmp_db.commit()
    tax_orders = get_filtered_orders(tmp_db, tax_relevant_only=True)
    assert len(tax_orders) == 1
    all_items = [i for o in tax_orders for p in o['packages'] for i in p['items']]
    assert len(all_items) == 1


def test_year_and_tax_filter_combined(tmp_db):
    save_orders(tmp_db, parse_orders(FIXTURE_A), {}, {}, {})
    tmp_db.execute('UPDATE items SET tax_relevant=1 WHERE id=(SELECT MIN(id) FROM items)')
    tmp_db.commit()
    assert len(get_filtered_orders(tmp_db, year='2024', tax_relevant_only=True)) == 1
    assert len(get_filtered_orders(tmp_db, year='2023', tax_relevant_only=True)) == 0


def test_export_invoice_fallback(tmp_db):
    """invoice_name resolution: item overrides package; package is fallback; blank if neither."""
    save_orders(tmp_db, parse_orders(FIXTURE_B), {}, {}, {})
    tmp_db.execute("UPDATE items SET tax_relevant=1")

    # B00EJBP6A0 is in shipment DKHqm9zdr — set only package invoice → fallback to package
    tmp_db.execute("UPDATE packages SET invoice_name='SHIP-INV' WHERE shipment_id='DKHqm9zdr'")
    # B00BYRMMCW is in shipment U1qYPH4xv — set both package and item invoice → item wins
    tmp_db.execute("UPDATE packages SET invoice_name='PKG-INV' WHERE shipment_id='U1qYPH4xv'")
    tmp_db.execute("UPDATE items SET invoice_name='ITEM-INV' WHERE asin='B00BYRMMCW'")
    tmp_db.commit()

    rows = get_export_rows(tmp_db)
    by_asin = {r['asin']: r for r in rows}

    assert by_asin['B00BYRMMCW']['invoice_name'] == 'ITEM-INV'   # item overrides package
    assert by_asin['B00EJBP6A0']['invoice_name'] == 'SHIP-INV'  # package fallback

    # Blank: clear both → invoice_name is None
    tmp_db.execute("UPDATE packages SET invoice_name=NULL WHERE shipment_id='DKHqm9zdr'")
    tmp_db.commit()
    rows2 = get_export_rows(tmp_db)
    by_asin2 = {r['asin']: r for r in rows2}
    assert by_asin2['B00EJBP6A0']['invoice_name'] is None        # blank when neither set


def test_csv_only_tax_relevant(tmp_db):
    save_orders(tmp_db, parse_orders(FIXTURE_B), {}, {}, {})
    tmp_db.execute("UPDATE items SET tax_relevant=1 WHERE asin='B00BYRMMCW'")
    tmp_db.commit()
    rows = get_export_rows(tmp_db)
    csv_text = generate_csv(rows)
    lines = csv_text.lstrip('﻿').splitlines()
    assert len(lines) == 2                        # header + 1 data row
    assert 'B00BYRMMCW' in lines[1]
    assert 'B00EJBP6A0' not in csv_text           # non-relevant item excluded


def test_csv_blank_amount_included(tmp_db):
    save_orders(tmp_db, parse_orders(FIXTURE_B), {}, {}, {})
    tmp_db.execute("UPDATE items SET tax_relevant=1, item_amount=NULL WHERE asin='B00EJBP6A0'")
    tmp_db.commit()
    rows = get_export_rows(tmp_db)
    csv_text = generate_csv(rows)
    lines = csv_text.lstrip('﻿').splitlines()
    assert len(lines) == 2
    assert 'B00EJBP6A0' in lines[1]   # item present despite blank amount


# ---------------------------------------------------------------------------
# HTML → Markdown conversion (mirrors the JS paste handler)
# ---------------------------------------------------------------------------

_HTML_FRAGMENT = """\
<div>Bestellung aufgegeben</div>
<div>3. Januar 2024</div>
<div>Summe</div>
<div>16,89 €</div>
<div>Bestellnr. 303-0000001-0000001</div>
<div><a href="https://www.amazon.de/dp/B0D2SVRC4W?ref=x">DAOUZL Sonnenblume</a></div>
<div><a href="https://www.amazon.de/your-orders/pop?orderId=303-0000001-0000001&amp;shipmentId=SHIP99&amp;asin=B0D2SVRC4W"> Deinen Artikel anzeigen</a></div>
"""


def test_html_to_markdown_links_preserved():
    md = html_to_markdown(_HTML_FRAGMENT)
    assert '[DAOUZL Sonnenblume](https://www.amazon.de/dp/B0D2SVRC4W?ref=x)' in md
    assert '?ref=x' in md                        # query string intact
    assert 'shipmentId=SHIP99' in md             # shipmentId survives &amp; unescape


def test_html_to_markdown_end_to_end():
    """HTML→markdown conversion feeds correctly into the existing parser."""
    md = html_to_markdown(_HTML_FRAGMENT)
    orders = parse_orders(md)
    assert len(orders) == 1
    items = [i for p in orders[0]['packages'] for i in p['items']]
    assert len(items) == 1
    assert items[0]['asin'] == 'B0D2SVRC4W'
    assert orders[0]['packages'][0]['shipment_id'] == 'SHIP99'


def test_csv_format(tmp_db):
    save_orders(tmp_db, parse_orders(FIXTURE_B), {}, {}, {})
    tmp_db.execute("UPDATE items SET tax_relevant=1, item_amount='9,90' WHERE asin='B00BYRMMCW'")
    tmp_db.execute("UPDATE items SET tax_relevant=1 WHERE asin='B00EJBP6A0'")
    tmp_db.commit()
    csv_text = generate_csv(get_export_rows(tmp_db))

    # UTF-8 BOM present
    assert csv_text.startswith('﻿')

    lines = csv_text.lstrip('﻿').splitlines()
    assert len(lines) == 3             # header + 2 items

    # semicolon separator + correct column order
    assert lines[0].split(';') == list(EXPORT_COLUMNS)

    # comma decimal preserved (not converted to dot)
    assert '9,90' in csv_text
