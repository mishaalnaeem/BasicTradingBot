from binance.client import Client
import pandas as pd
from time import sleep
import pandas_ta as ta
import numpy as np
import time
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException

#init
api_key = "ZWRaoWOTwGjOXplLWXI6tjSjApuNhbc57xWlMSNtr8mUuN2z9fHz1LHfuW8iQuUo"
api_secret = "rxv4pGIxiPCHfBkiP7ycQkclNp6hYSQ56GLEcPJhuLzqkXaFTYbG4nxensO6LPgT"

client = Client(api_key, api_secret)

client.API_URL = 'https://testnet.binance.vision/api'

cryptoSymbol = 'ETHUSDT'

def fetchData():

    #setting the interval for getting historical data
    interval = '5m' 

    #get timestamp of the earliest timestamp data available 
    timestamp = client._get_earliest_valid_timestamp(cryptoSymbol, interval)

    #get candle stick data
    historialCandles = client.get_historical_klines(cryptoSymbol, interval, timestamp, limit=1000)

    #place required data in datafram
    for line in historialCandles:
        del line[5:]
    dataFrame = pd.DataFrame(historialCandles, columns=['date', 'open', 'high', 'low', 'close'])

    return dataFrame

def calculateMACD(dataFrame, fast, slow, signal):
    macdDF = pd.DataFrame()

    #calculate exponential moving average
    macdDF['Moving Average Fast'] = dataFrame['close'].ewm(span=fast, min_periods=fast).mean()
    macdDF['Moving Average Slow'] = dataFrame['close'].ewm(span=slow, min_periods=slow).mean()

    #macd
    macdDF['MACD'] = macdDF['Moving Average Fast'] - macdDF['Moving Average Slow']

    #signal
    macdDF['Signal'] = macdDF['MACD'].ewm(span=signal, min_periods= signal).mean()

    macdDF['Hist'] = macdDF['MACD'] - macdDF['Signal']
    return macdDF

def calculateRSI(dataFrame):
    rsiDF = pd.DataFrame()

    #Calculate Diff
    rsiDF['diff'] = dataFrame['price'].diff(1)

    #Calculate Gain and Loss
    rsiDF['gain'] = rsiDF['diff'].clip(lower=0).round(2)
    rsiDF['loss'] = rsiDF['diff'].clip(upper=0).abs().round(2)

    #Calculate Avg Gain and Loss
    timePeriod = 14

    rsiDF['avgGain'] = rsiDF['gain'].rolling(window=timePeriod, min_periods=timePeriod).mean()[:timePeriod+1]
    rsiDF['avgLoss'] = rsiDF['loss'].rolling(window=timePeriod, min_periods=timePeriod).mean()[:timePeriod+1]

    #Get WSM avg
    for i, row in enumerate(rsiDF['avgGain'].iloc[timePeriod+1:]):
        rsiDF['avgGain'].iloc[i + timePeriod + 1] =\
        (rsiDF['avgGain'].iloc[i + timePeriod] *
         (timePeriod - 1) +
         rsiDF['gain'].iloc[i + timePeriod + 1])\
        / timePeriod
    
    for i, row in enumerate(rsiDF['avgLoss'].iloc[timePeriod+1:]):
        rsiDF['avgLoss'].iloc[i + timePeriod + 1] =\
        (rsiDF['avgLoss'].iloc[i + timePeriod] *
         (timePeriod - 1) +
         rsiDF['loss'].iloc[i + timePeriod + 1])\
        / timePeriod

    #calculate RS value
    rsiDF['rs'] = rsiDF['avgGain'] / rsiDF['avgLoss']

    #calculate RSI
    rsiDF['rsi'] = 100 - (100 / (1.0 + rsiDF['rs']))

    return rsiDF

def computeTechnicalIndicators(dataFrame):

    macdStatus, rsiStatus = 'WAIT', 'WAIT'

    #Set index of the dataframe to date
    dataFrame.set_index('date', inplace=True)

    #Change unit to milliseconds
    dataFrame.index = pd.to_datetime(dataFrame.index, unit='ms')

    macdDF = calculateMACD(dataFrame, 12, 26, 9)
    lastHist = macdDF['Hist'].iloc[-1]
    prevHist = macdDF['Hist'].iloc[-2]

    if not np.isnan(prevHist) and not np.isnan(lastHist):
        crossover = (abs(lastHist+prevHist)) != (abs(lastHist)) + (abs(prevHist))

        if crossover:
            macdStatus = 'BUY' if lastHist > 0 else 'SELL'
            print(macdStatus)
    if macdStatus != 'WAIT':
        rsi = calculateRSI(dataFrame)
        lastRsi = rsi['rsi'].iloc[-1]

        print(rsi)

        if(lastRsi <= 30):
            rsiStatus = 'BUY'
        elif (lastRsi >= 70):
            rsiStatus = 'SELL'
    else:
        print("MACD Calculations suggest to WAIT")
    return rsiStatus

def executeTrade():


    while(1):
        dataFrame = fetchData()
        rsi = computeTechnicalIndicators(dataFrame)

        currentlyHolding = False

        if rsi == 'BUY' and not currentlyHolding:
            print("Placing BUY order")
            currentlyHolding = True
            try:
                buy_limit = client.order_market_buy(symbol='ETHUSDT', quantity=100, price=2000)
            except BinanceAPIException as e:
                # error handling goes here
                print(e)
            except BinanceOrderException as e:
                # error handling goes here
                print(e)

        elif rsi == 'SELL' and currentlyHolding:
            print("Placing SELL order")
            try:
                market_order = client.order_market_sell(symbol='ETHUSDT', quantity=100)
            except BinanceAPIException as e:
                # error handling goes here
                print(e)
            except BinanceOrderException as e:
                # error handling goes here
                print(e)
            currentlyHolding=False

        time.sleep(60*5) #interval is 5 minutes

    return

executeTrade()

