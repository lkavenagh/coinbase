import sys
import os
import time

from Trader import Trader

trader = Trader()

chunk_size = 1

lastBuyCost = trader.getBuyQuote('ETH', chunk_size)[0]
lastSellProceeds = trader.getSellQuote('ETH', chunk_size)[0]

print('Last bought at ${:.2f}'.format(lastBuyCost))
print('Last sold at ${:.2f}'.format(lastSellProceeds))

newSellProceeds = newBuyProceeds = -1
while (newSellProceeds < 0) & (newBuyProceeds < 0):
    sell_quote = trader.getSellQuote('ETH', chunk_size)
    if sell_quote is not None:
        sell_quote = sell_quote[0]
        tmp = sell_quote - lastBuyCost
        if tmp > (newSellProceeds + abs(newSellProceeds)*0.01):
            print('ETH sell price (${:.2f}) rising: Sell proceeds would now be ${:.2f}'.format(sell_quote, tmp))
        newSellProceeds = tmp
    
    buy_quote = trader.getBuyQuote('ETH', chunk_size)
    if buy_quote is not None:
        buy_quote = buy_quote[0]
        tmp = lastSellProceeds - buy_quote
        if tmp > (newBuyProceeds + abs(newBuyProceeds)*0.01):
            print('ETH buy price (${:.2f}) falling: Buy proceeds would now be ${:.2f}'.format(buy_quote, tmp))
        newBuyProceeds = tmp
    
    time.sleep(5)
    
print('Profitable trade!')
print('New sell would generate ${:.2f}'.format(newSellProceeds))
print('New buy would generate ${:.2f}'.format(newBuyProceeds))