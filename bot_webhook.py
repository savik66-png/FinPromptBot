"""
FinPrompt Bot - Webhook version for Bothost
"""

import os
import json
import logging
from flask import Flask, request, jsonify
import requests
import config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Загружаем промпты
with open("prompts.json", "r", encoding="utf-8") as f:
    prompts = json.load(f)

# Обработчик webhook от Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        
        # Команда /start
        if text == '/start':
            menu = "\n".join([f"{i+1}. {prompts[key]['title']}" for i, key in enumerate(prompts)])
            send_message(chat_id, f"Привет! 👋\nВыбери промпт:\n{menu}")
            return jsonify({'ok': True})
        
        # Обработка выбора промпта
        if text.isdigit():
            index = int(text) - 1
            keys = list(prompts.keys())
            if 0 <= index < len(keys):
                send_message(chat_id, prompts[keys[index]]['prompt'])
                return jsonify({'ok': True})
        
        # Поиск по названию
        text_lower = text.lower()
        for key in prompts:
            if text_lower in prompts[key]['title'].lower():
                send_message(chat_id, prompts[key]['prompt'])
                return jsonify({'ok': True})
        
        # Не понял
        send_message(chat_id, "Напиши /start для списка промптов")
    
    return jsonify({'ok': True})

# Функция отправки сообщения
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        requests.post(url, json=data, timeout=5)
    except:
        pass

# Установка webhook
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = os.environ.get('WEBHOOK_URL', '') + '/webhook'
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/setWebhook"
    data = {'url': webhook_url}
    response = requests.post(url, json=data)
    return jsonify(response.json())

# Главная страница
@app.route('/')
def index():
    return "FinPrompt Bot is running!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
