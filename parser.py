import re

GERMAN_MONTHS = {
    'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4,
    'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
    'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12,
}

NOISE_TEXTS = [
    'Nochmals kaufen',
    'Deinen Artikel anzeigen',
    'Schreib eine Produktrezension',
    'Bestelldetails anzeigen',
    'Rechnung',
    'Problem bei Bestellung',
    'Eine Frage zum Produkt stellen',
    'Meine Video-Bibliothek',
]


def _clean(line):
    return re.sub(r'^\*\s*', '', line).strip()


def _parse_date(s):
    m = re.match(r'(\d+)\.\s+(\w+)\s+(\d{4})', s)
    if not m:
        return None
    day, month_name, year = m.groups()
    month = GERMAN_MONTHS.get(month_name)
    if not month:
        return None
    return f"{year}-{month:02d}-{int(day):02d}"


def _is_noise(text):
    return any(n in text for n in NOISE_TEXTS)


def _links(line):
    return re.findall(r'\[([^\]]*)\]\(([^)]+)\)', line)


def _find_product(line_links):
    """Return (name, asin_or_None) for the first real product link, else None."""
    for text, url in line_links:
        if _is_noise(text):
            continue
        m = re.search(r'/dp/([A-Z0-9]{10})', url, re.IGNORECASE)
        if m:
            return text.strip(), m.group(1).upper()
        if '/gp/video/detail/' in url:
            return text.strip(), None
    return None


def _parse_items(lines):
    items = []
    pending_qty = 1
    cur = None

    for line in lines:
        lnks = _links(line)

        # Capture shipmentId from the "Deinen Artikel anzeigen" link into current item
        for text, url in lnks:
            if 'Deinen Artikel anzeigen' in text and cur is not None:
                m = re.search(r'shipmentId=([^&)]+)', url)
                if m:
                    cur['shipment_id'] = m.group(1)

        product = _find_product(lnks)
        if product:
            if cur is not None:
                items.append(cur)
            name, asin = product
            cur = {
                'name': name,
                'asin': asin,
                'qty': pending_qty,
                'seller': None,
                'price': None,
                'shipment_id': None,
            }
            pending_qty = 1
            continue

        # Bare integer on its own line = quantity for the next item
        if re.match(r'^\d+$', line):
            pending_qty = int(line)
            continue

        if cur is not None:
            if line.startswith('Verkauf durch:'):
                seller_lnks = _links(line)
                if seller_lnks:
                    cur['seller'] = seller_lnks[0][0]
            elif re.match(r'^[\d,]+€$', line):
                cur['price'] = re.match(r'^([\d,]+)€$', line).group(1)

    if cur is not None:
        items.append(cur)
    return items


def _parse_block(lines):
    order = {
        'order_no': None,
        'order_date': None,
        'order_total': None,
        'type': 'physisch',
        'packages': [],
    }

    if lines and lines[0].startswith('Abonnement abgerechnet am'):
        order['type'] = 'digital'

    expect_total = False
    for i, line in enumerate(lines):
        if i == 1:
            d = _parse_date(line)
            if d:
                order['order_date'] = d

        if line == 'Summe':
            expect_total = True
            continue

        if expect_total:
            m = re.match(r'^([\d,]+)\s*€', line)
            if m:
                order['order_total'] = m.group(1)
            expect_total = False
            continue

        m = re.match(r'Bestellnr\.\s+(\S+)', line)
        if m:
            order['order_no'] = m.group(1)
            if order['order_no'].startswith('D0'):
                order['type'] = 'digital'

    items = _parse_items(lines)

    # Group items into packages keyed by shipment_id (preserves insertion order)
    buckets: dict = {}
    for item in items:
        sid = item['shipment_id']
        if sid not in buckets:
            buckets[sid] = []
        buckets[sid].append({
            'name': item['name'],
            'asin': item['asin'],
            'qty': item['qty'],
            'seller': item['seller'],
            'price': item['price'],
        })

    order['packages'] = [
        {'shipment_id': sid, 'line_items': pkg_items}
        for sid, pkg_items in buckets.items()
    ]
    return order


def parse_orders(text: str) -> list:
    """Parse one or more pasted Amazon order blocks and return a list of order dicts."""
    lines = [_clean(l) for l in text.split('\n')]

    boundaries = [
        i for i, l in enumerate(lines)
        if l.startswith('Bestellung aufgegeben') or l.startswith('Abonnement abgerechnet am')
    ]

    orders = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        orders.append(_parse_block(lines[start:end]))
    return orders
