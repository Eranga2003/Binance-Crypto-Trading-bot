from flask import Flask, jsonify, request
from flask_cors import CORS
from data_engine.data_fetcher import DataFetcher
from technical_analysis.support_resistance import find_zones, validate_zones
import traceback
import pandas as pd

app = Flask(__name__)
CORS(app)

fetcher = DataFetcher()

@app.route('/api/data')
def get_data():
    symbol = request.args.get('symbol', 'BTC/USDT')
    timeframe = request.args.get('timeframe', '4h')
    
    try:
        limit = 300
        if timeframe in ['1d', '4h']:
            limit = 100
        elif timeframe in ['15m', '1m']:
            limit = 500
            
        df = fetcher.fetch_ohlcv(symbol, timeframe, limit=limit)
        if df is None or df.empty:
            return jsonify({'error': 'Failed to fetch data'}), 500
            
        df = df.dropna(subset=['timestamp', 'open', 'high', 'low', 'close'])
        df = df.drop_duplicates(subset=['timestamp'])
        df = df.sort_values('timestamp')
        # Lightweight charts expects: {time: unix_timestamp, open: O, high: H, low: L, close: C}
        df['time'] = df['timestamp'].apply(lambda x: int(x.timestamp()) if pd.notnull(x) else 0)
        df = df.drop_duplicates(subset=['time'], keep='last')
        df = df.sort_values('time')
        candles = []
        for _, row in df.iterrows():
            candles.append({
                'time': int(row['time']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close'])
            })
        return jsonify({'candles': candles})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/levels')
def get_levels():
    symbol = request.args.get('symbol', 'BTC/USDT')
    timeframe = request.args.get('timeframe', '4h')
    
    try:
        if timeframe == '4h':
            df_1d = fetcher.fetch_ohlcv(symbol, '1d', limit=100)
            df_4h = fetcher.fetch_ohlcv(symbol, '4h', limit=100)
            if df_1d is None or df_4h is None:
                return jsonify({'error': 'Failed to fetch data'}), 500
            zones_1d = find_zones(df_1d, num_support=10, num_resistance=10, window=5, tolerance=0.01)
            sup = validate_zones(df_4h, zones_1d['support'], top_n=5, tolerance=0.005)
            res = validate_zones(df_4h, zones_1d['resistance'], top_n=5, tolerance=0.005)
        elif timeframe == '1h':
            df = fetcher.fetch_ohlcv(symbol, '1h', limit=300)
            if df is None: return jsonify({'error': 'Failed to fetch data'}), 500
            zones = find_zones(df, num_support=4, num_resistance=4, window=5, tolerance=0.005)
            sup, res = zones['support'], zones['resistance']
        elif timeframe == '15m':
            df = fetcher.fetch_ohlcv(symbol, '15m', limit=500)
            if df is None: return jsonify({'error': 'Failed to fetch data'}), 500
            zones = find_zones(df, num_support=4, num_resistance=4, window=8, tolerance=0.003)
            sup, res = zones['support'], zones['resistance']
        elif timeframe == '1m':
            df = fetcher.fetch_ohlcv(symbol, '1m', limit=500)
            if df is None: return jsonify({'error': 'Failed to fetch data'}), 500
            zones = find_zones(df, num_support=2, num_resistance=2, window=10, tolerance=0.001)
            sup, res = zones['support'], zones['resistance']
        else:
            return jsonify({'error': 'Unsupported timeframe'}), 400
            
        return jsonify({'support': sup, 'resistance': res})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Web Server for UI...")
    app.run(port=5000, debug=True)
