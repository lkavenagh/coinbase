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

max_order_time = 60
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
    return(bx_client.get_order(uuid))
    
def getPrice(market, t = 'Last'):
    p = bx_client.get_ticker(market)
    if p['success']:
        return(p['result'][t])
    else:
        return(None)
        
def getAskPrice(market):
    p = bx_client.get_ticker(market)
    if p['success']:
        return(p['result']['Ask'])
    else:
        return(None)

def getBalance(curr):
    b = bx_client.get_balances()
    if b['success']:
        for i in b['result']:
            if i['Currency'] == curr:
                return i['Balance']
            
def getTotalWorth():
    btc = getBalance('BTC')
    usd = getBalance('USDT')
    xr = getPrice(market, 'Last')
    return(usd + (btc*xr))

def removeStaleOrders(orders):
    for s in orders:
        o = getOrderStatus(s['uuid'])
        td = datetime.datetime.now(datetime.timezone.utc) - pytz.utc.localize(datetime.datetime.strptime(o['result']['Opened'][:19], '%Y-%m-%dT%H:%M:%S'))
        if td.seconds > max_order_time:
            cancelOrder(o['result']['OrderUuid'])

def removeCompletedOrders(orders, out):
    for s in orders:
        o = getOrderStatus(s['uuid'])
        if o['result']['Closed'] != None:
            if o['result']['Type'] == 'LIMIT_SELL':
                sell_orders.remove(sell_orders[np.where([True if b['uuid'] == s['uuid'] else False for b in sell_orders])[0][0]])
                out = out.append(pd.DataFrame([[
                        datetime.datetime.strptime(o['result']['Closed'][:19], '%Y-%m-%dT%H:%M:%S'),
                        'sell',
                        o['result']['Quantity'],
                        o['result']['PricePerUnit'],
                        getTotalWorth(),
                        getPrice(market, 'Last'),
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
                        getPrice(market, 'Last'),
                        np.mean(out.lastPrice.tail(rolling_stats)),
                        np.std(out.lastPrice.tail(rolling_stats))
                        ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
    
            print(getTotalWorth())

    return(out)

def plotResults(out):
    fig = plt.figure()
    ax = fig.add_subplot(211)
    
    ax.plot(out.time, out.lastPrice)
    
    for i in np.arange(0,len(out)):
        if out.type[i] != None:
            if out.type[i] == 'sell':
                ax.plot(out.time[i], out.prc[i], color = 'red', marker = 'o')
            if out.type[i] == 'buy':
                ax.plot(out.time[i], out.prc[i], color = 'green', marker = 'o')
            if out.type[i] == 'sellattempt':
                ax.plot(out.time[i], out.prc[i], color = 'red', marker = 'o', markerfacecolor = 'none')
            if out.type[i] == 'buyattempt':
                ax.plot(out.time[i], out.prc[i], color = 'green', marker = 'o', markerfacecolor = 'none')
    
    ax.plot(out.time, out.mu, color = 'black', ls = '--', lw = 1)
    ax.plot(out.time, out.mu + out.sd, color = 'red', ls = '--', lw = 1)
    ax.plot(out.time, out.mu - out.sd, color = 'red', ls = '--', lw = 1)
    
    ax.xaxis.set_ticks([])
    
    ax.set_title('Bitcoin price, with buys (green) and sells (red)')
    
    ax = fig.add_subplot(212)
    ax.plot(out.time, out.netWorth)
    for l in ax.xaxis.get_majorticklabels():
        l.set_rotation(45)
    
    ax.set_title('Net worth (BTC + USD), in USD')
    
    fig.tight_layout()
    
    try:
        fig.savefig('price_chart.png')
    except:
        fig.savefig('_permerror_price_chart.png')
    
    plt.close(fig)

            
#%% Add mu and sd to the 'out' dataframe, so you can plot it point-in-time.
cancelAllOrders()

priceHistory = []
netWorthHistory = []

nextTrade = 'buy'
plt.ion()
plt.show()

out = out.append(pd.DataFrame([[
                bx_client.get_marketsummary('USDT-BTC')['result'][0]['TimeStamp'],
                np.nan,
                np.nan,
                np.nan,
                getTotalWorth(),
                getPrice(market, 'Last'),
                np.mean(out.lastPrice.tail(rolling_stats)),
                np.std(out.lastPrice.tail(rolling_stats))
                ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
while 1:
    newtime = bx_client.get_marketsummary('USDT-BTC')['result'][0]['TimeStamp']

    if (newtime > str(out.time.tail(1).iloc[0])):
        out = out.append(pd.DataFrame([[
                newtime,
                np.nan,
                np.nan,
                np.nan,
                getTotalWorth(),
                getPrice(market, 'Last'),
                np.mean(out.lastPrice.tail(rolling_stats)),
                np.std(out.lastPrice.tail(rolling_stats))
                ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
    
    if (nextTrade == 'buy') & (getBalance('USDT') < (getPrice(market, 'Ask') * btc_max)):
        nextTrade = 'sell'
        myPrint('Not enough USD to buy, switching to sell')
    if (nextTrade == 'sell') & (getBalance('BTC') < btc_max):
        nextTrade = 'buy'
        myPrint('Not enough BTC to sell, switching to buy')
    
    if len(out) > 10:
        mu = np.mean(out.lastPrice.tail(rolling_stats))
        sd = np.std(out.lastPrice.tail(rolling_stats))
        if (out.lastPrice.tail(1).iloc[0] < (mu - (1*sd))) & (out.lastPrice.tail(1).iloc[0] < out.lastPrice.tail(2).iloc[0]):
            if (len(buy_orders + sell_orders) < num_open_orders) & (getBalance('USDT') > (getPrice(market, 'Ask') * btc_max)):
                buyBTC(btc_max, getPrice(market, 'Bid'))
                out = out.append(pd.DataFrame([[
                        datetime.datetime.strptime(newtime[:19], '%Y-%m-%dT%H:%M:%S'),
                        'buyattempt',
                        btc_max,
                        getPrice(market, 'Bid') + (getPrice(market, 'Ask')-getPrice(market, 'Bid'))/2,
                        getTotalWorth(),
                        getPrice(market, 'Last'),
                        np.mean(out.lastPrice.tail(rolling_stats)),
                        np.std(out.lastPrice.tail(rolling_stats))
                        ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
                nextTrade = 'sell'
        elif (out.lastPrice.tail(1).iloc[0] > (mu + (1*sd))) & (out.lastPrice.tail(1).iloc[0] > out.lastPrice.tail(2).iloc[0]):
            if (len(buy_orders + sell_orders) < num_open_orders) & (getBalance('BTC') > btc_max) & (len(sell_orders) == 0):
                sellBTC(btc_max, getPrice(market, 'Ask'))
                out = out.append(pd.DataFrame([[
                        datetime.datetime.strptime(newtime[:19], '%Y-%m-%dT%H:%M:%S'),
                        'sellattempt',
                        btc_max,
                        getPrice(market, 'Bid') + (getPrice(market, 'Ask')-getPrice(market, 'Bid'))/2,
                        getTotalWorth(),
                        getPrice(market, 'Last'),
                        np.mean(out.lastPrice.tail(rolling_stats)),
                        np.std(out.lastPrice.tail(rolling_stats))
                        ]], columns = ['time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
                nextTrade == 'buy'
    
    removeStaleOrders(sell_orders + buy_orders)
    out = removeCompletedOrders(sell_orders + buy_orders, out)
    
    out = out.reset_index(drop = True)
    out.time = [datetime.datetime.strptime(d[:19], '%Y-%m-%dT%H:%M:%S') if type(d) == str else d for d in out.time]
    
    plotResults(out)
    
    time.sleep(1)
    