from flask import Flask, request, jsonify
import sqlite3
import json
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

DATABASE = 'database.db'


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        with open('database.sql', 'r') as f:
            conn.executescript(f.read())


def generate_token(user_id):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return s.dumps({'user_id': user_id})


def verify_token(token):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        data = s.loads(token, max_age=3600)  # Токен дійсний тількм 1 годину
    except Exception:
        return None
    return data.get('user_id')


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    login = data.get('login')
    password = data.get('password')

    if not login or not password:
        return jsonify({'message': 'Login and password are required'}), 400

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE login = ?", (login,))
        if cursor.fetchone():
            return jsonify({'message': 'User already exists'}), 409

        cursor.execute("INSERT INTO users (login, password) VALUES (?, ?)", (login, password))
        conn.commit()

    return jsonify({'message': 'User registered successfully'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    login = data.get('login')
    password = data.get('password')

    if not login or not password:
        return jsonify({'message': 'Login and password are required'}), 400

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE login = ? AND password = ?", (login, password))
        user = cursor.fetchone()

        if not user:
            return jsonify({'message': 'Invalid credentials'}), 401

        token = generate_token(user[0])
        return jsonify({'user_id': user[0], 'token': token}), 200


@app.route('/balance', methods=['POST'])
def get_balance():
    data = request.json
    token = data.get('token')
    user_id = data.get('user_id')

    if not token or not user_id:
        return jsonify({'message': 'Token and user ID are required'}), 400

    user_id_from_token = verify_token(token)
    if user_id_from_token != int(user_id):
        return jsonify({'message': 'Invalid token'}), 400

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({'message': 'User not found'}), 404

    return jsonify({'balance': result[0]}), 200


@app.route('/transactions', methods=['POST'])
def get_transactions():
    data = request.json
    token = data.get('token')
    user_id = data.get('user_id')

    if not token or not user_id:
        return jsonify({'message': 'Token and user ID are required'}), 400

    user_id_from_token = verify_token(token)
    if user_id_from_token != int(user_id):
        return jsonify({'message': 'Invalid token'}), 400

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT transactions FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({'message': 'User not found'}), 404

        transactions = json.loads(result[0]) if result[0] else {}

    return jsonify({'transactions': transactions}), 200


@app.route('/transaction', methods=['POST'])
def process_transaction():
    data = request.json
    token = data.get('token')
    user_id = data.get('user_id')
    transaction_value = data.get('transaction_value')

    if not token or not user_id or transaction_value is None:
        return jsonify({'message': 'Token, user ID, and transaction value are required'}), 400

    user_id_from_token = verify_token(token)
    if user_id_from_token != int(user_id):
        return jsonify({'message': 'Invalid token'}), 400

    if not isinstance(transaction_value, int):
        return jsonify({'message': 'Transaction value must be an integer'}), 400

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT balance, transactions FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({'message': 'User not found'}), 404

        balance, transactions_json = result
        transactions = json.loads(transactions_json)

        balance += transaction_value

        transaction_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        transactions[transaction_date] = transaction_value

        cursor.execute("UPDATE users SET balance = ?, transactions = ? WHERE id = ?", 
                       (balance, json.dumps(transactions), user_id))
        conn.commit()

    return jsonify({
        'message': 'Transaction processed successfully',
        'new_balance': balance,
        'transactions': transactions
    }), 200


@app.route('/delete_user', methods=['DELETE'])
def delete_user():
    data = request.json
    token = data.get('token')
    user_id = data.get('user_id')

    if not token or not user_id:
        return jsonify({'message': 'Token and user ID are required'}), 400

    user_id_from_token = verify_token(token)
    if user_id_from_token != int(user_id):
        return jsonify({'message': 'Invalid token'}), 400

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({'message': 'User not found'}), 404

        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

    return jsonify({'message': 'User deleted successfully'}), 200


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'Server is running'}), 200


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
