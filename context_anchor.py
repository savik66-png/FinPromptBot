"""
КОНТЕКСТНЫЙ ЯКОРЬ - ИСТОРИЯ НАШЕГО ЧАТА
Создан на основе обсуждения миграции с PythonAnywhere на Bothost

История:
1. Бот изначально работал на PythonAnywhere (polling бот)
2. Создавали версию с вебхуком (bot_webhook.py) для Bothost
3. Оказалось, что на Bothost работает polling версия (bot_pro.py)
4. Были проблемы с дублированием кнопок и сообщений
5. Решили оставить polling версию, но добавить защиту от дублирования

Текущий статус: Бот работает на Bothost, использует bot_pro.py (polling)
"""

import time
import json
import os
from datetime import datetime

class ChatHistory:
    """Хранит историю взаимодействий с пользователем"""
    
    def __init__(self):
        self.history_file = "chat_history.json"
        self.user_states = {}
        self.message_tracker = {}
        self.load_history()
    
    def load_history(self):
        """Загружает историю из файла"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_states = data.get('user_states', {})
                    self.message_tracker = data.get('message_tracker', {})
            except:
                self.user_states = {}
                self.message_tracker = {}
    
    def save_history(self):
        """Сохраняет историю в файл"""
        try:
            data = {
                'user_states': self.user_states,
                'message_tracker': self.message_tracker,
                'last_update': datetime.now().isoformat()
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def track_message(self, user_id, message_type, message_id=None):
        """Отслеживает отправленное сообщение"""
        key = f"{user_id}_{message_type}"
        current_time = time.time()
        
        # Проверяем, не отправляли ли уже такое сообщение
        if key in self.message_tracker:
            last_time = self.message_tracker[key].get('timestamp', 0)
            # Если прошло меньше 2 секунд - считаем дубликатом
            if current_time - last_time < 2:
                return False
        
        # Сохраняем новое сообщение
        self.message_tracker[key] = {
            'timestamp': current_time,
            'message_id': message_id,
            'type': message_type
        }
        
        # Автосохранение каждые 10 записей
        if len(self.message_tracker) % 10 == 0:
            self.save_history()
        
        return True
    
    def get_user_state(self, user_id):
        """Получает состояние пользователя"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                'last_action': time.time(),
                'current_category': None,
                'current_prompt': None,
                'message_count': 0,
                'last_keyboard': None,
                'created_at': datetime.now().isoformat()
            }
        return self.user_states[user_id]
    
    def update_user_state(self, user_id, **kwargs):
        """Обновляет состояние пользователя"""
        state = self.get_user_state(user_id)
        state.update(kwargs)
        state['last_action'] = time.time()
        state['message_count'] = state.get('message_count', 0) + 1
        self.user_states[user_id] = state
    
    def clear_user_state(self, user_id):
        """Очищает состояние пользователя"""
        if user_id in self.user_states:
            # Сохраняем статистику перед очисткой
            stats = {
                'total_messages': self.user_states[user_id].get('message_count', 0),
                'last_session': datetime.now().isoformat()
            }
            # Очищаем текущее состояние, но оставляем статистику
            self.user_states[user_id] = {
                'last_action': time.time(),
                'current_category': None,
                'current_prompt': None,
                'message_count': stats['total_messages'],
                'last_keyboard': None,
                'stats': stats
            }
    
    def get_chat_summary(self):
        """Возвращает статистику чата"""
        total_users = len(self.user_states)
        total_messages = sum(state.get('message_count', 0) for state in self.user_states.values())
        
        return {
            'total_users': total_users,
            'total_messages': total_messages,
            'active_sessions': len([uid for uid, state in self.user_states.items() 
                                  if time.time() - state.get('last_action', 0) < 3600]),
            'last_update': datetime.now().isoformat()
        }

# Глобальный экземпляр якоря
anchor = ChatHistory()

# Функция для автосохранения при завершении
import atexit
atexit.register(anchor.save_history)
