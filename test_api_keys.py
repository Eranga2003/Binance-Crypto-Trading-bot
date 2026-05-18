#!/usr/bin/env python3
"""
Diagnostic script to verify API keys are loaded correctly
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

EXCHANGE = os.getenv("EXCHANGE", "bybit").strip().lower()
api_key = (
    os.getenv("API_KEY", "") or
    os.getenv("BYBIT_API_KEY", "") or
    os.getenv("BINANCE_API_KEY", "")
).strip()
api_secret = (
    os.getenv("API_SECRET", "") or
    os.getenv("BYBIT_API_SECRET", "") or
    os.getenv("BINANCE_API_SECRET", "")
).strip()

print("=" * 60)
print("API KEY DIAGNOSTIC")
print("=" * 60)
print(f"Exchange configured: {EXCHANGE}")

print(f"\n✓ API Key loaded: {len(api_key) > 0}")
if api_key:
    print(f"  Length: {len(api_key)} characters")
    print(f"  First 10: {api_key[:10]}")
    print(f"  Last 10: {api_key[-10:]}")
    
    # Check for common issues
    if api_key.startswith('"') or api_key.startswith("'"):
        print("  ❌ ERROR: Key has quotes around it!")
    if api_key.startswith(' ') or api_key.endswith(' '):
        print("  ❌ ERROR: Key has extra whitespace!")
    else:
        print("  ✓ No quotes or whitespace detected")

print(f"\n✓ API Secret loaded: {len(api_secret) > 0}")
if api_secret:
    print(f"  Length: {len(api_secret)} characters")
    print(f"  First 10: {api_secret[:10]}")
    print(f"  Last 10: {api_secret[-10:]}")
    
    # Check for common issues
    if api_secret.startswith('"') or api_secret.startswith("'"):
        print("  ❌ ERROR: Secret has quotes around it!")
    if api_secret.startswith(' ') or api_secret.endswith(' '):
        print("  ❌ ERROR: Secret has extra whitespace!")
    else:
        print("  ✓ No quotes or whitespace detected")

print("\n" + "=" * 60)
print("NEXT STEPS FOR BYBIT SETUP:")
print("=" * 60)
print("""
1. Go to: https://www.bybit.com/
   (Login and open API Management / Demo Trading)

2. Ensure you are using Bybit Demo Trading or the correct Bybit API account

3. Create NEW API Key with these settings:
   - Type: System Generated (recommended)
   - Enable: ✓ Read ✓ Trade
   - If testing on sandbox, make sure TESTNET=True in .env

4. Copy the keys WITHOUT quotes and paste them in .env file as:
   EXCHANGE=bybit
   API_KEY=your_key_here
   API_SECRET=your_secret_here

5. Do NOT use keys restricted to whitelisted IPs if testing locally
""")
print("=" * 60)
