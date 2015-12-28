var CoinbaseExchange = require('coinbase-exchange');
var publicClient = new CoinbaseExchange.PublicClient();
var authedClient = new CoinbaseExchange.AuthenticatedClient(
  'ea3867448cb29220af13b39e26a2f5b7',
  'c9cVzSi3x1gDbVTWmYB/WiTvP/Q2xfIHoU6+1RWjVZx4R+8tDcMJqabrjinM5FpB3fv5dd+xTAiGeTb3OUKJZw==',
  'qj8l5rolkr9t3xr'
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
