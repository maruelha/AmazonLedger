import json
import os

from flask import Flask, redirect, render_template, request, Response

from db import (clear_db, delete_items, delete_orders, generate_csv,
                get_all_orders, get_connection, get_export_rows,
                get_filtered_orders, get_years, save_edits, save_orders)
from parser import parse_orders

app = Flask(__name__)
DB_PATH = os.environ.get('DB_PATH', 'amazon_ledger.db')


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/parse', methods=['POST'])
def parse():
    text = request.form.get('paste', '')
    orders = parse_orders(text)
    return render_template('review.html', orders=orders, parsed_json=json.dumps(orders, ensure_ascii=False))


@app.route('/save', methods=['POST'])
def save():
    orders = json.loads(request.form.get('parsed_json', '[]'))

    tax_flags = {}
    item_amounts = {}
    shipment_amounts = {}

    for key, value in request.form.items():
        if key.startswith('tax_relevant__'):
            tax_flags[key[len('tax_relevant__'):]] = True
        elif key.startswith('item_amount__'):
            item_amounts[key[len('item_amount__'):]] = value
        elif key.startswith('shipment_amount__'):
            shipment_amounts[key[len('shipment_amount__'):]] = value

    conn = get_connection(DB_PATH)
    result, skipped = save_orders(conn, orders, tax_flags, item_amounts, shipment_amounts)
    conn.close()

    return render_template('done.html', result=result, skipped=skipped)


@app.route('/manage')
def manage():
    conn = get_connection(DB_PATH)
    orders = get_all_orders(conn)
    conn.close()
    return render_template('manage.html', orders=orders)


@app.route('/manage/delete', methods=['POST'])
def manage_delete():
    order_ids = [int(x) for x in request.form.getlist('order_id')]
    item_ids  = [int(x) for x in request.form.getlist('item_id')]
    conn = get_connection(DB_PATH)
    if order_ids:
        delete_orders(conn, order_ids)
    if item_ids:
        delete_items(conn, item_ids)
    conn.close()
    return redirect('/manage')


@app.route('/manage/clear', methods=['POST'])
def manage_clear():
    conn = get_connection(DB_PATH)
    clear_db(conn)
    conn.close()
    return redirect('/manage')


@app.route('/browse')
def browse():
    year    = request.args.get('year', '')
    tax_rel = request.args.get('tax_rel', '') == '1'
    conn = get_connection(DB_PATH)
    years  = get_years(conn)
    orders = get_filtered_orders(conn, year=year or None, tax_relevant_only=tax_rel)
    conn.close()
    return render_template('browse.html', orders=orders, years=years,
                           selected_year=year, tax_rel=tax_rel)


@app.route('/browse/save', methods=['POST'])
def browse_save():
    year    = request.form.get('year', '')
    tax_rel = request.form.get('tax_rel', '')
    item_ids = [int(x) for x in request.form.getlist('item_ids')]
    pkg_ids  = [int(x) for x in request.form.getlist('pkg_ids')]
    conn = get_connection(DB_PATH)
    save_edits(conn, request.form, item_ids, pkg_ids)
    conn.close()
    parts = [p for p in [f'year={year}' if year else '',
                          f'tax_rel={tax_rel}' if tax_rel else ''] if p]
    return redirect(f'/browse?{"&".join(parts)}')


@app.route('/export')
def export():
    year = request.args.get('year', '')
    conn = get_connection(DB_PATH)
    rows = get_export_rows(conn, year=year or None)
    conn.close()
    csv_bytes = generate_csv(rows).encode('utf-8')
    fname = f'amazon_steuer{"_" + year if year else ""}.csv'
    return Response(csv_bytes, mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="{fname}"'})


if __name__ == '__main__':
    app.run(debug=True)
