var CoinbaseExchange = require('coinbase-exchange');
var publicClient = new CoinbaseExchange.PublicClient();
var authedClient = new CoinbaseExchange.AuthenticatedClient(
  '8f575a96c1bcd93e933bfef84c6b130e',
  'bn8v17GTfyQWx22VRxQM/QqlyCtiE7Ybd+NBJZUVsc/qSwnNFnDNKBxHK9j/WNnpo7rPCW2DcFYtjy0CbXvrHg==',
  'lm9l7jzawobyylfudbq589f6r'
);
// var client = new Client({'apiKey': 'Tl2NnJCujIMvqRet',
//                          'apiSecret': 'DrJ4V0s0aJWmJbvcqvpWC2HVdFEhJpwA'})

// var sellParams = {
//   'price': '460', //USD
//   'size': '0.01', //BTC
//   'product_id': 'BTC-USD'
// };
// authedClient.sell(sellParams, function(err, response, data){
//   console.log(data);
// });

authedClient.getOrders(function(err, response, data){
  // authedClient.cancelOrder(data[0]['id'], function(err, response, data){
    console.log(data);
  // });
});

console.log(Math.round(553.12345*100)/100)

// authedClient.getAccounts(function(err, response, data){
//   console.log(data);
//   for (var i = 0; i < data.length; i++) {
//     console.log(data[i]['currency'] == 'USD');
//   }
// });
