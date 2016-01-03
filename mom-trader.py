#!/usr/bin/env python
# -*- coding: latin-1 -*-

# Requires python-requests. Install with pip:
#
#   pip install requests
#
# or, with easy-install:
#
#   easy_install requests

import json, hmac, hashlib, time, requests, base64, config, sys, smtplib
from datetime import datetime
from dateutil import tz
from requests.auth import AuthBase

requests.packages.urllib3.disable_warnings()

LAST_N_TRADES = 50
DOUBLE_DOWN_TOL = 2.0
SELL_PERC_TRADES = 0.8
BUY_PERC_TRADES = 0.5
TURNAROUND_TRADES = 10
TRADE_ATTEMPTS = 20
QTY = 0.01

lastTrade = {'side': 'sell', 'size': 0, 'price': 0}

from_zone = tz.gettz('UTC')
to_zone = tz.gettz('America/Los_Angeles')

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
    password = config.settings['gmailPwd']
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(username,password)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()

def getRecentTrades(N, auth):
    r = requests.get(api_url + 'products/BTC-USD/trades', auth=auth)
    maxTrades = min(N, len(r.json()))
    out = [{'side':r.json()[i]['side'],'price':r.json()[i]['price'],'time':r.json()[i]['time']} for i in range(0, maxTrades)]

    return out

def lastXHrsPerf(X, auth):
    r = requests.get(api_url + 'fills', auth=auth).json()
    fees = 0
    buyCost = 0
    sellCost = 0
    buyQty = 0
    sellQty = 0
    for i in range(0,len(r)):
        age = datetime.utcnow() - datetime.strptime(r[i]['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        ageHours = float(age.days*24 + age.seconds//3600)
        if (ageHours < X):
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

    print('Fees: ' + str(fees))
    print('Avg. buy price: ' + str(round(buyCost,2)))
    print('Avg. sell price: ' + str(round(sellCost,2)))

    print('Total trading profit: ' + str(round((sellCost*sellQty) - (buyCost*buyQty) - fees, 2)))

def buy(qty, limit, auth):
    order = {
        'size': qty,
        'price': limit,
        'side': 'buy',
        'product_id': 'BTC-USD',
    }
    r = requests.post(api_url + 'orders', json=order, auth=auth)
    return(r.json())


def sell(qty, limit, auth):
    order = {
        'size': qty,
        'price': limit,
        'side': 'sell',
        'product_id': 'BTC-USD',
    }
    r = requests.post(api_url + 'orders', json=order, auth=auth)
    return(r.json())

def sellLimit(qty, limit, auth):
    print('SELL ' + str(qty) + 'BTC @ $' + str(limit) + "\n")
    attempts = 0
    r = sell(qty, limit, auth)
    time.sleep(5)
    status = requests.get(api_url + 'orders/' + r['id'], auth=auth).json()

    while status['status'] != 'done' and attempts < TRADE_ATTEMPTS-1:
        attempts += 1
        requests.delete(api_url + 'orders/' + r['id'], auth=auth)
        time.sleep(1)
        book = getOrderBook(auth)
        r = sell(qty, max(limit, float(book['asks'][0][0])), auth)
        time.sleep(5)
        status = requests.get(api_url + 'orders/' + r['id'], auth=auth).json()

    if status['status'] == 'done':
        print(datetime.now())
        print('SOLD ' + str(status['size']) + 'BTC @ $' + str(status['price']) + "\n")
        sendEmail('SOLD ' + str(status['size']) + 'BTC @ $' + str(status['price']), '')
        return(True)
    else:
        print('SELL order not filled, cancelling')
        cancelAll(auth)
        return(False)

def buyLimit(qty, limit, auth):
    print('BUY ' + str(qty) + 'BTC @ $' + str(limit) + "\n")
    attempts = 0
    r = buy(qty, limit, auth)
    time.sleep(5)
    status = requests.get(api_url + 'orders/' + r['id'], auth=auth).json()
    while status['status'] != 'done' and attempts < TRADE_ATTEMPTS-1:
        attempts += 1
        requests.delete(api_url + 'orders/' + r['id'], auth=auth)
        time.sleep(1)
        book = getOrderBook(auth)
        r = buy(qty, min(limit, float(book['bids'][0][0])), auth)
        time.sleep(5)
        status = requests.get(api_url + 'orders/' + r['id'], auth=auth).json()

    if status['status'] == 'done':
        print(datetime.now())
        print('BOUGHT ' + str(status['size']) + 'BTC @ $' + str(status['price']) + "\n")
        sendEmail('BOUGHT ' + str(status['size']) + 'BTC @ $' + str(status['price']), '')
        return(True)
    else:
        print('BUY order not filled, cancelling')
        cancelAll(auth)
        return(False)

def cancelAll(auth):
    r = requests.delete(api_url + 'orders', auth=auth)
    print('Cancelled all orders')
    print(json.dumps(r.json(), indent=4, sort_keys=True))

def getMyOrders(auth):
    r = requests.get(api_url + 'orders', auth=auth)
    return r.json()

def decideSide(trades, book, usdBalance, btcBalance, lastTrade, auth):
    lastMarketTrade = trades[0]['side']
    tradeHist = []
    for i in range(0,LAST_N_TRADES):
        if trades[i]['side'] == 'sell':
            tradeHist.append(1)
        else:
            tradeHist.append(-1)

    if sum(tradeHist) > (LAST_N_TRADES*SELL_PERC_TRADES) and sum([tradeHist[i] for i in range(0,TURNAROUND_TRADES)]) < TURNAROUND_TRADES:
        # Price is rising fast
        nextTrade = 'sell'
    elif sum(tradeHist) < (-1*LAST_N_TRADES*BUY_PERC_TRADES) and sum([tradeHist[i] for i in range(0,TURNAROUND_TRADES)]) > -TURNAROUND_TRADES:
        # Price is dropping fast
        nextTrade = 'buy'
    else:
        nextTrade = 'None'

    # sys.stdout.write('\r' + str(sum(tradeHist)))
    # sys.stdout.flush()

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

    if (usdBalance < requiredUSD or btcBalance < requiredBTC):
        print('Insufficient balance')
        nextTrade = 'None'

    if (nextTrade == lastTrade['side']):
        # Don't do 2 buys/sells in a row...unless the price is way different
        if lastTrade['side'] == 'sell' and float(book['bids'][0][0]) < (lastTrade['price'] + DOUBLE_DOWN_TOL):
            nextTrade = 'None'
        elif lastTrade['side'] == 'buy' and float(book['bids'][0][0]) > (lastTrade['price'] - DOUBLE_DOWN_TOL):
            nextTrade = 'None'

    return nextTrade

def getOrderBook(auth):
    r = requests.get(api_url + 'products/BTC-USD/book', auth=auth)

    return r.json()

# Create custom authentication for Exchange
class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or '')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message, hashlib.sha256)
        signature_b64 = signature.digest().encode('base64').rstrip('\n')

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request

