from flask import Flask, jsonify, request, g, send_file, after_this_request
import os
import pandas as pd
import tempfile
import time
import threading
import zipfile  # Импорт для создания архива
from flask_cors import CORS
from collections import OrderedDict
import subprocess

app = Flask(__name__)
# Расширенные разрешения CORS для всех источников и методов
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Middleware для логирования запросов и добавления общих данных
@app.before_request
def before_request_func():
    g.start_time = "Запрос обработан в начале"
    print(f"Запрос: {request.method} {request.path}")

# Маршрут для получения индикаторов в формате JSON
@app.route('/get_indicators_json/<symbol>/<interval>', methods=['GET'])
def get_indicators(symbol, interval):
    result_folder = f'results/{symbol}/{interval}/'
    files = [f for f in os.listdir(result_folder) if f.endswith('_indicators.csv')]

    if not files:
        return jsonify({"error": "No indicator files found"}), 404

    data = []
    volatility_data = {}

    # Обработка первого файла для извлечения данных волатильности
    for file in files:
        file_path = os.path.join(result_folder, file)
        df = pd.read_csv(file_path)

    # Проверка на наличие данных о historical volatility
    if 'historical_volatility_period' in df.columns and 'historical_volatility_value' in df.columns:
    # Сортировка данных волатильности
     sorted_volatility = df[['historical_volatility_period', 'historical_volatility_value']].dropna()
     sorted_volatility['historical_volatility_value'] = sorted_volatility['historical_volatility_value'].round(2)
     sorted_volatility = sorted_volatility.sort_values(
        by='historical_volatility_period',
        key=lambda x: x.str.extract(r'(\d+)')[0].astype(int)
    )
    
    # Формирование секции волатильности в упорядоченном виде
    volatility_data = {
        f"{symbol.replace('USDT', '')} Volatility": {
            row['historical_volatility_period']: row['historical_volatility_value']
            for _, row in sorted_volatility.iterrows()
        }
    }

    # Обработка и добавление индикаторов в JSON-структуру для анализа
    for index, row in df.iterrows():
            row_data = OrderedDict({
                "row_number": index + 1,
                "timestamp": row['timestamp'],
                "open": row['open'],
                "high": row['high'],
                "low": row['low'],
                "close": row['close'],
                "volume": row['volume'],
                "quote_asset_volume": row.get("quote_asset_volume"),
                "number_of_trades": round(row.get("number_of_trades", 0), 2),
                "taker_buy_base_asset_volume": row.get("taker_buy_base_asset_volume"),
                "open_interest": row.get("open_interest"),
                "funding_rate": row.get("funding_rate"),
                "long_short_ratio": row.get("long_short_ratio"),
                "RSI": row.get("RSI"),
                "MACD": row.get("MACD"),
                "MACD_signal": row.get("MACD_signal"),
                "MACD_hist": row.get("MACD_hist"),
                "OBV": row.get("OBV"),
                "Stochastic_k": row.get("Stochastic_k"),
                "Stochastic_d": row.get("Stochastic_d"),
                "Parabolic_SAR": row.get("Parabolic_SAR"),
                "Boillenger_Upper": row.get("Boillenger_Upper"),
                "Boillenger_Middle": row.get("Boillenger_Middle"),
                "Boillenger_Lower": row.get("Boillenger_Lower"),
                "CCI": row.get("CCI"),
                "ATR": row.get("ATR"),
                "MFI": row.get("MFI"),
                "ADX": row.get("ADX"),
                "EMA_9": row.get("EMA_9"),
                "EMA_21": row.get("EMA_21"),
                "VWAP": round(row.get("VWAP", 0), 2),
                "ROC": row.get("ROC"),
                "Doji": row.get("Doji"),
                "Engulfing": row.get("Engulfing")
            })
            data.append(row_data)

    # Ограничение вывода до 50 строк
    if len(data) > 100:
        data = data[:100]

    # Формируем ответ с секцией волатильности и данными для анализа
    response = OrderedDict()
    if volatility_data:
        response.update(volatility_data)  # Секция волатильности
    response["Data for Analysis"] = data  # Основная секция с данными для анализа

    return jsonify(response), 200

