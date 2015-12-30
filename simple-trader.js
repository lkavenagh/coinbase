var config = require('./config');
var moment = require('moment');

var CoinbaseExchange = require('coinbase-exchange');
var publicClient = new CoinbaseExchange.PublicClient();
var authedClient = new CoinbaseExchange.AuthenticatedClient(
  config.apiKey,
  config.secret,
  config.passphrase
  // 'https://api-public.sandbox.exchange.coinbase.com'
);

var tooLongBuy = 10 //don't leave a buy order unfilled for more than 10 seconds
var tooLongSell = 60 * 5
var redoSell = true;
var qty = 0.02;
var spread = 0.1;
var lastprice = -1;
var nextOrderIsBuy = true;
var usdBalance = 0;
var btcBalance = 0;
var timeSinceLastFill = 60;

function cancelAll() {
  authedClient.getOrders(function(err, response, data){
    for (var i = 0; i < data.length; i++) {
      var id = data[i]['id'];
      authedClient.cancelOrder(data[i]['id'], function(err, response, data){
        console.log("Cancelled order: ", id);
      });
    }
  });
};

function listAllOrders() {
  authedClient.getOrders(function(err, response, data){
    if (data.length == 0) {
      console.log('No open orders');
    }
    for (var i = 0; i < data.length; i++) {
      console.log(data[i])
    }
  });
};

function profit24hr() {
  var avgBuyPrice = 0;
  var avgSellPrice = 0;
  var buyQty = 0;
  var sellQty = 0;
  var totalFees = 0;
  getTime(function(nowTime){
    authedClient.getFills(function(err, response, fills){
      if (fills.length == 0) {
        console.log('No fills');
      }
      for (var i = 0; i < fills.length; i++) {
        if (moment(nowTime).diff(moment(fills[i]['created_at']), 'seconds') < (60*60*24)) {
          if (fills[i]['side'] == 'sell') {
            avgSellPrice = avgSellPrice + (fills[i]['price'] * fills[i]['size'])
            sellQty = sellQty + parseFloat(fills[i]['size'])
          } else {
            avgBuyPrice = avgBuyPrice + (fills[i]['price'] * fills[i]['size'])
            buyQty = buyQty + parseFloat(fills[i]['size'])
          }
          totalFees = totalFees + parseFloat(fills[i]['fee'])
        }
      }
      avgBuyPrice = avgBuyPrice / buyQty
      avgSellPrice = avgSellPrice / sellQty

      var tradingProfit = (avgSellPrice * sellQty) - (avgBuyPrice * buyQty) - totalFees
      myPrint('Last 24 hours trading profit: ' + tradingProfit)
    });
  });
};

function getTime(cb) {
  publicClient.getTime(function(err, response, data) {
    if (data != null) {
      cb(data['iso']);
    } else {
      cb(null);
    }
  })
}

function sell(askprice, qty, cb) {
  var sellParams = {
    'price': askprice, //USD
    'size': qty, //BTC
    'product_id': 'BTC-USD'
  };
  authedClient.sell(sellParams, function(err, response, data){
    console.log(data);
    var success = false;
    if (data['message'] != 'price too precise') {
      success = true;
    }
    cb(success);
  });
};

function buy(bidprice, qty, cb) {
  var buyParams = {
    'price': bidprice, //USD
    'size': qty, //BTC
    'product_id': 'BTC-USD'
  };
  authedClient.buy(buyParams, function(err, response, data){
    console.log(data);
    var success = false;
    if (data['message'] != 'price too precise') {
      success = true;
    }
    cb(success);
  });
};

function myPrint(text) {
  var date = new Date();

  var hour = date.getHours();
  hour = (hour < 10 ? "0" : "") + hour;

  var min  = date.getMinutes();
  min = (min < 10 ? "0" : "") + min;

  var sec  = date.getSeconds();
  sec = (sec < 10 ? "0" : "") + sec;

  var year = date.getFullYear();

  var month = date.getMonth() + 1;
  month = (month < 10 ? "0" : "") + month;

  var day  = date.getDate();
  day = (day < 10 ? "0" : "") + day;

  console.log("[" + year + "-" + month + "-" + day + " " + hour + ":" + min + ":" + sec + "] " + text);
  //console.log("[" + date.toISOString() + "] " + text);
}

