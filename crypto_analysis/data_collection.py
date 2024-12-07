import os
import pandas as pd
import requests
import json
import sys
import time
import hmac
import numpy as np
from hashlib import sha256
from binance.client import Client
from pybit.unified_trading import HTTP
from datetime import datetime, timedelta

# API Keys
BINANCE_API_KEY = 'qmhqtiWeTKeNhN8enxajJKZdzDiBhUHiDdWhYwYb57PPAmYzy5wltiFUOpdtb3tw'
BINANCE_API_SECRET = 'ErptSQRHF11UxrORzBqatLGXpZZJmljOOQgNHKQoP22L3k59Vs5z38Xtajy1HKo7'
BINGX_API_KEY = 'n6flaOsL4nt0QHrSzRHbl5fuWnBWH6U428caSFJTxOKFL7sCIZB3ql7vcBJMbIQ1LZZ95lNQOCBYK3olZxw'
BINGX_SECRET_KEY = 'nwOYkI1KaQTraGKbV7gfV66EoOUZYItF8cYptI7LuVXGPtX9O9JM03Stg7DOBvo4webWlseSZZDtUTuXUz8A'
BYBIT_API_KEY = '25eURVXtg49Ce264bq'

# API URLs
BINGX_API_URL = 'https://open-api.bingx.com'
BYBIT_API_URL = 'https://api.bybit.com'

# Создаём сессию для соединения с ByBit API
session = HTTP()

# Initialize Binance Client
try:
    binance_client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
except Exception as e:
    print(f"Error initializing Binance client: {e}")
    sys.exit(1)

# Function to generate HMAC SHA256 signature
def generate_signature(secret_key, query_string):
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), sha256).hexdigest()

# Function to create a query string for BingX and add timestamp
def create_query_string(params):
    sorted_keys = sorted(params.keys())
    query_string = "&".join(f"{key}={params[key]}" for key in sorted_keys)
    return query_string + f"&timestamp={int(time.time() * 1000)}"

# Binance Kline Data Function with dynamic column assignment
def get_binance_kline_data(symbol, interval, num_candles):
    try:
        candles = binance_client.get_historical_klines(symbol, interval, limit=num_candles)
        if not candles:
            return pd.DataFrame()

        # Create DataFrame with the exact number of columns returned by Binance API
        df = pd.DataFrame(candles)
        
        # Define expected column names up to the maximum possible fields
        expected_columns = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore1', 'ignore2'
        ]
        
        # Assign column names dynamically based on the number of columns in `df`
        df.columns = expected_columns[:df.shape[1]]
        
        # Convert timestamp to datetime and filter to the columns we need
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                   'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume']]
    except Exception as e:
        print(f"Error fetching Binance data: {e}")
        return pd.DataFrame()

