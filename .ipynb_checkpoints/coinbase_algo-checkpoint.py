import sys
import os
import time

from Trader import Trader

trader = Trader()

chunk_size = 1

lastBuyCost = trader.getBuyQuote('ETH', chunk_size)[0]
lastSellProceeds = trader.getSellQuote('ETH', chunk_size)[0]

sys.stdout.write('{}: Last bought at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastBuyCost))
sys.stdout.write('{}: Last sold at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastSellProceeds))

newSellProceeds = newBuyProceeds = -1
totalProfit = 0
while (newSellProceeds < 0) & (newBuyProceeds < 0):
    sell_quote = trader.getSellQuote('ETH', chunk_size)
    if sell_quote is not None:
        sell_quote = sell_quote[0]
        tmp = sell_quote - lastBuyCost
        if tmp > (newSellProceeds + abs(newSellProceeds)*0.01):
            sys.stdout.write('{}: ETH sell price (${:.2f}) rising: Sell proceeds would now be ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), sell_quote, tmp))
        newSellProceeds = tmp
    
    buy_quote = trader.getBuyQuote('ETH', chunk_size)
    if buy_quote is not None:
        buy_quote = buy_quote[0]
        tmp = lastSellProceeds - buy_quote
        if tmp > (newBuyProceeds + abs(newBuyProceeds)*0.01):
            sys.stdout.write('{}: ETH buy price (${:.2f}) falling: Buy proceeds would now be ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), buy_quote, tmp))
        newBuyProceeds = tmp
    
    if newSellProceeds > 0:
        sys.stdout.write('{}: Profitable trade!\n'.format(time.strftime('%Y-%m-%d %H:%M:%S')))
        sys.stdout.write('{}: New sell generates ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), newSellProceeds))
        totalProfit += newSellProceeds
        lastSellProceeds = sell_quote
        
        sys.stdout.write('{}: Last bought at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastBuyCost))
        sys.stdout.write('{}: Last sold at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastSellProceeds))
        newSellProceeds = -1
        
    if newBuyProceeds > 0:
        sys.stdout.write('{}: Profitable trade!\n'.format(time.strftime('%Y-%m-%d %H:%M:%S')))
        sys.stdout.write('{}: New buy would generate ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), newBuyProceeds))
        totalProfit += newBuyProceeds
        lastBuyCost = buy_quote
        
        sys.stdout.write('{}: Last bought at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastBuyCost))
        sys.stdout.write('{}: Last sold at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastSellProceeds))
        newBuyProceeds = -1
        
    time.sleep(5)
    

