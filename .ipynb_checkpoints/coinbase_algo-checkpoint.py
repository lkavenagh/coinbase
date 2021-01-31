import sys
import os
import time
import numpy as np

from Trader import Trader

def wait_for_price_turnaround(price_type = 'sell'):
    if price_type == 'sell':
        # Wait for price to stop rising
        sell_quote = trader.getSellQuote(cc, chunk_size)[0]
        print('Current sell quote: {:.2f}'.format(sell_quote))
        print('Last buy cost: {:.2f}'.format(last_buy_cost))
        sell_proceeds = sell_quote - last_buy_cost
        print('Current sell proceeds: {:.2f}'.format(sell_proceeds))
        if test:
            stop_loss = sell_quote - 1
        else:
            stop_loss = (sell_proceeds/2) + last_buy_cost
            
        print('Price at which turnaround is true: {:.2f}'.format(stop_loss))

        while sell_quote > stop_loss:
            sell_quote = trader.getSellQuote(cc, chunk_size)[0]
            
            new_sell_proceeds = sell_quote - last_buy_cost
            if new_sell_proceeds > sell_proceeds:
                if test:
                    stop_loss = sell_quote - 1
                else:
                    stop_loss = (sell_proceeds/2) + last_buy_cost
                sell_proceeds = new_sell_proceeds
                sys.stdout.write('{}: Price (${:.2f}) still rising, new sell would currently generate ${:.2f} stop loss adjusted to ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), sell_quote, new_sell_proceeds, stop_loss))
            
            time.sleep(5)
            
        sys.stdout.write('{}: Price ({:.2f}) has turned around and hit stop loss ({:.2f})\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), sell_quote, stop_loss))
        
        return(1)
            
    elif price_type == 'buy':
        # Wait for price to stop falling
        buy_quote = trader.getBuyQuote(cc, chunk_size)[0]
        buy_proceeds = last_sell_cost - buy_quote
        if test:
            stop_loss = buy_quote + 1
        else:
            stop_loss = last_sell_cost - (buy_proceeds/2)

        while buy_quote < stop_loss:
            buy_quote = trader.getBuyQuote(cc, chunk_size)[0]
            
            new_buy_proceeds = last_sell_cost - buy_quote
            if new_buy_proceeds > buy_proceeds:
                if test:
                    stop_loss = buy_quote + 1
                else:
                    stop_loss = last_sell_cost - (buy_proceeds/2)
                buy_proceeds = new_buy_proceeds
                sys.stdout.write('{}: Price (${:.2f}) still falling, new buy would currently generate ${:.2f} (stop loss adjusted to ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), buy_quote, new_buy_proceeds, stop_loss))
            
            time.sleep(5)

        sys.stdout.write('{}: Price ({:.2f}) has turned around and hit stop loss ({:.2f})\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), buy_quote, stop_loss))
        
        return(1)

def wait_for_profitable_margin():
    global last_reported_sell_profit, last_reported_buy_profit, sell_proceeds, buy_proceeds
    
    sell_quote = trader.getSellQuote(cc, chunk_size)[0]
    sell_proceeds = sell_quote - last_buy_cost
    
    buy_quote = trader.getBuyQuote(cc, chunk_size)[0]
    buy_proceeds = last_sell_proceeds - buy_quote
    
    while (sell_proceeds < profit_margin_usd) & (buy_proceeds < profit_margin_usd):
        sell_quote = trader.getSellQuote(cc, chunk_size)
        if sell_quote is not None:
            sell_quote = sell_quote[0]
            tmp = sell_quote - last_buy_cost
            if tmp > (last_reported_sell_profit + abs(last_reported_sell_profit)*0.05):
                sys.stdout.write('{}: {} sell price (${:.2f}) rising: Sell proceeds would now be ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), cc, sell_quote, tmp))
                last_reported_sell_profit = tmp
            sell_proceeds = tmp

        buy_quote = trader.getBuyQuote(cc, chunk_size)
        if buy_quote is not None:
            buy_quote = buy_quote[0]
            tmp = last_sell_proceeds - buy_quote
            if tmp > (last_reported_buy_profit + abs(last_reported_buy_profit)*0.05):
                sys.stdout.write('{}: {} buy price (${:.2f}) falling: Buy proceeds would now be ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), cc, buy_quote, tmp))
                last_reported_buy_profit = tmp
            buy_proceeds = tmp
            
        sys.stdout.flush()
        time.sleep(5)
        
    return(1)

trader = Trader()

cc = 'BTC'
profit_margin_usd = -5
test = True

size_of_trade_usd = 250
chunk_size = size_of_trade_usd / trader.getBuyQuote(cc, 1)[0]

sys.stdout.write('Trading {}\n'.format(cc))
sys.stdout.write('Chunk size: {:,.4f} {}\n\n'.format(chunk_size, cc))
sys.stdout.flush()

last_buy_cost = trader.getBuyQuote(cc, chunk_size)[0]
last_sell_proceeds = trader.getSellQuote(cc, chunk_size)[0]

anchor_price = (last_buy_cost + last_sell_proceeds) / 2
last_buy_cost = anchor_price
last_sell_proceeds = anchor_price
sys.stdout.write('{}: Anchor price set at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), anchor_price))
sys.stdout.flush()

sell_proceeds = buy_proceeds = -np.Inf

last_reported_sell_profit = last_reported_buy_profit = -1e6

total_profit = 0

cc_balance = 0.01
usd_balance = 500

while(1):
    sys.stdout.write('{} balance: {:,.4f}\n'.format(cc, cc_balance))
    sys.stdout.write('{} balance: {:,.4f}\n\n'.format('USD', usd_balance))
    sys.stdout.flush()
    
    wait_for_profitable_margin()

    if sell_proceeds > profit_margin_usd:
        # Price is rising. Wait for it to start turning around
        sys.stdout.write('\n{}: Profitable trade!\n'.format(time.strftime('%Y-%m-%d %H:%M:%S')))
        sys.stdout.write('{}: New sell would currently generate ${:.2f}\n\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), sell_proceeds))
        sys.stdout.flush()
        
        wait_for_price_turnaround('sell')

        if test:
            sell_quote = trader.getSellQuote(cc, chunk_size)[0]
        else:
            sell_order = trader.sell(cc, chunk_size)
            sell_quote = float(sell_order.total.amount)
        
        sell_proceeds = sell_quote - last_buy_cost

        sys.stdout.write('{}: Selling - proceeds: ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), sell_proceeds))

        total_profit += sell_proceeds
        last_sell_proceeds = sell_quote

        if test:
            cc_balance -= chunk_size
        else:
            cc_balance -= float(sell_order.amount.amount)
        
        usd_balance += sell_quote

        sys.stdout.write('{}: USD balance: ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), usd_balance))
        sys.stdout.write('{}: {} balance: {:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), cc, cc_balance))
        
        sys.stdout.write('{}: Last bought at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), last_buy_cost))
        sys.stdout.write('{}: Last sold at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), last_sell_proceeds))
        sell_proceeds = -np.Inf
        sys.stdout.flush()


    elif buy_proceeds > profit_margin_usd:
        # Price is falling. Wait for it to turn around
        sys.stdout.write('\n{}: Profitable trade!\n'.format(time.strftime('%Y-%m-%d %H:%M:%S')))
        sys.stdout.write('{}: New buy would currently generate ${:.2f}\n\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), buy_proceeds))
        sys.stdout.flush()
        
        wait_for_price_turnaround('buy')

        if test:
            buy_quote = trader.getBuyQuote(cc, chunk_size)[0]
        else:
            buy_order = trader.buy(cc, chunk_size)
            buy_quote = float(buy_order.total.amount)
            
        buy_proceeds = last_sell_cost - buy_quote

        sys.stdout.write('{}: Buying - proceeds: ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), buy_proceeds))

        total_profit += buy_proceeds
        last_buy_cost = buy_quote

        if test:
            cc_balance += chunk_size
        else:
            cc_balance += float(buy_order.amount.amount)
        usd_balance -= buy_quote

        sys.stdout.write('{}: USD balance: ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), usd_balance))
        sys.stdout.write('{}: {} balance: {:.4f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), cc, cc_balance))
        
        sys.stdout.write('{}: Last bought at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), last_buy_cost))
        sys.stdout.write('{}: Last sold at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), last_sell_proceeds))
        buy_proceeds = -np.Inf
        sys.stdout.flush()
        

    # Finished one iteration - need to reset last buy/sell price
    # Complete another buy/sell if we are out of balance in CC or USD
    if cc_balance < chunk_size:
        # buy
        if test:
            buy_quote = trader.getBuyQuote(cc, chunk_size)[0]
            cc_balance += chunk_size
        else:
            buy_order = trader.buy(cc, chunk_size)
            buy_quote = buy_order.total.amount
            cc_balance += float(buy_order.amount.amount)
        
        usd_balance -= buy_quote
            
        last_buy_cost = buy_quote
        sys.stdout.write('{}: Buying (to rebalance) - cost: ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), last_buy_cost))
        sys.stdout.flush()
        last_sell_proceeds = trader.getSellQuote(cc, chunk_size)[0]
        
    elif usd_balance < size_of_trade_usd:
        # sell
        if test:
            sell_quote = trader.getSellQuote(cc, chunk_size)[0]
            cc_balance -= chunk_size
        else:
            sell_order = trader.sell(cc, chunk_size)
            sell_quote = sell_order.total.amount
            cc_balance -= float(sell_order.amount.amount)
        
        usd_balance += sell_quote
            
        last_sell_proceeds = sell_quote
        sys.stdout.write('{}: Selling (to rebalance) - proceeds: ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), last_sell_proceeds))
        sys.stdout.flush()
        last_buy_cost = trader.getBuyQuote(cc, chunk_size)[0]
        
    else:
        last_buy_cost = trader.getBuyQuote(cc, chunk_size)[0]
        last_sell_proceeds = trader.getSellQuote(cc, chunk_size)[0]
        
    sys.stdout.write('{}: USD balance: ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), usd_balance))
    sys.stdout.write('{}: {} balance: {:.4f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), cc, cc_balance))
    
    sys.stdout.write('Finished an iteration\n')
    sys.stdout.flush()
    
    last_reported_sell_profit = last_reported_buy_profit = -1e6
    
    time.sleep(5)