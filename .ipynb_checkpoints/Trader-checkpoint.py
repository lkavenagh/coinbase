#!/usr/bin/env python
# -*- coding: latin-1 -*-

# Requires python-requests. Install with pip:
#
#   pip install requests
#
# or, with easy-install:
#
#   easy_install requests

import os, sys
sys.path.append(os.path.join(os.environ['HOMEDRIVE'], os.environ['HOMEPATH'], 'documents\github\coinbase'))
import pandas as pd
from datetime import datetime
from dateutil import tz
import hashlib
import hmac
import requests
import time

from requests.auth import AuthBase

requests.packages.urllib3.disable_warnings()

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
        
        self.api_url = readConfig('coinbaseapiurl')
        self.auth = HMACAuth(readConfig('coinbaseapikey'), readConfig('coinbasesecret'), readConfig('coinbasepassphrase'))
        self.usdBalance, self.btcBalance = self.printBalances(True)
        
    def sendApiGet(self, call_url):
        return(requests.get(self.api_url + call_url, auth = self.auth))
    
    def sendApiPost(self, call_url, payload):
        return(requests.post(self.api_url + call_url, json=payload, auth = self.auth))
        
    def sendApiDelete(self, call_url):
        return(requests.delete(self.api_url + call_url, auth = self.auth))
        
    def getRecentTrades(self, N, auth):
        r = sendApiGet('products/BTC-USD/trades')
        while not hasattr(r, 'json'):
            time.sleep(1)
            r = sendApiGet('products/BTC-USD/trades')

        maxTrades = min(N, len(r.json()))
        out = [{'side':r.json()[i]['side'],'price':r.json()[i]['price'],'time':r.json()[i]['time']} for i in range(0, maxTrades)]

        return out

    def lastXHrsPerf(self, X, auth):
        r = makeApiGet('fills').json()
        fees = 0
        buyCost = 0
        sellCost = 0
        buyQty = 0
        sellQty = 0
        for i in range(0,len(r)):
            if (datetime.strptime(r[i]['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ') >= START_TIME):
                fees += float(r[i]['fee'])
                if r[i]['side'] == 'buy':
                    buyCost += float(r[i]['price']) * float(r[i]['size'])
                    buyQty += float(r[i]['size'])
                else:
                    sellCost += float(r[i]['price']) * float(r[i]['size'])
                    sellQty += float(r[i]['size'])

        if buyQty != 0:
            buyCost = buyCost / buyQty

        if sellQty != 0:
            sellCost = sellCost / sellQty

        book = getOrderBook()
        mm_price = (float(book['asks'][0][0]) + float(book['bids'][0][0])) / 2

        self.usdBalance, self.btcBalance = printBalances(False)

        message = ('Fees: ' + str(fees) +
            '\nAvg. buy price: ' + str(round(buyCost,2)) +
            '\nAvg. sell price: ' + str(round(sellCost,2)) +
            '\n\nTotal trading profit: ' + str(round((sellCost*sellQty) - (buyCost*buyQty) - fees, 2)) +
            '\n\nCurrent account value: $' + str(mm_price * self.btcBalance + self.usdBalance) + '\n'
            )

        return(message)

    def buy(self, qty, limit):
        order = {
            'size': qty,
            'price': limit,
            'side': 'buy',
            'product_id': 'BTC-USD',
        }
        print('Buying ' + str(qty) + ' @ $' + str(limit) + ' limit.')
        r = sendApiPost('orders', order)
        return(r.json())

    def sell(self, qty, limit):
        order = {
            'size': qty,
            'price': limit,
            'side': 'sell',
            'product_id': 'BTC-USD',
        }
        print('Selling ' + str(qty) + ' @ $' + str(limit) + ' limit.')
        r = sendApiPost('orders', order)
        return(r.json())

    def sellLimit(self, qty, limit):
        print(datetime.now())
        print('SELL ' + str(qty) + 'BTC @ $' + str(limit))
        attempts = 0
        r = sell(qty, limit, auth)
        time.sleep(5)
        status = sendApiGet('orders/' + r['id']).json()
        while not status.has_key('status'):
            print(status)
            time.sleep(1)
            status = sendApiGet('orders/' + r['id']).json()

        while status['status'] != 'done' and attempts < TRADE_ATTEMPTS-1:
            attempts += 1
            sendApiDelete('orders/' + r['id'])
            time.sleep(1)
            book = getOrderBook()
            r = sell(qty, max(limit, float(book['asks'][0][0])))
            time.sleep(5)
            status = sendApiGet('orders/' + r['id']).json()

        if status['status'] == 'done':
            print(datetime.now())
            print('SOLD ' + str(status['size']) + 'BTC @ $' + str(status['price']) + "\n")
            m = lastXHrsPerf(24, self.auth)
            print(m)
            sendEmail('BTC_BOT SOLD ' + str(status['size']) + 'BTC @ $' + str(status['price']), m)
            return(True, status['price'])
        else:
            print('SELL order not filled, cancelling')
            cancelAll()
            return(False, -1)

    def buyLimit(self, qty, limit):
        print(datetime.now())
        print('BUY ' + str(qty) + 'BTC @ $' + str(limit))
        attempts = 0
        r = buy(qty, limit, self.auth)
        time.sleep(5)
        status = sendApiGet('orders/' + r['id']).json()
        while not status.has_key('status'):
            print('Status not found...')
            time.sleep(1)
            status = sendApiGet('orders/' + r['id']).json()

        while status['status'] != 'done' and attempts < TRADE_ATTEMPTS-1:
            attempts += 1
            sendApiDelete('orders/' + r['id'])
            time.sleep(1)
            book = getOrderBook()
            r = buy(qty, min(limit, float(book['bids'][0][0])), self.auth)
            time.sleep(5)
            status = sendApiGet('orders/' + r['id']).json()

        if status['status'] == 'done':
            print(datetime.now())
            print('BOUGHT ' + str(status['size']) + 'BTC @ $' + str(status['price']) + "\n")
            m = lastXHrsPerf(24, auth)
            print(m)
            sendEmail('BTC_BOT BOUGHT ' + str(status['size']) + 'BTC @ $' + str(status['price']), m)
            return(True,status['price'])
        else:
            print('BUY order not filled, cancelling')
            cancelAll()
            return(False, -1)

    def cancelAll(self):
        sendApiDelete('orders')
        print('Cancelled all orders')
        print(json.dumps(r.json(), indent=4, sort_keys=True))

    def getMyOrders(self):
        r = sendApiGet('orders')
        return r.json()

    def decideSide(self, trades, book, lastTrade):
        lastMarketTrade = trades[0]['side']
        tradeHist = []
        for i in range(0,LAST_N_TRADES):
            if trades[i]['side'] == 'sell':
                tradeHist.append(1)
            else:
                tradeHist.append(-1)

        if lastTrade['side'] == 'buy':
            if trades[0]['price'] > lastTrade['price'] or trades[0]['price'] < lastTrade['price'] - DOUBLE_DOWN_TOL:
                oppodiboppo = True
            else:
                oppodiboppo = False
        else:
            oppodiboppo = True

        if sum(tradeHist) > (LAST_N_TRADES*SELL_PERC_TRADES) and oppodiboppo and sum([tradeHist[i] for i in range(0,TURNAROUND_TRADES)]) < TURNAROUND_TRADES:
            # Price is rising fast
            nextTrade = 'sell'
        elif sum(tradeHist) < (-1*LAST_N_TRADES*BUY_PERC_TRADES) and oppodiboppo and sum([tradeHist[i] for i in range(0,TURNAROUND_TRADES)]) > -TURNAROUND_TRADES:
            # Price is dropping fast
            nextTrade = 'buy'
        else:
            nextTrade = 'None'

        if nextTrade == 'None':
            return nextTrade
        else:
            myOrders = getMyOrders(auth)
            if len(myOrders) > 0:
                print('Order still outstanding')
                nextTrade = 'None'

        if nextTrade == 'buy':
            requiredUSD = QTY * float(book['asks'][0][0])
            requiredBTC = 0
        elif nextTrade == 'sell':
            requiredUSD = 0
            requiredBTC = QTY
        else:
            requiredUSD = 0
            requiredBTC = 0

        if (self.usdBalance < requiredUSD or self.btcBalance < requiredBTC):
            print('Insufficient balance for ' + nextTrade + '. Need USD/BTC ' + str(requiredUSD) + ' / ' + str(requiredBTC))
            nextTrade = 'None'

        if (nextTrade == lastTrade['side']):
            # Don't do 2 buys/sells in a row...unless the price is way different
            if lastTrade['side'] == 'sell' and float(book['asks'][0][0]) < (lastTrade['price'] + DOUBLE_DOWN_TOL):
                nextTrade = 'None'
            elif lastTrade['side'] == 'buy' and float(book['bids'][0][0]) > (lastTrade['price'] - DOUBLE_DOWN_TOL):
                nextTrade = 'None'

        return nextTrade

    def getOrderBook(self):
        r = sendApiGet('products/BTC-USD/book')
        while not hasattr(r, 'json'):
            time.sleep(1)
            r = sendApiGet('products/BTC-USD/book')

        return r.json()

    def printBalances(self, output):
        r = sendApiGet(self.api_url + 'accounts').json()
        for account in r:
            if account['currency'] == 'USD':
                self.usdBalance = float(account['balance'])
            elif account['currency'] == 'BTC':
                self.btcBalance = float(account['balance'])

        if (output):
            print('USD/BTC balances: $' + str(round(self.usdBalance,2)) + ' / BTC ' + str(round(self.btcBalance,4)))

# Create custom authentication for Exchange
class HMACAuth(AuthBase):
    def __init__(self, api_key, api_secret, api_version):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_version = api_version

    def __call__(self, request):
        timestamp = str(int(time.time()))
        message = timestamp + request.method + request.path_url + (request.body or '')
        secret = self.api_secret

        if not isinstance(message, bytes):
            message = message.encode()
        if not isinstance(secret, bytes):
            secret = secret.encode()

        signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
        request.headers.update({
            requests.utils.to_native_string('CB-VERSION'): self.api_version,
            requests.utils.to_native_string('CB-ACCESS-KEY'): self.api_key,
            requests.utils.to_native_string('CB-ACCESS-SIGN'): signature,
            requests.utils.to_native_string('CB-ACCESS-TIMESTAMP'): timestamp,
        })
        return request


