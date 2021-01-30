import sys
import os
import time

from Trader import Trader

trader = Trader()

cc = 'ETH'

size_of_trade_usd = 250
chunk_size = size_of_trade_usd / trader.getBuyQuote(cc, 1)[0]

sys.stdout.write('Trading {}\n'.format(cc))
sys.stdout.write('Chunk size: {:,.4f} {}'.format(chunk_size, cc))
sys.stdout.flush()

lastBuyCost = trader.getBuyQuote(cc, chunk_size)[0]
lastSellProceeds = trader.getSellQuote(cc, chunk_size)[0]

sys.stdout.write('{}: First bought at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastBuyCost))
sys.stdout.write('{}: First sold at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastSellProceeds))
sys.stdout.flush()

newSellProceeds = newBuyProceeds = -1
lastReportedSellPrice = lastReportedBuyPrice = -1e6
totalProfit = 0
totalUSDSpent = 0
while (newSellProceeds < 0) & (newBuyProceeds < 0):
    sell_quote = trader.getSellQuote(cc, chunk_size)
    if sell_quote is not None:
        sell_quote = sell_quote[0]
        tmp = sell_quote - lastBuyCost
        if tmp > (lastReportedSellPrice + abs(lastReportedSellPrice)*0.05):
            sys.stdout.write('{}: {} sell price (${:.2f}) rising: Sell proceeds would now be ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), cc, sell_quote, tmp))
            lastReportedSellPrice = tmp
        newSellProceeds = tmp
    
    buy_quote = trader.getBuyQuote(cc, chunk_size)
    if buy_quote is not None:
        buy_quote = buy_quote[0]
        tmp = lastSellProceeds - buy_quote
        if tmp > (lastReportedBuyPrice + abs(lastReportedBuyPrice)*0.05):
            sys.stdout.write('{}: {} buy price (${:.2f}) falling: Buy proceeds would now be ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), cc, buy_quote, tmp))
            lastReportedBuyPrice = tmp
        newBuyProceeds = tmp
    
    if newSellProceeds > 0:
        sys.stdout.write('\n{}: Profitable trade!\n'.format(time.strftime('%Y-%m-%d %H:%M:%S')))
        sys.stdout.write('{}: New sell generates ${:.2f}\n\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), newSellProceeds))
        totalProfit += newSellProceeds
        lastSellProceeds = sell_quote
        lastReportedSellPrice = 0
        
        totalUSDSpent -= sell_quote
        
        sys.stdout.write('{}: Spent USD${:.2f} so far\n\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), totalUSDSpent))
        
        sys.stdout.write('{}: Last bought at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastBuyCost))
        sys.stdout.write('{}: Last sold at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastSellProceeds))
        newSellProceeds = -1
        
    if newBuyProceeds > 0:
        sys.stdout.write('\n{}: Profitable trade!\n'.format(time.strftime('%Y-%m-%d %H:%M:%S')))
        sys.stdout.write('{}: New buy would generate ${:.2f}\n\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), newBuyProceeds))
        totalProfit += newBuyProceeds
        lastBuyCost = buy_quote
        lastReportedBuyPrice = 0
        
        totalUSDSpent += buy_quote
        
        sys.stdout.write('{}: Spent USD${:.2f} so far\n\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), totalUSDSpent))
        
        sys.stdout.write('{}: Last bought at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastBuyCost))
        sys.stdout.write('{}: Last sold at ${:.2f}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), lastSellProceeds))
        newBuyProceeds = -1
        
    sys.stdout.flush()
    time.sleep(5)
    

