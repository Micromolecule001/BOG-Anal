import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_BASE_URL = 'https://09b3-91-210-248-211.ngrok-free.app'

# Middleware для обработки запросов от ChatGPT и пересылки на основной сервер API
@app.route('/middleware/<path:path>', methods=['GET', 'POST'])
def middleware(path):
    full_url = f"{API_BASE_URL}/{path}"
    
    # Логи запросов от ChatGPT
    print(f"Received request: {request.method} {request.url}")
    
    try:
        # Передача GET-запросов на основной сервер API
        if request.method == 'GET':
            response = requests.get(full_url, params=request.args)
        else:
            response = requests.post(full_url, data=request.form)
        
        response.raise_for_status()  # Проверка успешности запроса
        return jsonify(response.json()), response.status_code
    
    except requests.exceptions.RequestException as e:
        # Логирование ошибки и возврат сообщения об ошибке
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=55556)