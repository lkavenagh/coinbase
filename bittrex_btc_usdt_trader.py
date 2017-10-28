import os
os.chdir(r'c:\users\barby\documents\github\coinbase')
import config
from bittrex import Bittrex
import time
import pytz
import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt

sell_orders = []
buy_orders = []
out = pd.DataFrame(columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd'])

btc_max = 0.001
usd_max = 0.5

fee_pct = 0.0025

max_order_time = 120
rolling_stats = 100
num_open_orders = 5

market = 'USDT-BTC'

bx_client = Bittrex(config.bittrex_api['apiKey'], config.bittrex_api['secret'])

def myPrint(s):
    print(str(datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')) + ': ' + s)
    
def sellBTC(qty, limit=9999):
    myPrint('Selling ' + str(qty) + ' BTC at limit of $' + str(limit))
    s = bx_client.sell_limit('USDT-BTC', qty, limit)
    if s['success']:
        sell_orders.append(s['result'])
    else:
        myPrint(s['message'])
        
def buyBTC(qty, limit=1):
    myPrint('Buying ' + str(qty) + ' BTC at limit of $' + str(limit))
    b = bx_client.buy_limit('USDT-BTC', qty, limit)
    if b['success']:
        buy_orders.append(b['result'])
    else:
        myPrint(b['message'])

def cancelAllOrders():
    orders = bx_client.get_open_orders()
    for o in orders['result']:
        cancelOrder(o['OrderUuid'])

def cancelAllSellOrders():
    tmp_sells = sell_orders.copy()
    for o in tmp_sells:
        cancelOrder(o['uuid'])

def cancelAllBuyOrders():
    tmp_buys = buy_orders.copy()
    for o in tmp_buys:
        cancelOrder(o['uuid'])
            
def cancelOrder(uuid):
    o = getOrderStatus(uuid)
    if o != None:
        myPrint('Cancelling ' + o['result']['Type'] + ' order (' + o['result']['OrderUuid'] + ')')
        c = bx_client.cancel(uuid)
        if c['success'] | (c['message'] == 'ORDER_NOT_OPEN'):
            if o['result']['Type'] == 'LIMIT_SELL':
                if len(np.where([True if b['uuid'] == uuid else False for b in sell_orders])[0]) > 0:
                    sell_orders.remove(sell_orders[np.where([True if b['uuid'] == uuid else False for b in sell_orders])[0][0]])
            elif o['result']['Type'] == 'LIMIT_BUY':
                if len(np.where([True if b['uuid'] == uuid else False for b in buy_orders])[0]) > 0:
                    buy_orders.remove(buy_orders[np.where([True if b['uuid'] == uuid else False for b in buy_orders])[0][0]])
        else:
            myPrint(c['message'])

def getOrderStatus(uuid):
    o = bx_client.get_order(uuid)
    if o['success'] == True:
        return(o)
    else:
        return(None)
        
def getPrices(market):
    try:
        p = bx_client.get_ticker(market)
    except:
        time.sleep(5)    
        p = bx_client.get_ticker(market)
    if p['success']:
        return(p['result'])
    else:
        return(None)

def getBalances():
    b = bx_client.get_balances()
    s = dict()
    if b['success']:
        for i in b['result']:
            s[i['Currency']] = i['Balance']
    return s
            
def getTotalWorth():
    b = getBalances()
    btc = b['BTC']
    usd = b['USDT']
    p = getPrices(market)
    xr = p['Bid'] + ((p['Ask'] - p['Bid'])/2)
    return(usd + (btc*xr))

def removeStaleOrders(orders):
    for s in orders:
        o = getOrderStatus(s['uuid'])
        if o != None:
            n = datetime.datetime.now(datetime.timezone.utc)
            ot = pytz.utc.localize(datetime.datetime.strptime(o['result']['Opened'][:19], '%Y-%m-%dT%H:%M:%S'))
            td = n - ot
            if (n > ot) & (td.seconds > max_order_time):
                if o['result']['OrderUuid'] != None:
                    cancelOrder(o['result']['OrderUuid'])

def removeCompletedOrders(orders, out):
    for s in orders:
        o = getOrderStatus(s['uuid'])
        if o != None:
            if o['result']['Closed'] != None:
                if o['result']['Type'] == 'LIMIT_SELL':
                    sell_orders.remove(sell_orders[np.where([True if b['uuid'] == s['uuid'] else False for b in sell_orders])[0][0]])
                    out = out.append(pd.DataFrame([[
                            datetime.datetime.strptime(o['result']['Closed'][:19], '%Y-%m-%dT%H:%M:%S'),
                            'sell',
                            o['result']['Quantity'],
                            o['result']['PricePerUnit'],
                            getTotalWorth(),
                            getPrices(market)['Last'],
                            np.mean(out.lastPrice.tail(rolling_stats)),
                            np.std(out.lastPrice.tail(rolling_stats))
                            ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
                elif o['result']['Type'] == 'LIMIT_BUY':
                    buy_orders.remove(buy_orders[np.where([True if b['uuid'] == s['uuid'] else False for b in buy_orders])[0][0]])
                    out = out.append(pd.DataFrame([[
                            datetime.datetime.strptime(o['result']['Closed'][:19], '%Y-%m-%dT%H:%M:%S'),
                            'buy',
                            o['result']['Quantity'],
                            o['result']['PricePerUnit'],
                            getTotalWorth(),
                            getPrices(market)['Last'],
                            np.mean(out.lastPrice.tail(rolling_stats)),
                            np.std(out.lastPrice.tail(rolling_stats))
                            ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
        
                print(getTotalWorth())

    return(out)

def plotResults(out):
    toplot = out.reset_index(drop = True)
    fig = plt.figure()
    ax = fig.add_subplot(211)
    
    ax.plot(toplot.time, toplot.lastPrice)
    
    for i in np.arange(0,len(toplot)):
        if toplot.type[i] != None:
            if toplot.type[i] == 'sell':
                ax.plot(toplot.time[i], toplot.prc[i], color = 'red', marker = 'o')
            if toplot.type[i] == 'buy':
                ax.plot(toplot.time[i], toplot.prc[i], color = 'green', marker = 'o')
            if toplot.type[i] == 'sellattempt':
                ax.plot(toplot.time[i], toplot.prc[i], color = 'red', marker = 'o', markerfacecolor = 'none')
            if toplot.type[i] == 'buyattempt':
                ax.plot(toplot.time[i], toplot.prc[i], color = 'green', marker = 'o', markerfacecolor = 'none')
    
    ax.plot(toplot.time, toplot.mu, color = 'black', ls = '--', lw = 1)
    ax.plot(toplot.time, toplot.mu + toplot.sd, color = 'red', ls = '--', lw = 1)
    ax.plot(toplot.time, toplot.mu - toplot.sd, color = 'red', ls = '--', lw = 1)
    
    ax.xaxis.set_ticks([])
    
    ax.set_title('Bitcoin price, with buys (green) and sells (red)')
    
    ax = fig.add_subplot(212)
    ax.plot(toplot.time, toplot.netWorth)
    for l in ax.xaxis.get_majorticklabels():
        l.set_rotation(45)
    
    ax.set_title('Net worth (BTC + USD), in USD')
    
    ax.ticklabel_format(style='plain', useOffset=False, axis='y')
    
    fig.tight_layout()
    
    try:
        fig.savefig('price_chart.png')
    except:
        fig.savefig('_permerror_price_chart.png')
    
    plt.close(fig)

            
#%% Add mu and sd to the 'out' dataframe, so you can plot it point-in-time.
cancelAllOrders()

myPrint(str(getPrices(market)['Last']))
myPrint(str(getTotalWorth()))

priceHistory = []
netWorthHistory = []

#nextTrade = 'buy'
plt.ion()
plt.show()

out = out.append(pd.DataFrame([[
                bx_client.get_marketsummary('USDT-BTC')['result'][0]['TimeStamp'],
                np.nan,
                np.nan,
                np.nan,
                getTotalWorth(),
                getPrices(market)['Last'],
                np.mean(out.lastPrice.tail(rolling_stats)),
                np.std(out.lastPrice.tail(rolling_stats))
                ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
while 1:
    newtime = bx_client.get_marketsummary('USDT-BTC')['result'][0]['TimeStamp']
    b = getBalances()
    usdbal = b['USDT']
    btcbal = b['BTC']
    prices = getPrices(market)
    askprice = prices['Ask']
    bidprice = prices['Bid']
    lastprice = prices['Last']
    worth = getTotalWorth()
    
    feediff = fee_pct * lastprice
    buyprice = bidprice - feediff
    sellprice = askprice + feediff

    if (newtime > str(out.time.tail(1).iloc[0])):
        out = out.append(pd.DataFrame([[
                newtime,
                np.nan,
                np.nan,
                np.nan,
                worth,
                lastprice,
                np.mean(out.lastPrice.tail(rolling_stats)),
                np.std(out.lastPrice.tail(rolling_stats))
                ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
    
#    if (nextTrade == 'buy') & (usdbal < (askprice * btc_max)):
#        nextTrade = 'sell'
#        myPrint('Not enough USD to buy, switching to sell')
#    if (nextTrade == 'sell') & (btcbal < btc_max):
#        nextTrade = 'buy'
#        myPrint('Not enough BTC to sell, switching to buy')
    
    if len(out) > 10:
        mu = np.mean(out.lastPrice.tail(rolling_stats))
        sd = np.std(out.lastPrice.tail(rolling_stats))
        if (out.lastPrice.tail(1).iloc[0] < (mu - (1*sd))) & (out.lastPrice.tail(1).iloc[0] < out.lastPrice.tail(2).iloc[0]):
            if (len(buy_orders + sell_orders) < num_open_orders) & (usdbal > (buyprice * btc_max)):
                buyBTC(btc_max, buyprice)
                out = out.append(pd.DataFrame([[
                        datetime.datetime.strptime(newtime[:19], '%Y-%m-%dT%H:%M:%S'),
                        'buyattempt',
                        btc_max,
                        buyprice,
                        worth,
                        lastprice,
                        mu,
                        sd
                        ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
#                nextTrade = 'sell'
        elif (out.lastPrice.tail(1).iloc[0] > (mu + (1*sd))) & (out.lastPrice.tail(1).iloc[0] > out.lastPrice.tail(2).iloc[0]):
            if (len(buy_orders + sell_orders) < num_open_orders) & (btcbal > btc_max) & (len(sell_orders) == 0):
                sellBTC(btc_max, sellprice)
                out = out.append(pd.DataFrame([[
                        datetime.datetime.strptime(newtime[:19], '%Y-%m-%dT%H:%M:%S'),
                        'sellattempt',
                        btc_max,
                        sellprice,
                        worth,
                        lastprice,
                        mu,
                        sd
                        ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
#                nextTrade == 'buy'
    
    removeStaleOrders(sell_orders + buy_orders)
    out = removeCompletedOrders(sell_orders + buy_orders, out)
    
    out = out.reset_index(drop = True)
    out.time = [datetime.datetime.strptime(d[:19], '%Y-%m-%dT%H:%M:%S') if type(d) == str else d for d in out.time]
    
    plotResults(out.tail(1000))
    
    time.sleep(5)
    