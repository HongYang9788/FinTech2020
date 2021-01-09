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
            'Bitfinex': {
                'pairs': ['ETH-USDT'],
            },
        }
        # 多久取樣的頻率
        # 頻率不要低於60秒
        # 10*60 為10分鐘
        self.period = 60 * 60
        self.options = {}

        # user defined class attribute
        # 可以在下方定義變數
        self.last_type = 'sell'
        self.last_cross_status = None
        self.close_price_trace = np.array([])
        self.high_price_trace = np.array([])
        self.low_price_trace = np.array([])
        self.rsi_long = 30
        self.rsi_short = 12
        self.cci_period = 12
        self.s_rsi = None
        self.l_rsi = None
        self.last_cci = None
        self.UP = 1
        self.DOWN = 2
        self.first_buy = True
        self.last_buy_price = 0
        self.last_sell_price = 0

    def get_current_rsi_cross(self):
        if np.isnan(self.s_rsi) or np.isnan(self.l_rsi):
            return None
        if self.s_rsi > self.l_rsi:
            return self.UP
        return self.DOWN

    # called every self.period
    def trade(self, information):
        exchange = list(information['candles'])[0] #Binance
        pair = list(information['candles'][exchange])[0] # ETH-USDT
        close_price = information['candles'][exchange][pair][0]['close'] # 收盤價格
        high_price = information['candles'][exchange][pair][0]['high']
        low_price = information['candles'][exchange][pair][0]['low']

        # add latest price into trace
        self.close_price_trace = np.append(self.close_price_trace, [float(close_price)])
        self.close_price_trace = self.close_price_trace[-(self.rsi_long+10):]
        self.high_price_trace = np.append(self.high_price_trace, [float(close_price)])
        self.high_price_trace = self.high_price_trace[-(self.rsi_long+10):]
        self.low_price_trace = np.append(self.low_price_trace, [float(close_price)])
        self.low_price_trace = self.low_price_trace[-(self.rsi_long+10):]
        # calculate rsi
        self.s_rsi = talib.RSI(self.close_price_trace, self.rsi_short)[-1]
        self.l_rsi = talib.RSI(self.close_price_trace, self.rsi_long)[-1]
        # calculate cci
        current_cci = talib.CCI(self.high_price_trace, self.low_price_trace, self.close_price_trace, self.cci_period)[-1]

        cur_cross = self.get_current_rsi_cross()

        self.ETH_amount = float(self['assets'][exchange]['ETH'])

        if cur_cross is None:
            return []
        if current_cci is None:
            return []

        if self.last_cross_status is None:
            self.last_cross_status = cur_cross
            return []
        if self.last_cci is None:
            self.last_cci = current_cci
            return []

        if self.first_buy:
            Log('First buying' + ', Assets' + str(self['assets'][exchange]['ETH']))
            self.last_type = 'buy'
            self.last_buy_price = close_price
            self.last_cross_status = cur_cross
            self.last_cci = current_cci
            self.first_buy = False
            return [
                {
                    'exchange': exchange,
                    'amount': float(self['assets'][exchange]['USDT']) / close_price * 0.5,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]

        # CCI從超買區返回正常區
        if self.last_cci > 100 and current_cci <= 100 and (close_price - self.last_buy_price) >=  0.05 * close_price:
            Log('CCI selling' + ', Assets' + str(self['assets'][exchange]['ETH']))
            self.last_type = 'sell'
            self.last_cross_status = cur_cross
            self.last_sell_price = close_price
            self.last_cci = current_cci
            return [
                {
                    'exchange': exchange,
                    'amount': -1 * self.ETH_amount * 0.5,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]
        # CCI從超賣區返回正常區
        elif self.last_cci < -100 and current_cci >= -100 and cur_cross == self.UP and (close_price - self.last_sell_price) <=  -0.05 * close_price:
            Log('CCI buying' + ', Assets' + str(self['assets'][exchange]['ETH']))
            self.last_type = 'buy'
            self.last_cross_status = cur_cross
            self.last_buy_price = close_price
            self.last_cci = current_cci
            return [
                {
                    'exchange': exchange,
                    'amount': float(self['assets'][exchange]['USDT']) / close_price * 0.5,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]
        # CCI 在超買或超賣區 不做事
        elif current_cci < -100 or current_cci > 100:
            self.last_cross_status = cur_cross
            self.last_cci = current_cci
            return []
        # CCI在正常區域
        else:
            if self.last_type == 'sell' and cur_cross == self.UP and self.last_cross_status == self.DOWN and (close_price - self.last_sell_price) <=  -0.02 * close_price:
                Log('RSI buying' + ', Assets' + str(self['assets'][exchange]['ETH']))
                self.last_type = 'buy'
                self.last_cross_status = cur_cross
                self.last_buy_price = close_price
                self.last_cci = current_cci
                return [
                    {
                        'exchange': exchange,
                        'amount': float(self['assets'][exchange]['USDT']) / close_price *  0.2,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
            # cross down
            elif self.last_type == 'buy' and cur_cross == self.DOWN and self.last_cross_status == self.UP and (close_price - self.last_buy_price) >=  0.02 * close_price:
                Log('RSI selling' + ', Assets' + str(self['assets'][exchange]['ETH']))
                self.last_type = 'sell'
                self.last_cross_status = cur_cross
                self.last_sell_price = close_price
                self.last_cci = current_cci
                return [
                    {
                        'exchange': exchange,
                        'amount': -1*self.ETH_amount * 0.2,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
            self.last_cross_status = cur_cross
            self.last_cci = current_cci
            return []
