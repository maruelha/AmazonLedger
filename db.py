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
