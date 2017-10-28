import os
os.chdir(r'c:\users\barby\documents\github\coinbase')
import config
import gdax
import time
import pytz
import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt

sell_orders = []
buy_orders = []
out = pd.DataFrame(columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd'])

currencies = ['BTC', 'LTC', 'ETH']

cur_max = 0.25

fee_pct = 0.000005

max_order_time = 120
rolling_stats = 100
num_open_orders = 5

gdax_client = gdax.AuthenticatedClient(config.gdax_api['apiKey'], config.gdax_api['secret'], config.gdax_api['passphrase'])

def myPrint(s):
    print(str(datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')) + ': ' + s)
    
def sell(qty, cur, limit=9999):
    limit = round(limit,2)
    s = gdax_client.sell(price=limit, size=qty, product_id = cur + '-USD')
    if 'status' in s:
        myPrint('Selling ' + str(qty) + ' ' + cur + ' (' + s['id'] + ')')
        sell_orders.append(s)
    else:
        myPrint('Selling ' + str(qty) + ' ' + cur + ' - ' + s['message'])
        
def buy(qty, cur, limit=1):
    limit = round(limit,2)
    b = gdax_client.buy(price=limit, size=qty, product_id = cur + '-USD')
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
    btc = b['BTC']
    usd = b['USD']
    ltc = b['LTC']
    eth = b['ETH']
    p = getPrices('BTC')
    xr_btc = p['bid'] + ((p['ask'] - p['bid'])/2)
    p = getPrices('LTC')
    xr_ltc = p['bid'] + ((p['ask'] - p['bid'])/2)
    p = getPrices('ETH')
    xr_eth = p['bid'] + ((p['ask'] - p['bid'])/2)
    
    return(usd + (btc*xr_btc) + (ltc*xr_ltc) + (eth*xr_eth))

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
                                datetime.datetime.strptime(o['done_at'][:19], '%Y-%m-%dT%H:%M:%S'),
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
                                datetime.datetime.strptime(o['done_at'][:19], '%Y-%m-%dT%H:%M:%S'),
                                'buy',
                                o['size'],
                                (float(o['executed_value']) + float(o['fill_fees'])) / float(o['filled_size']),
                                getTotalWorth(),
                                getPrices(o['product_id'][:3])['price'],
                                np.mean(out.loc[out.currency == o['product_id'][:3]].lastPrice.tail(rolling_stats)),
                                np.std(out.loc[out.currency == o['product_id'][:3]].lastPrice.tail(rolling_stats))
                                ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))

    return(out)
    
def plotResults(out):
    fig = plt.figure(figsize = (8,11))
    for n,c in enumerate(list(set(out.currency))):
        toplot = out.loc[out.currency == c]
        toplot = toplot.reset_index(drop = True)
        ax = fig.add_subplot(4,1,n+1)
        
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
        
        ax.set_title(c + ' price')
        
    ax = fig.add_subplot(414)
    toplot = out.reset_index(drop = True)
    toplot = toplot.loc[toplot.currency == 'BTC']
    ax.plot(toplot.time, toplot.netWorth)
    for l in ax.xaxis.get_majorticklabels():
        l.set_rotation(45)
    
    ax.set_title('Net worth in USD')
    
    ax.ticklabel_format(style='plain', useOffset=False, axis='y')
    
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

#nextTrade = 'buy'
plt.ion()
plt.show()

out = out.append(pd.DataFrame([[
                'BTC',
                gdax_client.get_time()['iso'],
                np.nan,
                np.nan,
                np.nan,
                getTotalWorth(),
                getPrices('BTC')['price'],
                np.nan,
                np.nan
                ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
while 1:
    newtime = gdax_client.get_time()['iso']
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
                        datetime.datetime.strptime(newtime[:19], '%Y-%m-%dT%H:%M:%S'),
                        np.nan,
                        np.nan,
                        np.nan,
                        worth,
                        lastprice[c],
                        mu,
                        sd
                        ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))
    
        if (out.loc[out.currency == c].lastPrice.tail(1).iloc[0] < (mu - (1*sd))) & (out.loc[out.currency == c].lastPrice.tail(1).iloc[0] < out.loc[out.currency == c].lastPrice.tail(2).iloc[0]):
            if (len(buy_orders + sell_orders) < num_open_orders) & ((0.9*usdbal/buyprice[c]) > 0.01):
                buy(round(min(cur_max, 0.9*usdbal/buyprice[c]),2), c, buyprice[c])
                out = out.append(pd.DataFrame([[
                        c,
                        datetime.datetime.strptime(newtime[:19], '%Y-%m-%dT%H:%M:%S'),
                        'buyattempt',
                        round(min(cur_max, 0.9*usdbal/buyprice[c]),2),
                        buyprice[c],
                        worth,
                        lastprice[c],
                        mu,
                        sd
                        ]], columns = ['currency', 'time', 'type', 'qty', 'prc', 'netWorth', 'lastPrice', 'mu', 'sd']))

        elif (out.loc[out.currency == c].lastPrice.tail(1).iloc[0] > (mu + (1*sd))) & (out.loc[out.currency == c].lastPrice.tail(1).iloc[0] > out.loc[out.currency == c].lastPrice.tail(2).iloc[0]):
            if (len(buy_orders + sell_orders) < num_open_orders) & (bal[c] > min(cur_max, bal[c])) & (len(sell_orders) == 0):
                sell(min(cur_max, bal[c]), c, sellprice[c])
                out = out.append(pd.DataFrame([[
                        c,
                        datetime.datetime.strptime(newtime[:19], '%Y-%m-%dT%H:%M:%S'),
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
    out.time = [datetime.datetime.strptime(d[:19], '%Y-%m-%dT%H:%M:%S') if type(d) == str else d for d in out.time]
    
    out = out.tail(1000)
    out = out.reset_index(drop = True)
    plotResults(out)
    
    time.sleep(5)
    