# Маршрут для получения индикаторов в формате CSV
@app.route('/get_indicators_csv/<symbol>/<interval>', methods=['GET'])
def get_indicators_csv(symbol, interval):
    num_candles = request.args.get('num_candles', default=1400, type=int)  # Получаем количество свечей, по умолчанию 1400
    result_folder = f'results/{symbol}/{interval}/'
    files = [f for f in os.listdir(result_folder) if f.endswith('_indicators.csv')]
    
    if not files:
        return jsonify({"error": "No indicator files found"}), 404
    
    # Находим файл с нужным количеством свечей
    matching_files = [f for f in files if f"{num_candles}" in f]
    
    if not matching_files:
        return jsonify({"error": f"No file found with {num_candles} candles"}), 404
    
    # Возвращаем первый файл как пример
    file_path = os.path.join(result_folder, matching_files[0])
    return send_file(file_path, mimetype='text/csv', as_attachment=True)

# ZIP ZIP ZIP    
@app.route('/get_indicators_zip/<symbol>/<interval>', methods=['GET'])
def get_indicators_zip(symbol, interval):
    num_candles = request.args.get('num_candles', default=1400, type=int)
    result_folder = f'results/{symbol}/{interval}/'
    files = [f for f in os.listdir(result_folder) if f.endswith('_indicators.csv')]
    
    if not files:
        return jsonify({"error": "No indicator files found"}), 404
    
    # Создаем временную директорию, если её нет
    temp_dir = "B:/CBTW/tmp"
    os.makedirs(temp_dir, exist_ok=True)

    zip_path = os.path.join(temp_dir, f"{symbol}_{interval}_indicators.zip")
    
    # Создаем zip-архив
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in files:
            file_path = os.path.join(result_folder, file)
            zipf.write(file_path, arcname=file)

    @after_this_request
    def remove_file(response):
        def delayed_delete():
            # Небольшая задержка, чтобы убедиться, что файл отправлен
            time.sleep(1)
            try:
                os.remove(zip_path)
            except Exception as e:
                print(f"Error deleting zip file: {e}")
        
        # Запускаем удаление в отдельном потоке
        threading.Thread(target=delayed_delete).start()
        return response

    return send_file(zip_path, mimetype='application/zip', as_attachment=True, download_name=f"{symbol}_{interval}_indicators.zip") 

# Маршрут для запуска анализа данных
@app.route('/run_data_collection/<exchange>/<symbol>/<interval>', methods=['GET'])
def run_data_collection(exchange, symbol, interval):
    num_candles = request.args.get('num_candles', default=1400, type=int)  # Default is 1400 candles
    try:
        # Adjust the script execution based on the exchange parameter
        subprocess.run([
            'C:/ProgramData/anaconda3/python.exe', 
            'B:/CBTW/crypto_analysis/data_collection.py', exchange, symbol, interval, str(num_candles)
        ], check=True)
        return jsonify({"message": f"Data collection for {symbol} on {exchange} ({interval}) started successfully"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e), "output": e.stderr}), 500
        
# Маршрут для запуска анализа данных
@app.route('/run_indicators_analysis/<symbol>/<interval>', methods=['GET'])
def run_indicators_analysis(symbol, interval):
    num_candles = request.args.get('num_candles', default=1400, type=int)  # Получаем количество свечей, по умолчанию 1500
    try:
        subprocess.run(['C:/ProgramData/anaconda3/python.exe', 
                        'B:/CBTW/crypto_analysis/indicators_analysis.py', symbol, interval, str(num_candles)], check=True)
        return jsonify({"message": f"Indicator analysis for {symbol} ({interval}) started successfully"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e), "output": e.stderr}), 500

# Новый маршрут Webhook для ChatGPT и других систем для автоматического запуска
@app.route('/webhook/run_script', methods=['POST'])
def webhook_run_script():
    try:
        data = request.get_json()
        script_name = data.get('script_name')
        symbol = data.get('symbol')
        interval = data.get('interval')

        # Получаем количество свечей из запроса, если указано
        num_candles = data.get('num_candles', 1400)  # По умолчанию 1400, если не указано

        if script_name == 'data_collection':
            subprocess.run(['C:/ProgramData/anaconda3/python.exe', 
                            'B:/CBTW/crypto_analysis/data_collection.py', symbol, interval, str(num_candles)], check=True)
        elif script_name == 'indicators_analysis':
            subprocess.run(['C:/ProgramData/anaconda3/python.exe', 
                            'B:/CBTW/crypto_analysis/indicators_analysis.py', symbol, interval, str(num_candles)], check=True)
        else:
            return jsonify({"error": "Invalid script name"}), 400

        return jsonify({"message": f"Script {script_name} for {symbol} ({interval}) started successfully"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e), "output": e.stderr}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=55555)