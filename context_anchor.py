"""
КОНТЕКСТНЫЙ ЯКОРЬ для отслеживания состояний
"""

# Глобальный словарь для хранения последних сообщений
last_messages = {}

def save_message_info(user_id, message_type, message_id, keyboard=None):
    """Сохранить информацию о последнем сообщении"""
    if user_id not in last_messages:
        last_messages[user_id] = {}
    
    last_messages[user_id][message_type] = {
        'message_id': message_id,
        'keyboard': keyboard,
        'timestamp': time.time()
    }

def get_last_message_info(user_id, message_type):
    """Получить информацию о последнем сообщении"""
    if user_id in last_messages and message_type in last_messages[user_id]:
        return last_messages[user_id][message_type]
    return None

def clear_user_messages(user_id):
    """Очистить все сообщения пользователя"""
    if user_id in last_messages:
        del last_messages[user_id]

def should_show_message(user_id, message_type, cooldown_seconds=2):
    """Проверить, можно ли показывать сообщение (защита от дублирования)"""
    last_info = get_last_message_info(user_id, message_type)
    
    if not last_info:
        return True
    
    current_time = time.time()
    time_diff = current_time - last_info['timestamp']
    
    # Если прошло меньше cooldown_seconds секунд - не показываем
    if time_diff < cooldown_seconds:
        return False
    
    return True

# Импортируем time
import time