api_url = config.settings['apiURL']
auth = CoinbaseExchangeAuth(config.settings['apiKey'], config.settings['secret'], config.settings['passphrase'])

try:
    while True:
        # Get accounts
        r = requests.get(api_url + 'accounts', auth=auth).json()

        for account in r:
            if account['currency'] == 'USD':
                usdBalance = float(account['balance'])
            elif account['currency'] == 'BTC':
                btcBalance = float(account['balance'])

        trades = getRecentTrades(100, auth)
        book = getOrderBook(auth)
        tradeSide = decideSide(trades, book, usdBalance, btcBalance, lastTrade, auth)
        if tradeSide == 'buy':
            time.sleep(5)
            book = getOrderBook(auth)
            success = buyLimit(QTY, book['bids'][0][0], auth)
            if success:
                lastTrade = {'side': 'buy', 'size': QTY, 'price': float(book['asks'][0][0])}
                lastXHrsPerf(24, auth)
                print('USD/BTC balances: $' + str(round(usdBalance,2)) + ' / BTC ' + str(round(btcBalance,4)))
            else:
                print('Trade not filled, returning to top.')
        elif tradeSide == 'sell':
            time.sleep(5)
            book = getOrderBook(auth)
            success = sellLimit(QTY, book['asks'][0][0], auth)
            if success:
                lastTrade = {'side': 'sell', 'size': QTY, 'price': float(book['bids'][0][0])}
                lastXHrsPerf(24, auth)
                print('USD/BTC balances: $' + str(round(usdBalance,2)) + ' / BTC ' + str(round(btcBalance,4)))
            else:
                print('Trade not filled, returning to top.')

        time.sleep(2)
except:
    cancelAll(auth)
    sendEmail('Error occurred :(', '')
    raise