function main() {
  publicClient.getProductOrderBook({'level': '1'}, function(err, response, data) {
    if (data != null) {
      var bidprice = parseFloat(data['bids'][0][0]);
      var bidsize = data['bids'][0][1];
      var askprice = parseFloat(data['asks'][0][0]);
      var asksize = data['asks'][0][1];

      getTime(function(nowTime){
        if (nowTime != null) {
          authedClient.getOrders(function(err, response, orders){
            if (orders == null || orders.length == 0) {
              // No orders on the book, cooldown ready, so lets make the algo do something

              authedClient.getAccounts(function(err, response, accounts){
                // Get balances
                for (var i = 0; i < accounts.length; i++) {
                  if (accounts[i]['currency'] == 'USD') {
                    usdBalance = parseFloat(accounts[i]['balance']);
                  } else if (accounts[i]['currency'] == 'BTC') {
                    btcBalance = parseFloat(accounts[i]['balance']);
                  };
                };
                var totalUSD = usdBalance + (btcBalance*bidprice);

                authedClient.getFills(function(err, response, fills) {
                  if (fills.length > 0) {
                    lastprice = parseFloat(fills[0]['price']);
                    nextOrderIsBuy = fills[0]['side'] == 'sell';
                    timeSinceLastFill = moment(nowTime).diff(moment(fills[0]['created_at']), 'seconds')
                    if (!nextOrderIsBuy && redoSell) {
                      lastprice = askprice-spread;
                      redoSell = false;
                    }
                    if (nextOrderIsBuy) {
                      if ((askprice - bidprice) > 0.02) {
                        tradePrice = Math.round(100*(bidprice + askprice)/2)/100
                      } else {
                        tradePrice = bidprice;
                      }
                    } else {
                      if ((askprice - bidprice) > 0.02) {
                        tradePrice = Math.max(Math.round(100*(bidprice + askprice)/2)/100, (lastprice+spread));
                      } else {
                        tradePrice = Math.max(askprice, (lastprice+spread));
                      }
                    }
                  } else {
                    // No fills, do a buy first
                    nextOrderIsBuy = true;
                    tradePrice = bidprice;
                  }
                  if (nextOrderIsBuy) {
                    // Send in a BUY order
                    if (usdBalance > (tradePrice * qty * 1.0025) && timeSinceLastFill >= 10) {
                      myPrint('Total balance = ' + totalUSD);
                      profit24hr();
                      myPrint("Buy " + qty + " at " + tradePrice);
                      s = buy(Math.round(100*tradePrice)/100, qty, function(s) {});
                    } else {
                      myPrint('timeSinceLastFill: ' + timeSinceLastFill + ' seconds');
                    }
                  } else {
                    // Send in a SELL order
                    if (btcBalance > qty && timeSinceLastFill > 10) {
                      myPrint('Total balance = ' + totalUSD);
                      profit24hr();
                      myPrint("Sell " + qty + " at " + tradePrice);
                      s = sell(Math.round(100*tradePrice)/100, qty, function(s) {});
                    }
                  }
                });
              });
            } else {
              // There's an order waiting, cancel it if it's been there too long and it's a buy
              if (orders[0] != undefined && orders[0]['side'] == 'buy') {
                timeSinceLastFill = moment(nowTime).diff(moment(orders[0]['created_at']), 'seconds')
                if (timeSinceLastFill > tooLongBuy) {
                  myPrint('Buy order unfilled for ' + timeSinceLastFill + ' seconds, cancelling...');
                  cancelAll();
                }
              }
              if (orders[0] != undefined && orders[0]['side'] == 'sell') {
                timeSinceLastFill = moment(nowTime).diff(moment(orders[0]['created_at']), 'seconds')
                if (timeSinceLastFill > tooLongSell && parseFloat(orders[0]['price']) > (askprice + 0.25)) {
                  myPrint('Sell order unfilled for ' + timeSinceLastFill + ' seconds, cancelling...');
                  cancelAll();
                  redoSell = true;
                }
              }
            };
          });
        }
      });
      setTimeout(main, 5000);
    }
  });
}
main();
