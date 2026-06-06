import json
import os

from flask import Flask, redirect, render_template, request

from db import (clear_db, delete_items, delete_orders, get_all_orders,
                get_connection, save_orders)
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


if __name__ == '__main__':
    app.run(debug=True)
