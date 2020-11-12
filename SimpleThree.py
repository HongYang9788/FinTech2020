class Strategy():
    # option setting needed
    def __setitem__(self, key, value):
        self.options[key] = value

    # option setting needed
    def __getitem__(self, key):
        return self.options.get(key, '')

    def __init__(self):
        # strategy property
        self.subscribedBooks = {
            'Binance': {
                'pairs': ['ETH-USDT'],
            },
        }
        # 多久取樣的頻率
        # 頻率不要低於60秒
        # 10*60 為10分鐘
        self.period = 10 * 60
        self.options = {}

        # user defined class attribute
        # 可以在下方定義變數
        self.last_type = 'sell'
        self.last_cross_status = None
        self.close_price_trace = np.array([])
        self.ma_long = 180
        self.ma_short =  20
        self.UP = 1
        self.DOWN = 2
        self.l_ma = None
        self.s_ma = None
        self.last_sell_price = 0
        self.last_buy_price = 0
        self.first_time = True
        self.trade_cold =  180
        self.current_trade_cold = 0
        self.ETH_amount = 0

    def get_current_ma_cross(self):
        if np.isnan(self.s_ma) or np.isnan(self.l_ma):
            return None
        if self.s_ma > self.l_ma:
            return self.UP
        return self.DOWN

    # called every self.period
    def trade(self, information):
        exchange = list(information['candles'])[0] #Binance
        pair = list(information['candles'][exchange])[0] # ETH-USDT
        close_price = information['candles'][exchange][pair][0]['close'] # 收盤價格

        self.close_price_trace = np.append(self.close_price_trace, [float(close_price)])
        self.close_price_trace = self.close_price_trace[-self.ma_long:]
        self.s_ma = talib.SMA(self.close_price_trace, self.ma_short)[-1]
        self.l_ma = talib.SMA(self.close_price_trace, self.ma_long)[-1]
        cur_cross = self.get_current_ma_cross()

        if cur_cross is None:
            return []

        if self.last_cross_status is None:
            self.last_cross_status = cur_cross
            return []

        self.ETH_amount = int(float(self['assets'][exchange]['ETH']))

        #Log('Assets' + str(self['assets'][exchange]['ETH']))

        # cross up
        if self.first_time:
            Log('First buying' + ', Assets' + str(self['assets'][exchange]['ETH']))
            self.last_type = 'buy'
            self.last_buy_price = close_price
            self.last_cross_status = cur_cross
            self.first_time = False
            return [
                {
                    'exchange': exchange,
                    'amount': 100,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]
        

        if self.current_trade_cold <= self.trade_cold:
            if self.last_type == 'sell' and (close_price - self.last_sell_price) <=  -0.03 * self.last_sell_price:
                Log('Main buying' + ', Assets' + str(self['assets'][exchange]['ETH']))
                self.last_type = 'buy'
                self.last_buy_price = close_price
                self.last_cross_status = cur_cross
                self.current_trade_cold = 0
                return [
                    {
                        'exchange': exchange,
                        'amount':  150 ,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
            # cross down
            elif self.last_type == 'buy' and (close_price - self.last_buy_price) >=  0.02 * self.last_buy_price:
                Log('Main selling' + ', Assets' + str(self['assets'][exchange]['ETH']))
                self.last_type = 'sell'
                self.last_sell_price = close_price
                self.last_cross_status = cur_cross
                self.current_trade_cold = 0
                return [
                    {
                        'exchange': exchange,
                        'amount': -1 * min(self.ETH_amount, 150),
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
        else:
            if self.last_type == 'sell' and cur_cross == self.UP and self.last_cross_status == self.DOWN:
                Log('Cross buying' + ', Assets' + str(self['assets'][exchange]['ETH']))
                self.last_type = 'buy'
                self.last_buy_price = close_price
                self.last_cross_status = cur_cross
                self.current_trade_cold = 0
                return [
                    {
                        'exchange': exchange,
                        'amount':  40 ,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
            # cross down
            elif self.last_type == 'buy' and cur_cross == self.DOWN and self.last_cross_status == self.UP:
                Log('Cross selling' + ', Assets' + str(self['assets'][exchange]['ETH']))
                self.last_type = 'sell'
                self.last_sell_price = close_price
                self.last_cross_status = cur_cross
                self.current_trade_cold = 0
                return [
                    {
                        'exchange': exchange,
                        'amount': -1 * min(self.ETH_amount, 40),
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
       
        self.last_cross_status = cur_cross
        self.current_trade_cold += 1
        return []
