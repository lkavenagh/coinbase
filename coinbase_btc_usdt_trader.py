import os
os.chdir(r'c:\users\barby\documents\github\coinbase')
import config
import gdax
import time
import pytz
from dateutil import tz
import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt

sell_orders = []
buy_orders = []
out = pd.DataFrame(columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd'])

returns = [None, None, None]
currencies = ['BTC', 'BCH', 'LTC', 'ETH']

cur_max = 0.01

fee_pct = 0.000005

global from_zone
global to_zone
from_zone = tz.tzutc()
to_zone = tz.tzlocal()

max_order_time = 120
rolling_stats = 100
num_open_orders = 5

gdax_client = gdax.AuthenticatedClient(config.gdax_api['apiKey'], config.gdax_api['secret'], config.gdax_api['passphrase'])

def myPrint(s):
    print(str(datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')) + ': ' + s)
    
def sell(qty, cur, limit=9999):
    limit = round(limit,2)
    s = gdax_client.sell(price=limit, size=qty, post_only = True, product_id = cur + '-USD')
    if 'status' in s:
        myPrint('Selling ' + str(qty) + ' ' + cur + ' (' + s['id'] + ')')
        sell_orders.append(s)
    else:
        myPrint('Selling ' + str(qty) + ' ' + cur + ' - ' + s['message'])
        
def buy(qty, cur, limit=1):
    limit = round(limit,2)
    b = gdax_client.buy(price=limit, size=qty, post_only = True, product_id = cur + '-USD')
    if 'status' in b:
        myPrint('Buying ' + str(qty) + ' ' + cur + ' (' + b['id'] + ')')
        buy_orders.append(b)
    else:
        myPrint('Buying ' + str(qty) + ' ' + cur + ' - ' + b['message'])

def cancelAllOrders():
    orders = gdax_client.get_orders()
    for o in orders[0]:
        cancelOrder(o['id'])
        
def cancelOrder(id):
    o = getOrderStatus(id)
    if o != None:
        myPrint('Cancelling ' + o['side'] + ' order (' + o['id'] + ')')
        c = gdax_client.cancel_order(id)
        if 'message' not in c:
            if o['side'] == 'sell':
                if len(np.where([True if b['id'] == id else False for b in sell_orders])[0]) > 0:
                    sell_orders.remove(sell_orders[np.where([True if b['id'] == id else False for b in sell_orders])[0][0]])
            elif o['side'] == 'buy':
                if len(np.where([True if b['id'] == id else False for b in buy_orders])[0]) > 0:
                    buy_orders.remove(buy_orders[np.where([True if b['id'] == id else False for b in buy_orders])[0][0]])
        else:
            myPrint(c['message'])
            
def getOrderStatus(id):
    o = gdax_client.get_order(id)
    return(o)
    
def getPrices(cur):
    try:
        p = gdax_client.get_product_ticker(cur + '-USD')
    except:
        time.sleep(1)    
        p = gdax_client.get_product_ticker(cur + '-USD')
    p['ask']= float(p['ask'])
    p['bid']= float(p['bid'])
    p['price']= float(p['price'])
    return(p)

def getBalances():
    try:
        b = gdax_client.get_accounts()
    except:
        time.sleep(1)
        b = gdax_client.get_accounts()
    s = dict()
    for i in b:
        s[i['currency']] = float(i['balance'])
    return s

def getAccountIds():
    b = gdax_client.get_accounts()
    s = dict()
    for i in b:
        s[i['currency']] = i['id']
    return s

def getTotalWorth():
    b = getBalances()
    usd = b['USD']
    
    worths = []
    
    for c in currencies:
        p = getPrices(c)
        if 'ask' in p.keys():
            worths.append((p['bid'] + ((p['ask'] - p['bid'])/2)) * getBalances()[c])
        else:
            p = getPrices(c)
            worths.append((p['bid'] + ((p['ask'] - p['bid'])/2)) * getBalances()[c])
    
    return(usd + sum(worths))

def removeStaleOrders(orders):
    for s in orders:
        o = getOrderStatus(s['id'])
        if o != None:
            n = datetime.datetime.now(datetime.timezone.utc)
            ot = pytz.utc.localize(datetime.datetime.strptime(o['created_at'][:19], '%Y-%m-%dT%H:%M:%S'))
            td = n - ot
            if (n > ot) & (td.seconds > max_order_time):
                if o['id'] != None:
                    cancelOrder(o['id'])

def removeCompletedOrders(orders, out):
    for s in orders:
        o = getOrderStatus(s['id'])
        if o != None:
            if 'status' in o:
                if o['status'] == 'done':
                    if o['side'] == 'sell':
                        sell_orders.remove(sell_orders[np.where([True if b['id'] == s['id'] else False for b in sell_orders])[0][0]])
                        out = out.append(pd.DataFrame([[
                                o['product_id'][:3],
                                datetime.datetime.strptime(o['done_at'][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=from_zone).astimezone(to_zone).replace(tzinfo=None),
                                'sell',
                                o['size'],
                                (float(o['executed_value']) - float(o['fill_fees'])) / float(o['filled_size']),
                                getTotalWorth(),
                                getPrices(o['product_id'][:3])['price'],
                                np.mean(out.loc[out.currency == o['product_id'][:3]].lastPrice.tail(rolling_stats)),
                                np.std(out.loc[out.currency == o['product_id'][:3]].lastPrice.tail(rolling_stats))
                                ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
                    elif o['side'] == 'buy':
                        buy_orders.remove(buy_orders[np.where([True if b['id'] == s['id'] else False for b in buy_orders])[0][0]])
                        out = out.append(pd.DataFrame([[
                                o['product_id'][:3],
                                datetime.datetime.strptime(o['done_at'][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=from_zone).astimezone(to_zone).replace(tzinfo=None),
                                'buy',
                                o['size'],
                                (float(o['executed_value']) + float(o['fill_fees'])) / float(o['filled_size']),
                                getTotalWorth(),
                                getPrices(o['product_id'][:3])['price'],
                                np.mean(out.loc[out.currency == o['product_id'][:3]].lastPrice.tail(rolling_stats)),
                                np.std(out.loc[out.currency == o['product_id'][:3]].lastPrice.tail(rolling_stats))
                                ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))

    return(out)
    
def plotResults(out, b, returns):
    fig = plt.figure(figsize = (8,11))
    numplots = len(set(out.currency))+1
    for n,c in enumerate(list(set(out.currency))):
        toplot = out.loc[out.currency == c]
        toplot = toplot.reset_index(drop = True)
        ax = fig.add_subplot(numplots,1,n+1)
        
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
        
        ax.set_title(c + ' price' + '        ' + 'Balance: ' + str(round(b[c],3)))
        
    ax = fig.add_subplot(numplots,1,numplots)
    toplot = out.reset_index(drop = True)
    toplot = toplot.loc[toplot.currency == 'BTC']
    ax.plot(toplot.time, toplot.netWorth)
    for l in ax.xaxis.get_majorticklabels():
        l.set_rotation(45)
    
    ax.set_title('Net worth in USD' + '        ' + 'USD Balance: ' + str(round(b['USD'],3)))
    
    ax.ticklabel_format(style='plain', useOffset=False, axis='y')
    
    fig.text(0,0,'BTC return: ' + str(round(returns[0],2)) + '    My return: ' + str(round(returns[1],2)) + '    Excess return: ' + str(round(returns[2],2)), ha = 'left')
    fig.tight_layout()
    
    try:
        fig.savefig('price_chart.png')
    except:
        fig.savefig('_permerror_price_chart.png')
    
    plt.close(fig)

            
#%%
cancelAllOrders()

priceHistory = []
netWorthHistory = []

minsizes = dict()
minsizes['BTC'] = 0.001
minsizes['BCH'] = 0.01
minsizes['LTC'] = 0.1
minsizes['ETH'] = 0.01

#nextTrade = 'buy'
plt.ion()
plt.show()

starting_btc = getPrices('BTC')['price']
starting_pot = getTotalWorth()

newtime = datetime.datetime.strptime(gdax_client.get_time()['iso'][:19], '%Y-%m-%dT%H:%M:%S')

out = out.append(pd.DataFrame([[
                'BTC',
                newtime,
                np.nan,
                np.nan,
                np.nan,
                getTotalWorth(),
                getPrices('BTC')['price'],
                np.nan,
                np.nan
                ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))

out.time = [d.replace(tzinfo=from_zone).astimezone(to_zone).replace(tzinfo=None) for d in out.time]

while 1:
    newtime = datetime.datetime.strptime(gdax_client.get_time()['iso'][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=from_zone).astimezone(to_zone).replace(tzinfo=None)
    b = getBalances()
    usdbal = b['USD']
    bal = dict()
    sellprice = dict()
    buyprice = dict()
    lastprice = dict()
    for c in currencies:
        bal[c] = b[c]
        prices = getPrices(c)
        askprice = prices['ask']
        bidprice = prices['bid']
        lastprice[c] = prices['price']
        feediff = fee_pct * lastprice[c]
        buyprice[c] = bidprice - feediff
        sellprice[c] = askprice + feediff
    worth = getTotalWorth()
    
    for c in currencies:
        mu = np.mean(out.loc[out.currency == c].lastPrice.tail(rolling_stats))
        sd = np.std(out.loc[out.currency == c].lastPrice.tail(rolling_stats))
        if sd > 100:
            print(out)
            raise ValueError('A very specific bad thing happened')
        
        out = out.append(pd.DataFrame([[
                        c,
                        newtime,
                        np.nan,
                        np.nan,
                        np.nan,
                        worth,
                        lastprice[c],
                        mu,
                        sd
                        ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
    
        if (out.loc[out.currency == c].lastPrice.tail(1).iloc[0] < (mu - (1*sd))) & (out.loc[out.currency == c].lastPrice.tail(1).iloc[0] < out.loc[out.currency == c].lastPrice.tail(2).iloc[0]):
            if (len(buy_orders + sell_orders) < num_open_orders) & ((0.9*usdbal/buyprice[c]) > 0.01) & (round(min(cur_max, 0.9*usdbal/buyprice[c]),2) > minsizes[c]):
                buy(round(min(cur_max, 0.9*usdbal/buyprice[c]),2), c, buyprice[c])
                out = out.append(pd.DataFrame([[
                        c,
                        newtime,
                        'buyattempt',
                        round(min(cur_max, 0.9*usdbal/buyprice[c]),2),
                        buyprice[c],
                        worth,
                        lastprice[c],
                        mu,
                        sd
                        ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))

        elif (out.loc[out.currency == c].lastPrice.tail(1).iloc[0] > (mu + (1*sd))) & (out.loc[out.currency == c].lastPrice.tail(1).iloc[0] > out.loc[out.currency == c].lastPrice.tail(2).iloc[0]):
            if (len(buy_orders + sell_orders) < num_open_orders) & (bal[c] > min(cur_max, bal[c])) & (len(sell_orders) == 0) & (min(cur_max, bal[c]) > minsizes[c]):
                sell(min(cur_max, bal[c]), c, sellprice[c])
                out = out.append(pd.DataFrame([[
                        c,
                        newtime,
                        'sellattempt',
                        min(cur_max, bal[c]),
                        sellprice[c],
                        worth,
                        lastprice[c],
                        mu,
                        sd
                        ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))

    
    removeStaleOrders(sell_orders + buy_orders)
    out = removeCompletedOrders(sell_orders + buy_orders, out)
    
    out = out.reset_index(drop = True)
    
    out = out.tail(10)
    out = out.reset_index(drop = True)
    out = out.sort_values('time')
    
    current_btc = getPrices('BTC')['price']
    current_pot = getTotalWorth()

    returns[0] = (current_btc - starting_btc) / starting_btc
    returns[1] = (current_pot - starting_pot) / starting_pot
    returns[2] = returns[1] - returns[0]
    
    plotResults(out, b, returns)
    
    time.sleep(3)