import os
os.chdir(r'c:\users\barby\documents\github\coinbase')
import config
from coinbase.wallet.client import Client
from bittrex import Bittrex

#%% Coinbase
cb_client = Client(config.coinbase_api['apiKey'], config.coinbase_api['secret'])
cb_client.get_buy_price()


#%% Bittrex
bx_client = Bittrex(config.bittrex_api['apiKey'], config.bittrex_api['secret'])
bx_client.get_ticker('BTC-LTC')
