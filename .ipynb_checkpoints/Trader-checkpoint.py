import os, sys
import pandas as pd
from datetime import datetime
from dateutil import tz

from coinbase.wallet.client import Client

def readConfig(key):
    config = pd.read_csv(os.path.join('/', 'home', 'lkavenagh', 'config.txt'), header = None)
    config = [c.split('=') for c in config[0]]
    out = [c[1] for c in config if c[0] == key][0]
    return(out)
        
class Trader:
    def __init__(self):
        self.LAST_N_TRADES = 50
        self.DOUBLE_DOWN_TOL = 3.0
        self.SELL_PERC_TRADES = 0.7
        self.BUY_PERC_TRADES = 0.6
        self.TURNAROUND_TRADES = 10
        self.TRADE_ATTEMPTS = 20
        self.QTY = 0.01

        self.START_TIME = datetime.utcnow()

        self.lastTrade = {'side': 'sell', 'size': 0.01, 'price': 447.14}

        self.from_zone = tz.gettz('UTC')
        self.to_zone = tz.gettz('America/New_York')
        
        self.client = Client(readConfig('coinbaseapikey'), readConfig('coinbasesecret'))
        
        self.balances = dict()
        self.account_ids = dict()
        
        self.getBalances()
        
        self.setAccountIds()
        
    def getRecentTrades(self, currency, N):
        account_id = self.account_ids[currency]
        txs = self.client.get_transactions(account_id)['data']

        maxTrades = min(N, len(txs))
        out = [{'type':txs[i]['type'],
                'time':txs[i]['created_at'],
                'amount':txs[i]['amount']['amount'],
                'currency':txs[i]['amount']['currency'],
                'native_amount':txs[i]['native_amount']['amount'],
                'native_currency':txs[i]['native_amount']['currency']
               } for i in range(0, maxTrades)]

        return out

    def buy(self, currency, qty):
        buy = self.client.buy(account_id = self.account_ids[currency], 
                              amount = qty, 
                              currency = currency, 
                              payment_method = self.getUSDWalletID(),
                              commit = False)
        print('Buying {:.2f} of {}: ${:.2f} + ${:.2f} = USD${:.4f}'.format(float(buy.amount.amount), buy.amount.currency, float(buy.subtotal.amount), float(buy.fee.amount), float(buy.total.amount)))
        return(buy)
    
    def commit_buy(self, buy_order):
        self.client.commit_buy(self.account_ids[buy_order.amount['currency']], buy_order.id)

    def sell(self, currency, qty):
        sell = self.client.sell(account_id = self.account_ids[currency], 
                                amount = qty, 
                                currency = currency, 
                                payment_method = self.getUSDWalletID(),
                                commit = False)
        print('Selling {:.2f} of {}: ${:.2f} - ${:.2f} = USD${:.4f}'.format(float(sell.amount.amount), sell.amount.currency, float(sell.subtotal.amount), float(sell.fee.amount), float(sell.total.amount)))
        return(sell)
    
    def commit_sell(self, sell_order):
        self.client.commit_sell(self.account_ids[sell_order.amount['currency']], sell_order.id)

    def getBuyQuote(self, currency, qty = 1):
        try:
            buy = self.client.buy(account_id = self.account_ids[currency], 
                              amount = qty, 
                              currency = currency, 
                              payment_method = self.getUSDWalletID(),
                              quote = True)
        except:
            print('Timed out')
            return(None)
        
        return(float(buy['total']['amount']), float(buy['fee']['amount']))
    
    def getSellQuote(self, currency, qty = 1):
        try:
            sell = self.client.sell(account_id = self.account_ids[currency], 
                              amount = qty, 
                              currency = currency, 
                              payment_method = self.getUSDWalletID(),
                              quote = True)
        except:
            print('Timed out')
            return(None)
        
        return(float(sell['total']['amount']), float(sell['fee']['amount']))
    
    def cancelAll(self):
        txs = self.client.get_transactions(self.account_ids['USD'])['data']
        
        for tx in txs:
            if tx['status'] == 'pending':
                tx = self.client.cancel_request(tx[tx['type']]['id'], tx['id'])
                print('Cancelled transaction {}'.format(tx['id']))
            else:
                print('Transaction {} not cancelled'.format(tx['id']))
                
    def getBalances(self):
        accounts = self.client.get_accounts()['data']
        for account in accounts:
            self.balances[account['balance']['currency']] = float(account['balance']['amount'])
            
    def printBalances(self):
        self.getBalances()
        currs = sorted(self.balances.keys())
        currs.remove('USD')
        for currency in ['USD'] + currs:
            if (self.balances[currency] > 0) | (currency == 'USD'):
                print('{}: {:.4f}'.format(currency, self.balances[currency]))
            
    def setAccountIds(self):
        accounts = self.client.get_accounts()['data']
        for account in accounts:
            self.account_ids[account['balance']['currency']] = account['id']
            
    def getPaymentMethods(self):
        pms = self.client.get_payment_methods()['data']
        return(pms)
        
    def getUSDWalletID(self):
        pms = self.client.get_payment_methods()['data']
        for pm in pms:
            if pm['type'] == 'fiat_account':
                return(pm['id'])
            
    def getUSDBankID(self):
        pms = self.client.get_payment_methods()['data']
        for pm in pms:
            if pm['type'] == 'ach_bank_account':
                return(pm['id'])
