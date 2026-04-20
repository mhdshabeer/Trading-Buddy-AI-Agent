# scripts/04_mt5_direct.py
import MetaTrader5 as mt5

# Initialize connection to MT5
if not mt5.initialize():
    print("MT5 initialization failed. Make sure MT5 desktop is running.")
    print("Error code:", mt5.last_error())
else:
    # Get account info
    account = mt5.account_info()
    if account:
        print(f"Connected successfully!")
        print(f"Account balance: {account.balance} {account.currency}")
    else:
        print("Failed to fetch account info")
    
    # Shutdown the connection
    mt5.shutdown()