def calculate_position(account_balance, entry_price, stop_loss_price):
    """
    Calculates position size based on user rules:
    - 5% allocation of total account balance
    - 3% risk on that allocation
    - 5x Leverage
    - 3% Take Profit
    """
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
    position_size_crypto = final_position_usd / entry_price
    
    # Calculate TP (3% from entry)
    if entry_price > stop_loss_price: 
        # LONG Position
        take_profit_price = entry_price * (1 + 0.03)
    else: 
        # SHORT Position
        take_profit_price = entry_price * (1 - 0.03)
        
    return {
        'allocated_usd': allocation,
        'max_loss_usd': max_loss_usd,
        'position_size_usd': final_position_usd,
        'position_size_crypto': position_size_crypto,
        'take_profit_price': take_profit_price,
        'stop_loss_price': stop_loss_price,
        'leverage': leverage
    }
