import os, sys
sys.path.append(os.path.join(os.environ['HOMEDRIVE'], os.environ['HOMEPATH'], 'documents\github\coinbase'))
import pandas as pd
from datetime import datetime
from dateutil import tz

from coinbase.wallet.client import Client

def readConfig(key):
    config = pd.read_csv(os.path.join(os.environ['HOMEDRIVE'], os.environ['HOMEPATH'], 'documents\config.txt'), header = None)
    config = [c.split('=') for c in config[0]]
    out = [c[1] for c in config if c[0] == key][0]
    return(out)

def sendEmail(subject, body):
    msg = "\r\n".join([
      "From: lkavenagh@gmail.com",
      "To: lkavenagh@gmail.com",
      "Subject: " + subject,
      "",
      body
      ])
    fromaddr = 'lkavenagh@gmail.com'
    toaddrs = 'lkavenagh@gmail.com'
    username = 'lkavenagh@gmail.com'
    password = readConfig('gmailpw')
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(username,password)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()
        
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
        print('Buying {} of {} from account_id {}'.format(qty, currency, self.getUSDWalletID()))
        buy = self.client.buy(account_id = self.account_ids[currency], 
                              amount = qty, 
                              currency = currency, 
                              payment_method = self.getUSDWalletID())
        return(buy)

    def sell(self, currency, qty):
        print('Selling {} of {}'.format(qty, currency))
        sell = self.client.sell(account_id = self.account_ids[currency], 
                                amount = qty, 
                                currency = currency, 
                                payment_method = self.getUSDWalletID())
        return(sell)

    def getBuyQuote(self, currency, qty = 1):
        buy = self.client.buy(account_id = self.account_ids[currency], 
                              amount = qty, 
                              currency = currency, 
                              payment_method = self.getUSDWalletID(),
                              quote = True)
        
        return(buy['total']['amount'])
    
    def getSellQuote(self, currency, qty = 1):
        sell = self.client.sell(account_id = self.account_ids[currency], 
                              amount = qty, 
                              currency = currency, 
                              payment_method = self.getUSDWalletID(),
                              quote = True)
        
        return(sell['total']['amount'])
    
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
        for currency in self.balances.keys():
            print('{}: {:.4f}'.format(currency, self.balances[currency]))
            
    def setAccountIds(self):
        accounts = self.client.get_accounts()['data']
        for account in accounts:
            self.account_ids[account['balance']['currency']] = account['id']
            
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