# BingX Kline Data Function with Signature
def get_bingx_kline_data(symbol, interval, num_candles):
    try:
        formatted_symbol = symbol.replace("USDT", "-USDT")
        
        # Required parameters for BingX API request
        params = {
            "symbol": formatted_symbol,
            "interval": interval,
            "limit": num_candles
        }

        # Create the query string and generate the signature
        query_string = create_query_string(params)
        signature = generate_signature(BINGX_SECRET_KEY, query_string)

        # Final URL with query string and signature
        url = f"{BINGX_API_URL}/openApi/swap/v3/quote/klines?{query_string}&signature={signature}"

        # Headers with API key
        headers = {
            'X-BX-APIKEY': BINGX_API_KEY,
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                df = pd.DataFrame(data['data'], columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
                return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        print(f"Unexpected response for BingX Kline: {response.text}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching BingX Kline data: {e}")
        return pd.DataFrame()
        
# BingX Open Interest Data Function
def get_bingx_open_interest(symbol):
    try:
        formatted_symbol = symbol.replace("USDT", "-USDT")
        params = {'symbol': formatted_symbol}
        response = requests.get(f"{BINGX_API_URL}/openApi/swap/v2/quote/openInterest", params=params)
        
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame([data], columns=['openInterest', 'time'])
            df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
            return df[['timestamp', 'openInterest']]
        print(f"Unexpected response for BingX Open Interest: {response.text}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching BingX Open Interest: {e}")
        return pd.DataFrame()

# BingX Funding Rate Data Function
def get_bingx_funding_rate(symbol, num_records=100):
    try:
        formatted_symbol = symbol.replace("USDT", "-USDT")
        params = {
            'symbol': formatted_symbol,
            'limit': num_records,
            'timestamp': int(time.time() * 1000)
        }
        response = requests.get(f"{BINGX_API_URL}/openApi/swap/v2/quote/fundingRate", params=params)

        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                df = pd.DataFrame(data['data'], columns=['fundingRate', 'fundingTime'])
                df['timestamp'] = pd.to_datetime(df['fundingTime'], unit='ms')
                return df[['timestamp', 'fundingRate']]
        print(f"Unexpected response for BingX Funding Rate: {response.text}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching BingX Funding Rate: {e}")
        return pd.DataFrame()
 
# Convert interval to ByBit-compatible format
def convert_interval_to_bybit_format(interval):
    interval_map = {
        "15m": "15",
        "1h": "60",
        "4h": "240",
        "1d": "D",
        "1w": "W"
    }
    return interval_map.get(interval, interval)  # Возвращает интервал, если он не в маппинге

# ByBit Kline Data Function with adjusted timestamp conversion
def get_bybit_kline_data(symbol, interval, num_candles, category="linear"):
    try:
        # Конвертируем интервал в формат ByBit
        bybit_interval = convert_interval_to_bybit_format(interval)
        
        params = {
            'category': category,  # Использует 'linear' по умолчанию
            'symbol': symbol,
            'interval': bybit_interval,
            'limit': min(num_candles, 1000)  # Устанавливаем limit, максимум 1000
        }
        response = requests.get(f"{BYBIT_API_URL}/v5/market/kline", params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("retCode") == 0 and "result" in data and "list" in data["result"]:
                candles = data["result"]["list"]
                
                # Создаем DataFrame и задаем правильные названия колонок
                df = pd.DataFrame(candles, columns=[
                    'startTime', 'openPrice', 'highPrice', 'lowPrice', 'closePrice', 'volume', 'turnover'
                ])
                
                # Преобразуем startTime с помощью int(float(value)) для избегания ошибки
                df['timestamp'] = pd.to_datetime(df['startTime'].apply(lambda x: int(float(x))), unit='ms')
                
                # Переименовываем столбцы в соответствии с нашими стандартами
                df.rename(columns={
                    'openPrice': 'open', 
                    'highPrice': 'high', 
                    'lowPrice': 'low', 
                    'closePrice': 'close'
                }, inplace=True)
                
                # Возвращаем только необходимые столбцы
                return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        else:
            print(f"Unexpected response for ByBit Kline: {response.text}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching ByBit Kline data: {e}")
        return pd.DataFrame()

# ByBit Open Interest Data Function
def get_bybit_open_interest(symbol, interval="1h", limit=200):
    try:
        params = {
            'category': 'linear',
            'symbol': symbol,
            'intervalTime': interval,
            'limit': min(limit, 200)
        }
        response = requests.get(f"{BYBIT_API_URL}/v5/market/open-interest", params=params)

        # Проверка успешного получения данных
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'list' in data['result']:
                # Извлекаем данные из 'list' внутри 'result'
                df = pd.DataFrame(data['result']['list'], columns=['openInterest', 'timestamp'])
                
                # Преобразование 'timestamp' через float для избегания ошибок с большими значениями
                df['timestamp'] = pd.to_datetime(df['timestamp'].apply(lambda x: int(float(x))), unit='ms')
                
                # print("Первые строки DataFrame с данными по Open Interest:")
                # print(df.head())  # Проверка первых строк
                return df[['timestamp', 'openInterest']]
            else:
                print("No open interest data available for symbol:", symbol)
        else:
            print(f"Unexpected response for ByBit Open Interest: {response.text}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching ByBit Open Interest: {e}")
        return pd.DataFrame()

# ByBit Funding Rate Data Function with detailed response output
def get_bybit_funding_rate(symbol, limit=200):
    try:
        # Запрос истории funding rate
        response = session.get_funding_rate_history(
            category="linear",
            symbol=symbol,
            limit=limit,
        )
        
        # Проверяем успешность ответа
        if response.get("retCode") == 0:
            data = response.get("result", {}).get("list", [])
            if data:
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['fundingRateTimestamp'].apply(lambda x: int(float(x))), unit='ms')
                df.rename(columns={'fundingRate': 'funding_rate'}, inplace=True)
                return df[['timestamp', 'funding_rate']]
            else:
                print("No funding rate data available.")
                return pd.DataFrame()
        else:
            print("Error in response:", response.get("retMsg"))
            return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching ByBit Funding Rate: {e}")
        return pd.DataFrame()  

# ByBit Long-Short Ratio Data Function
def get_bybit_long_short_ratio(symbol, period="1h", limit=500):
    try:
        params = {
            'category': 'linear',
            'symbol': symbol,
            'period': period,
            'limit': min(limit, 500)  # Устанавливаем лимит до 500 записей
        }
        response = requests.get(f"{BYBIT_API_URL}/v5/market/account-ratio", params=params)

        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'list' in data['result']:
                df = pd.DataFrame(data['result']['list'], columns=['timestamp', 'buyRatio', 'sellRatio'])
                
                # Преобразуем timestamp для корректного отображения
                df['timestamp'] = pd.to_datetime(df['timestamp'].apply(lambda x: int(float(x))), unit='ms')
                
                # Рассчитываем long_short_ratio с округлением до 3 знаков
                df['long_short_ratio'] = (df['buyRatio'].astype(float) / df['sellRatio'].astype(float)).round(3)
                
                return df[['timestamp', 'long_short_ratio']]
            else:
                print("No long-short ratio data available for symbol:", symbol)
        else:
            print(f"Unexpected response for ByBit Long-Short Ratio: {response.text}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching ByBit Long-Short Ratio: {e}")
        return pd.DataFrame()

# ByBit Historical Volatility Data Function
def get_bybit_historical_volatility(symbol, periods=[7, 14, 21, 30, 60, 90, 180, 270]):
    volatility_data = []
    
    # Извлекаем базовое название монеты, убирая любые суффиксы типа USDT/USDC
    if symbol.endswith("USDT"):
        base_coin = symbol[:-4]  # Убираем последние 4 символа для USDT
    elif symbol.endswith("USDC"):
        base_coin = symbol[:-4]  # Убираем последние 4 символа для USDC
    else:
        base_coin = symbol  # Если нет суффиксов, оставляем как есть

    # Печать для проверки (можно убрать при окончательной отладке)
    print(f"Base Coin extracted: {base_coin}")

    for period in periods:  
        try:
            params = {
                'category': 'option',
                'baseCoin': base_coin,
                'period': period
            }
            response = requests.get(f"{BYBIT_API_URL}/v5/market/historical-volatility", params=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and data['result']:
                    for item in data['result']:
                        volatility_data.append({
                            'historical_volatility_period': f"{period} days",
                            'historical_volatility_value': item['value']
                        })
            else:
                print(f"No data available for period {period} days for {symbol}")
        except Exception as e:
            print(f"Error fetching historical volatility for period {period} days: {e}")

    return pd.DataFrame(volatility_data)

def save_combined_data(exchange, symbol, interval, num_candles):
    # Получение данных по Kline
    kline_data = None
    if exchange.lower() == 'binance':
        kline_data = get_binance_kline_data(symbol, interval, num_candles)
        kline_data = kline_data.sort_values(by='timestamp', ascending=False).reset_index(drop=True)  # Сортировка от последней к первой
    elif exchange.lower() == 'bingx':
        kline_data = get_bingx_kline_data(symbol, interval, num_candles)
    elif exchange.lower() == 'bybit':
        kline_data = get_bybit_kline_data(symbol, interval, num_candles)
    else:
        print(f"Exchange {exchange} is not supported.")
        return None

    if kline_data.empty:
        print(f"No Kline data available for {symbol} ({interval}) on {exchange}.")
        return None

    # Проверка и добавление данных с Binance, избегая дублирования колонок
    binance_data = get_binance_kline_data(symbol, interval, num_candles)
    if not binance_data.empty:
        columns_to_merge = {}
        if 'quote_asset_volume' in binance_data.columns and 'quote_asset_volume' not in kline_data.columns:
            columns_to_merge['quote_asset_volume'] = binance_data['quote_asset_volume']
        if 'number_of_trades' in binance_data.columns and 'number_of_trades' not in kline_data.columns:
            columns_to_merge['number_of_trades'] = binance_data['number_of_trades']
        if 'taker_buy_base_asset_volume' in binance_data.columns and 'taker_buy_base_asset_volume' not in kline_data.columns:
            columns_to_merge['taker_buy_base_asset_volume'] = binance_data['taker_buy_base_asset_volume']
        
        if columns_to_merge:
            kline_data = pd.concat([kline_data, pd.DataFrame(columns_to_merge)], axis=1)

    # Получение данных Open Interest с приоритетом ByBit, проверка на пустоту
    open_interest_data = get_bybit_open_interest(symbol, interval)
    if open_interest_data.empty:
        open_interest_data = get_bingx_open_interest(symbol)
    if not open_interest_data.empty:
        kline_data = pd.merge(kline_data, open_interest_data.rename(columns={'openInterest': 'open_interest'}), on='timestamp', how='left')

    # Получение данных Funding Rate с приоритетом ByBit, проверка на пустоту
    funding_rate_data = get_bybit_funding_rate(symbol)
    if funding_rate_data.empty:
        funding_rate_data = get_bingx_funding_rate(symbol)
    if not funding_rate_data.empty:
        kline_data = pd.merge(kline_data, funding_rate_data.rename(columns={'fundingRate': 'funding_rate'}), on='timestamp', how='left')
    
    # Получение данных Long-Short Ratio и проверка перед слиянием
    long_short_ratio_data = get_bybit_long_short_ratio(symbol)
    if not long_short_ratio_data.empty:
        kline_data = pd.merge(kline_data, long_short_ratio_data.rename(columns={'long_short_ratio': 'long_short_ratio'}), on='timestamp', how='left')
    
    # Получение данных Historical Volatility и проверка на пустоту
    historical_volatility_data = get_bybit_historical_volatility(symbol)
    if not historical_volatility_data.empty:
        # Добавление данных по волатильности в основной DataFrame
        kline_data = pd.concat([kline_data, historical_volatility_data], axis=1)
    else:
        print(f"No historical volatility data available for {symbol}")

    # Форматирование timestamp перед сохранением в CSV
    kline_data['timestamp'] = pd.to_datetime(kline_data['timestamp'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    # Сохранение данных в CSV
    folder_path = f"data/{symbol}/{interval}"
    os.makedirs(folder_path, exist_ok=True)
    csv_file = f"{folder_path}/{symbol}_{interval}_{num_candles}.csv"
    kline_data.to_csv(csv_file, index=False)
    print(f"Data saved to {csv_file}")

# Main execution
if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python data_collection.py <exchange> <symbol> <interval> <num_candles>")
        sys.exit(1)

    exchange = sys.argv[1]
    symbol = sys.argv[2]
    interval = sys.argv[3]
    num_candles = int(sys.argv[4]) if sys.argv[4].isdigit() else 1000

    save_combined_data(exchange, symbol, interval, num_candles)