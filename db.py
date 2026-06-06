import csv
import io
import sqlite3


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_orders(conn):
    orders = conn.execute(
        'SELECT * FROM orders ORDER BY order_date DESC, order_no'
    ).fetchall()
    result = []
    for order in orders:
        order = dict(order)
        packages = conn.execute(
            'SELECT * FROM packages WHERE order_id = ?', (order['id'],)
        ).fetchall()
        order['packages'] = []
        for pkg in packages:
            pkg = dict(pkg)
            pkg['items'] = [
                dict(i) for i in conn.execute(
                    'SELECT * FROM items WHERE package_id = ?', (pkg['id'],)
                ).fetchall()
            ]
            order['packages'].append(pkg)
        result.append(order)
    return result


def delete_orders(conn, order_ids):
    for oid in order_ids:
        conn.execute('DELETE FROM items    WHERE order_id = ?', (oid,))
        conn.execute('DELETE FROM packages WHERE order_id = ?', (oid,))
        conn.execute('DELETE FROM orders   WHERE id = ?',       (oid,))
    conn.commit()


def delete_items(conn, item_ids):
    for iid in item_ids:
        conn.execute('DELETE FROM items WHERE id = ?', (iid,))
    conn.commit()


def get_years(conn):
    rows = conn.execute(
        "SELECT DISTINCT strftime('%Y', order_date) AS y FROM orders "
        "WHERE order_date IS NOT NULL ORDER BY y DESC"
    ).fetchall()
    return [r['y'] for r in rows]


def get_filtered_orders(conn, year=None, tax_relevant_only=False):
    q = 'SELECT * FROM orders WHERE 1=1'
    params = []
    if year:
        q += " AND strftime('%Y', order_date) = ?"
        params.append(str(year))
    q += ' ORDER BY order_date DESC, order_no'

    result = []
    for order in [dict(r) for r in conn.execute(q, params).fetchall()]:
        order['packages'] = []
        has_items = False

        for pkg in [dict(p) for p in conn.execute(
            'SELECT * FROM packages WHERE order_id = ? ORDER BY id', (order['id'],)
        ).fetchall()]:
            item_q = 'SELECT * FROM items WHERE package_id = ?'
            item_p = [pkg['id']]
            if tax_relevant_only:
                item_q += ' AND tax_relevant = 1'
            item_q += ' ORDER BY id'
            pkg['items'] = [dict(i) for i in conn.execute(item_q, item_p).fetchall()]
            if pkg['items']:
                order['packages'].append(pkg)
                has_items = True

        if not tax_relevant_only or has_items:
            result.append(order)
    return result


def save_edits(conn, form, item_ids, pkg_ids):
    for iid in item_ids:
        conn.execute(
            'UPDATE items SET tax_relevant=?, tax_tag=?, item_amount=?, invoice_name=? WHERE id=?',
            (
                1 if f'item_{iid}_tax_relevant' in form else 0,
                1 if f'item_{iid}_tax_tag' in form else 0,
                _normalize(form.get(f'item_{iid}_item_amount', '')),
                form.get(f'item_{iid}_invoice_name', '').strip() or None,
                iid,
            )
        )
    for pid in pkg_ids:
        conn.execute(
            'UPDATE packages SET shipment_amount=?, invoice_name=? WHERE id=?',
            (
                _normalize(form.get(f'package_{pid}_shipment_amount', '')),
                form.get(f'package_{pid}_invoice_name', '').strip() or None,
                pid,
            )
        )
    conn.commit()


EXPORT_COLUMNS = [
    'order_date', 'order_no', 'type', 'shipment_id', 'item_name', 'asin',
    'qty', 'seller', 'item_amount', 'shipment_amount', 'tax_tag',
    'order_total', 'invoice_name',
]


def get_export_rows(conn, year=None):
    q = '''
        SELECT
            o.order_date, o.order_no, o.type, p.shipment_id,
            i.name   AS item_name, i.asin, i.qty, i.seller,
            i.item_amount, p.shipment_amount, i.tax_tag,
            o.order_total,
            COALESCE(i.invoice_name, p.invoice_name) AS invoice_name
        FROM items i
        JOIN packages p ON p.id = i.package_id
        JOIN orders  o ON o.id = i.order_id
        WHERE i.tax_relevant = 1
    '''
    params = []
    if year:
        q += " AND strftime('%Y', o.order_date) = ?"
        params.append(str(year))
    q += ' ORDER BY o.order_date, o.order_no, p.id, i.id'
    return [dict(r) for r in conn.execute(q, params).fetchall()]


def generate_csv(rows):
    """UTF-8-with-BOM, semicolon-delimited CSV (German-Excel-safe)."""
    out = io.StringIO()
    out.write('﻿')  # BOM
    w = csv.writer(out, delimiter=';', quoting=csv.QUOTE_MINIMAL, lineterminator='\r\n')
    w.writerow(EXPORT_COLUMNS)
    for row in rows:
        w.writerow(['' if row.get(col) is None else row[col] for col in EXPORT_COLUMNS])
    return out.getvalue()


def clear_db(conn):
    conn.execute('DELETE FROM items')
    conn.execute('DELETE FROM packages')
    conn.execute('DELETE FROM orders')
    conn.commit()


def _normalize(s):
    """Strip whitespace, return None if empty, replace decimal dot with comma."""
    s = (s or '').strip()
    return s.replace('.', ',') if s else None


def save_orders(conn, orders, tax_flags, item_amounts, shipment_amounts):
    """
    Insert orders/packages/items from parser output.
    Skips any order whose order_no already exists (skip-and-report).
    Returns (saved_counts_dict, skipped_count).
    """
    saved = {'orders': 0, 'packages': 0, 'items': 0}
    skipped = 0

    for i, order in enumerate(orders):
        existing = conn.execute(
            'SELECT id FROM orders WHERE order_no = ?', (order['order_no'],)
        ).fetchone()

        if existing:
            skipped += 1
            continue

        cur = conn.execute(
            'INSERT INTO orders (order_no, order_date, order_total, type) VALUES (?, ?, ?, ?)',
            (order['order_no'], order['order_date'], order['order_total'], order['type']),
        )
        order_id = cur.lastrowid
        saved['orders'] += 1

        for j, pkg in enumerate(order['packages']):
            s_amount = _normalize(shipment_amounts.get(f'{i}__{j}', ''))
            cur = conn.execute(
                'INSERT INTO packages (order_id, shipment_id, shipment_amount) VALUES (?, ?, ?)',
                (order_id, pkg['shipment_id'], s_amount),
            )
            pkg_id = cur.lastrowid
            saved['packages'] += 1

            for k, item in enumerate(pkg['items']):
                tax_rel = 1 if tax_flags.get(f'{i}__{j}__{k}') else 0
                i_amount = _normalize(item_amounts.get(f'{i}__{j}__{k}', ''))

                conn.execute(
                    '''INSERT INTO items
                         (order_id, package_id, name, asin, qty, seller, item_amount, tax_relevant)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (order_id, pkg_id, item['name'], item['asin'],
                     item['qty'], item['seller'], i_amount, tax_rel),
                )
                saved['items'] += 1

    conn.commit()
    return saved, skipped
