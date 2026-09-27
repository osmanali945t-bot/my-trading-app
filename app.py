from flask import Flask, render_template, request, jsonify
from tradingview_ta import TA_Handler, Interval
import datetime
import sqlite3
import os

app = Flask(__name__)

# আপনার পছন্দমতো অ্যাডমিন সিক্রেট কি
ADMIN_SECRET_KEY = "MD@OSMAN@ALI153"

# SQLite ডেটাবেস ইনিশিয়ালাইজেশন
def init_db():
    conn = sqlite3.connect('trading_users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# অ্যাপ চালু হওয়ার সাথে সাথে ডেটাবেস টেবিল চেক হবে
init_db()

def analyze_market_deep(symbol="EURUSD", duration=5):
    try:
        tf_map = {
            1: Interval.INTERVAL_1_MINUTE,
            3: Interval.INTERVAL_3_MINUTES,
            5: Interval.INTERVAL_5_MINUTES,
            15: Interval.INTERVAL_15_MINUTES,
            30: Interval.INTERVAL_30_MINUTES,
            60: Interval.INTERVAL_1_HOUR
        }
        interval_to_use = tf_map.get(duration, Interval.INTERVAL_5_MINUTES)
        
        try:
            handler = TA_Handler(
                symbol=symbol,
                screener="forex",
                exchange="FX_IDC",
                interval=interval_to_use
            )
            analysis = handler.get_analysis()
        except Exception:
            handler = TA_Handler(
                symbol=symbol,
                screener="forex",
                exchange="OANDA",
                interval=interval_to_use
            )
            analysis = handler.get_analysis()
        
        summary = analysis.summary.get('RECOMMENDATION', 'NEUTRAL')
        osc = analysis.oscillators.get('RECOMMENDATION', 'NEUTRAL')
        ma = analysis.moving_averages.get('RECOMMENDATION', 'NEUTRAL')
        
        price = round(float(analysis.indicators.get('close', 0.0)), 5)
        high = round(float(analysis.indicators.get('high', 0.0)), 5)
        low = round(float(analysis.indicators.get('low', 0.0)), 5)
        
        if high > 0 and low > 0 and price > 0:
            pivot = round((high + low + price) / 3.0, 5)
            resistance = round((2.0 * pivot) - low, 5)
            support = round((2.0 * pivot) - high, 5)
        else:
            pivot = price
            resistance = price
            support = price
        
        direction = "NEUTRAL"
        signal_type = "WAIT / NO TRADE"
        
        if "BUY" in summary and ("BUY" in osc or "BUY" in ma):
            direction = "CALL (UP) ⬆️"
            signal_type = "STRONG BUY"
        elif "SELL" in summary and ("SELL" in osc or "SELL" in ma):
            direction = "PUT (DOWN) ⬇️"
            signal_type = "STRONG SELL"

        entry_time = (datetime.datetime.now() + datetime.timedelta(minutes=1)).strftime("%H:%M:%S")

        return {
            "status": "success",
            "symbol": symbol,
            "duration": duration,
            "direction": direction,
            "signal_type": signal_type,
            "price": price,
            "support": support,
            "resistance": resistance,
            "pivot": pivot,
            "entry_time": entry_time
        }
    except Exception as e:
        return {"status": "error", "message": f"Market Data Error: {str(e)}"}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json(force=True, silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    username = str(data.get('username', '')).strip()
    phone = str(data.get('phone', '')).strip()
    password = str(data.get('password', '')).strip()

    if not email or not password or not username:
        return jsonify({"status": "error", "message": "দয়া করে সমস্ত ক্ষেত্র সঠিকভাবে পূরণ করুন!"})

    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = sqlite3.connect('trading_users.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (email, username, phone, password, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (email, username, phone, password, created_at))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "অ্যাকাউন্ট সফলভাবে তৈরি করা হয়েছে! লগইন করুন।"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "এই ইমেইল অ্যাকাউন্টটি ইতিমধ্যে নিবন্ধিত!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database Error: {str(e)}"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', '')).strip()

    conn = sqlite3.connect('trading_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()

    if user and user[1] == password:
        return jsonify({"status": "success", "message": "লগইন সফল!", "username": user[0]})
    else:
        return jsonify({"status": "error", "message": "ভুল ইমেইল বা পাসওয়ার্ড!"})

# 👑 অ্যাডমিন প্যানেল এপিআই (এখানে আপনি সব ইউজারের পাসওয়ার্ড দেখতে পাবেন)
@app.route('/admin/users', methods=['GET'])
def get_all_users():
    secret_key = request.args.get('key', '')
    
    # অ্যাডমিন ভেরিফিকেশন
    if secret_key != ADMIN_SECRET_KEY:
        return jsonify({"status": "error", "message": "Access Denied! Invalid Admin Secret Key."}), 403

    conn = sqlite3.connect('trading_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, email, username, phone, password, created_at FROM users')
    rows = cursor.fetchall()
    conn.close()

    user_list = []
    for row in rows:
        user_list.append({
            "id": row[0],
            "email": row[1],
            "username": row[2],
            "phone": row[3],
            "password": row[4],
            "created_at": row[5]
        })

    return jsonify({"status": "success", "total_users": len(user_list), "users": user_list})

@app.route('/api/get_signal', methods=['POST'])
def get_signal():
    data = request.get_json(force=True, silent=True) or {}
    symbol = str(data.get('symbol', 'EURUSD')).upper().replace("FX_IDC:", "").replace("OANDA:", "")
    try:
        duration = int(data.get('duration', 5))
    except (ValueError, TypeError):
        duration = 5
    return jsonify(analyze_market_deep(symbol, duration))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
