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

function getTime(cb) {
  publicClient.getTime(function(err, response, data) {
    if (data != null) {
      cb(data['iso']);
    } else {
      cb(null);
    }
  })
}

function profit24hr(cb) {
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
      cb(tradingProfit)
    });
  });
};

profit24hr()
