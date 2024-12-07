import os
import pandas as pd
import talib
import pandas_ta as ta
import sys

# Функция для расчёта индикаторов
def calculate_indicators(symbol, intervals):
    for interval in intervals:
        folder_path = f'data/{symbol}/{interval}/'
        
        if not os.path.exists(folder_path):
            print(f"Папка {folder_path} не найдена!")
            continue

        for file_name in os.listdir(folder_path):
            if file_name.startswith(f"{symbol}_{interval}") and file_name.endswith('.csv'):
                file_path = os.path.join(folder_path, file_name)

                df = pd.read_csv(file_path)
                df = df.sort_values(by='timestamp', ascending=True)

                if len(df) < 14:
                    print(f"Недостаточно данных для расчета индикаторов для {symbol} ({interval}) в файле {file_name}")
                    continue

                # Расчёт индикаторов только если они еще не существуют в DataFrame
                if 'RSI' not in df.columns:
                    df['RSI'] = talib.RSI(df['close'], timeperiod=14).round(2)
                if 'MACD' not in df.columns:
                    df['MACD'], df['MACD_signal'], df['MACD_hist'] = [x.round(2) for x in talib.MACD(df['close'])]
                if 'OBV' not in df.columns:
                    df['OBV'] = talib.OBV(df['close'], df['volume']).round(0)
                if 'Stochastic_k' not in df.columns:
                    df['Stochastic_k'], df['Stochastic_d'] = [x.round(2) for x in talib.STOCH(df['high'], df['low'], df['close'])]
                if 'Parabolic_SAR' not in df.columns:
                    df['Parabolic_SAR'] = talib.SAR(df['high'], df['low']).round(2)
                if 'Boillenger_Upper' not in df.columns:
                    df['Boillenger_Upper'], df['Boillenger_Middle'], df['Boillenger_Lower'] = [x.round(2) for x in talib.BBANDS(df['close'])]
                if 'CCI' not in df.columns:
                    df['CCI'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=14).round(2)
                if 'ATR' not in df.columns:
                    df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14).round(2)
                if 'MFI' not in df.columns:
                    df['MFI'] = talib.MFI(df['high'], df['low'], df['close'], df['volume'], timeperiod=14).round(2)
                if 'ADX' not in df.columns:
                    df['ADX'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14).round(2)
                if 'EMA_9' not in df.columns:
                    df['EMA_9'] = talib.EMA(df['close'], timeperiod=9).round(2)
                if 'EMA_21' not in df.columns:
                    df['EMA_21'] = talib.EMA(df['close'], timeperiod=21).round(2)
                if 'VWAP' not in df.columns:
                    df['VWAP'] = (df['volume'] * df['close']).cumsum() / df['volume'].cumsum()
                if 'ROC' not in df.columns:
                    df['ROC'] = talib.ROC(df['close'], timeperiod=10).round(2)
                if 'Doji' not in df.columns:
                    df['Doji'] = talib.CDLDOJI(df['open'], df['high'], df['low'], df['close'])
                if 'Engulfing' not in df.columns:
                    df['Engulfing'] = talib.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])

                # Сортировка и сохранение данных
                df = df.sort_values(by='timestamp', ascending=False)
                result_folder = f'results/{symbol}/{interval}'
                if not os.path.exists(result_folder):
                    os.makedirs(result_folder)

                num_candles = file_name.split('_')[-1].split('.')[0]
                result_file = f'{result_folder}/{symbol}_{interval}_{num_candles}_indicators.csv'
                df.to_csv(result_file, index=False)
                print(f"Результаты индикаторов для {symbol} ({interval}) успешно сохранены в {result_file}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python indicators_analysis.py <symbol> [<interval1> <interval2> ...]")
        sys.exit(1)

    symbol = sys.argv[1]  # Символ криптопары
    intervals = sys.argv[2:] if len(sys.argv) > 2 else ['15m', '1h', '4h', '1d', '1w']  # Таймфреймы
    calculate_indicators(symbol, intervals)