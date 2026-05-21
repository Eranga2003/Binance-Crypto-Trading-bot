import urllib.request
import urllib.error
try:
    urllib.request.urlopen('http://localhost:5000/api/data?symbol=BTC/USDT&timeframe=4h').read()
except urllib.error.HTTPError as e:
    print("HTTP error code:", e.code)
    print("Response body:", e.read().decode())
