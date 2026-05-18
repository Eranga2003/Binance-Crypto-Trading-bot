def calculate_position(account_balance, entry_price, stop_loss_price):
    """
    Calculates position size based on user rules:
    - 5% allocation of total account balance
    - 3% risk on that allocation
    - 5x Leverage
    - 3% Take Profit
    - Minimum order value: $5 USD (Bybit requirement)
    """
    # Bybit minimum order value (in USD)
    BYBIT_MIN_ORDER_VALUE = 5.0
    
    allocation = account_balance * 0.05
    leverage = 5
    
    # 3% risk of the allocated amount
    max_loss_usd = allocation * 0.03
    
    # Calculate difference percentage between entry and stop loss
    price_diff_percent = abs(entry_price - stop_loss_price) / entry_price
    
    if price_diff_percent == 0:
        return None
        
    position_size_usd = max_loss_usd / price_diff_percent
    
    # Cap position size by our leveraged allocation (5% of account * 5x leverage)
    max_leveraged_position = allocation * leverage
    
    final_position_usd = min(position_size_usd, max_leveraged_position)
    
    # ENFORCE MINIMUM ORDER VALUE
    if final_position_usd < BYBIT_MIN_ORDER_VALUE:
        # Scale up to meet minimum, but cap at available balance
        if account_balance >= BYBIT_MIN_ORDER_VALUE:
            final_position_usd = min(BYBIT_MIN_ORDER_VALUE, account_balance * 0.5)  # Max 50% of balance
        else:
            print(f"[Position Sizing] ERROR: Account balance ({account_balance:.2f} USDT) is below Bybit minimum ({BYBIT_MIN_ORDER_VALUE} USDT)")
            return None
    
    position_size_crypto = final_position_usd / entry_price
    
    # Calculate TP (3% from entry)
    if entry_price > stop_loss_price: 
        # LONG Position
        take_profit_price = entry_price * (1 + 0.03)
    else: 
        # SHORT Position
        take_profit_price = entry_price * (1 - 0.03)
    
    print(f"[Position Sizing] Balance: {account_balance:.2f} USDT | Position: {final_position_usd:.2f} USDT | Crypto: {position_size_crypto:.8f}")
        
    return {
        'allocated_usd': allocation,
        'max_loss_usd': max_loss_usd,
        'position_size_usd': final_position_usd,
        'position_size_crypto': position_size_crypto,
        'take_profit_price': take_profit_price,
        'stop_loss_price': stop_loss_price,
        'leverage': leverage
    }
