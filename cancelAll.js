var config = require('./config');

var CoinbaseExchange = require('coinbase-exchange');
var publicClient = new CoinbaseExchange.PublicClient();
var authedClient = new CoinbaseExchange.AuthenticatedClient(
  config.apiKey,
  config.secret,
  config.passphrase
);

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

cancelAll();
