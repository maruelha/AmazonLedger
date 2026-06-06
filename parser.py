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

_ORDER_NO_RE = re.compile(r'([A-Z0-9]{3}-\d{7}-\d{7})', re.IGNORECASE)


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


def _join_split_links(lines):
    """
    Merge lines that are continuation of a multi-line markdown link.
    Amazon's HTML-to-markdown paste sometimes splits long product names
    across lines.  A line that starts with '[' but has no '](' is the
    beginning of such a split; merge subsequent lines until '](' appears.
    """
    out = []
    buf = None
    for line in lines:
        if buf is not None:
            buf = buf + ' ' + line
            if '](' in buf:
                out.append(buf)
                buf = None
        elif line.startswith('[') and '](' not in line:
            buf = line
        else:
            out.append(line)
    if buf is not None:
        out.append(buf)
    return out


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

    # Work from non-blank lines so blank/whitespace-only noise between fields
    # doesn't prevent finding values (real clipboard has many such lines).
    content = [l for l in lines if l]

    if content and content[0].startswith('Abonnement abgerechnet am'):
        order['type'] = 'digital'

    # Date: first content line after the boundary (skip any blanks)
    if len(content) > 1:
        d = _parse_date(content[1])
        if d:
            order['order_date'] = d

    # Total: content line immediately after 'Summe'
    for i, line in enumerate(content):
        if line == 'Summe' and i + 1 < len(content):
            m = re.match(r'^([\d,]+)\s*€', content[i + 1])
            if m:
                order['order_total'] = m.group(1)
            break

    # Order number: may be on the same line as 'Bestellnr.' (clean format)
    # or on the next content line (real clipboard puts them on separate lines)
    for i, line in enumerate(content):
        if 'Bestellnr.' in line:
            m = _ORDER_NO_RE.search(line)
            if m:
                order['order_no'] = m.group(1)
            else:
                for j in range(i + 1, min(i + 4, len(content))):
                    m = _ORDER_NO_RE.search(content[j])
                    if m:
                        order['order_no'] = m.group(1)
                        break
            if order['order_no'] and order['order_no'].startswith('D0'):
                order['type'] = 'digital'
            break

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
    lines = _join_split_links([_clean(l) for l in text.split('\n')])

    boundaries = [
        i for i, l in enumerate(lines)
        if l.startswith('Bestellung aufgegeben') or l.startswith('Abonnement abgerechnet am')
    ]

    orders = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        orders.append(_parse_block(lines[start:end]))
    return orders
