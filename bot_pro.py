# -*- coding: utf-8 -*-
"""
PromptBinder — final (variant C)
- Polling via requests (no aiogram)
- Categories: icon + title — short description
- Prompts: title (clean)  <two spaces> ICON_ON_RIGHT
- Protection against duplicate icons
- PythonAnywhere friendly (Python 3.10/3.13)
"""

import os
import time
import json
import requests
import logging
import traceback
import re
from datetime import datetime

# ---------------------------
# Config
# ---------------------------
try:
    import config
except Exception:
    raise SystemExit("Create config.py with BOT_TOKEN in same folder.")

TOKEN = getattr(config, "BOT_TOKEN", None)
ADMIN_CHAT_ID = getattr(config, "ADMIN_CHAT_ID", None)
if not TOKEN:
    raise SystemExit("BOT_TOKEN missing in config.py")

URL = f"https://api.telegram.org/bot{TOKEN}/"

BASE = os.path.dirname(os.path.abspath(__file__))
PROMPTS_FILE = os.path.join(BASE, "prompts.json")
STATS_FILE = os.path.join(BASE, "stats.csv")
EVENT_LOG = os.path.join(BASE, "bot_events.log")
ERROR_LOG = os.path.join(BASE, "bot_errors.log")
SUMMARY_FILE = os.path.join(BASE, "summary.json")
DRAFTS_FILE = os.path.join(BASE, "drafts.json")

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("PromptBinder")

# ---------------------------
# Utilities
# ---------------------------
def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_read_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def safe_write_json(path, obj):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception(f"safe_write_json error: {e}")

def log_event(msg):
    try:
        with open(EVENT_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{now_ts()}] {msg}\n")
    except:
        pass

def log_error(msg):
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{now_ts()}] {msg}\n")
    except:
        logger.exception("log_error failed")

def ensure_stats_header():
    if not os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                f.write("timestamp,chat_id,event,detail,prompt\n")
        except Exception:
            log_error("cannot create stats.csv")

def append_stat(chat_id, event, detail="", prompt_key=""):
    ensure_stats_header()
    try:
        with open(STATS_FILE, "a", encoding="utf-8") as f:
            f.write(f'"{now_ts()}",{chat_id},"{event}","{detail}","{prompt_key}"\n')
    except Exception as e:
        log_error(f"append_stat error: {e}")

def save_summary(total_requests=0):
    stats_lines = 0
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                stats_lines = sum(1 for _ in f) - 1
    except:
        stats_lines = 0
    summary = {"snapshot_at": now_ts(), "stats_lines": stats_lines, "requests": total_requests}
    safe_write_json(SUMMARY_FILE, summary)

# ---------------------------
# prompts.json handling
# ---------------------------
SAMPLE = {
  "categories": [
    { "id": "creative",  "title": "Креатив",   "icon": "✨", "items": ["idea", "tagline"] },
    { "id": "marketing", "title": "Маркетинг", "icon": "📣", "items": ["ad", "product"] },
    { "id": "video",     "title": "Видео",     "icon": "🎬", "items": ["script"] },
    { "id": "content",   "title": "Контент",   "icon": "💬", "items": ["context"] },
    { "id": "crypto",    "title": "Крипто",    "icon": "🪙", "items": ["analysis", "news"] },
    { "id": "work",      "title": "Работа",    "icon": "📑", "items": ["email", "structure"] }
  ],
  "prompts": {
    "idea": {
      "title": "Идея",
      "fields": ["тема", "для кого", "цель"],
      "fields_examples": {"тема":"бот криптоньюс","для кого":"новички","цель":"собрать аудиторию"},
      "template": "Придумай идею по теме {тема} для {для кого}. Цель: {цель}."
    },
    "tagline": {
      "title": "Слоган",
      "fields": ["продукт", "стиль"],
      "fields_examples": {"продукт":"CryptoPulse","стиль":"современно"},
      "template": "Придумай 10 слоганов для {продукт} в стиле {стиль}."
    },
    "ad": {
      "title": "Реклама",
      "fields": ["продукт", "аудитория", "формат"],
      "fields_examples": {"продукт":"бот новостей","аудитория":"новички","формат":"короткий текст"},
      "template": "Создай рекламный текст для {продукт}, аудитория {аудитория}, формат {формат}."
    },
    "product": {
      "title": "Описание продукта",
      "fields": ["название", "проблема", "решение"],
      "fields_examples": {"название":"CryptoPulse","проблема":"много шума","решение":"фильтрация важного"},
      "template": "Создай описание продукта {название}. Проблема: {проблема}, решение: {решение}."
    },
    "script": {
      "title": "Сценарий",
      "fields": ["тема", "длительность"],
      "fields_examples": {"тема":"крипта 2025","длительность":"20 сек"},
      "template": "Сгенерируй сценарий на тему {тема}, длительность {длительность}."
    },
    "context": {
      "title": "Контент",
      "fields": ["тема", "стиль"],
      "fields_examples": {"тема":"обучение крипте","стиль":"простой язык"},
      "template": "Напиши контент по теме {тема} в стиле {стиль}."
    },
    "analysis": {
      "title": "Анализ монеты",
      "fields": ["монета", "период"],
      "fields_examples": {"монета":"BTC","период":"30 дней"},
      "template": "Сделай анализ монеты {монета} за период {период}."
    },
    "news": {
      "title": "Пересказ новости",
      "fields": ["новость", "стиль"],
      "fields_examples": {"новость":"вставьте текст","стиль":"кратко"},
      "template": "Перескажи новость: {новость}. Стиль: {стиль}."
    },
    "email": {
      "title": "Письмо",
      "fields": ["кому", "цель", "посыл"],
      "fields_examples": {"кому":"партнеру","цель":"сотрудничество","посыл":"совместный проект"},
      "template": "Письмо для {кому}. Цель: {цель}. Посыл: {посыл}."
    },
    "structure": {
      "title": "Структура документа",
      "fields": ["тип", "цель"],
      "fields_examples": {"тип":"презентация","цель":"продать идею"},
      "template": "Создай структуру документа {тип}, цель {цель}."
    }
  }
}

# create prompts.json if missing or invalid
if not os.path.exists(PROMPTS_FILE):
    safe_write_json(PROMPTS_FILE, SAMPLE)
    PROMPTS_RAW = SAMPLE
    log_event("prompts.json not found → sample created")
else:
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            PROMPTS_RAW = json.load(f)
    except Exception as e:
        log_error(f"prompts.json parse error: {e} — recreating sample")
        safe_write_json(PROMPTS_FILE, SAMPLE)
        PROMPTS_RAW = SAMPLE

CATEGORIES = PROMPTS_RAW.get("categories", [])[:6]
PROMPTS = PROMPTS_RAW.get("prompts", {})

# pad categories to 6 if less
while len(CATEGORIES) < 6:
    CATEGORIES.append({"id": f"more{len(CATEGORIES)+1}", "title": "Другие", "icon": "➕", "items": []})

# ---------------------------
# Icon maps
# ---------------------------
# prompt_icons: icon to show on the RIGHT of item button (small visual)
PROMPT_ICONS = {
    "idea": "💡",
    "tagline": "✍️",
    "ad": "📢",
    "product": "📦",
    "script": "🎞️",
    "context": "💬",
    "analysis": "📊",
    "news": "📰",
    "email": "✉️",
    "structure": "🧱"
}

# category short description (appears in button)
CATEGORY_DESC = {
    "creative": "идеи, слоганы",
    "marketing": "реклама, офферы",
    "video": "сценарии, ролики",
    "content": "посты, упрощение",
    "crypto": "монеты, новости",
    "work": "письма, структура"
}

# ---------------------------
# Helpers re icons / cleaning
# ---------------------------
def starts_with_icon(s, icon):
    if not s or not icon:
        return False
    s = s.strip()
    return s.startswith(icon) or s.startswith(icon + " ")

def strip_leading_icon(s):
    if not s:
        return s
    s = s.strip()
    # if first char(s) look like an emoji + space, remove them
    # heuristic: non-alnum + space
    if len(s) >= 2 and (not s[0].isalnum()) and s[1] == " ":
        return s[2:].strip()
    return s

# build category button label (icon left) with protection from duplicates
for c in CATEGORIES:
    icon = (c.get("icon") or "").strip()
    title = (c.get("title") or "").strip()
    title_clean = strip_leading_icon(title)
    desc = CATEGORY_DESC.get(c.get("id",""), "").strip()
    if icon and not starts_with_icon(title, icon):
        base = f"{icon} {title_clean}"
    else:
        base = title_clean
    if desc:
        c["button"] = f"{base} — {desc}"
    else:
        c["button"] = base

# ---------------------------
# Keyboards (dicts)
# ---------------------------
def kb_categories():
    kb = {"keyboard": [], "resize_keyboard": True, "one_time_keyboard": False}
    for c in CATEGORIES:
        kb["keyboard"].append([{"text": c["button"]}])
    kb["keyboard"].append([{"text": "❓ Что может бот"}])
    return kb

def kb_items(cat_id):
    kb = {"keyboard": [], "resize_keyboard": True, "one_time_keyboard": False}
    cat = next((x for x in CATEGORIES if x.get("id")==cat_id or x.get("button")==cat_id or x.get("title")==cat_id), None)
    if not cat:
        kb["keyboard"].append([{"text":"⬅️ Назад"}, {"text":"🏠 Домой"}])
        return kb
    items = cat.get("items", [])[:6]
    row = []
    for key in items:
        p = PROMPTS.get(key)
        if not p:
            continue
        title = strip_leading_icon(p.get("title",""))
        icon_right = PROMPT_ICONS.get(key, "")
        # add two spaces before right icon to separate visually
        btn = f"{title}{'  ' + icon_right if icon_right else ''}"
        row.append({"text": btn})
        if len(row) == 2:
            kb["keyboard"].append(row)
            row = []
    if row:
        kb["keyboard"].append(row)
    kb["keyboard"].append([{"text":"⬅️ Назад"}, {"text":"🏠 Домой"}])
    return kb

def kb_cancel():
    return {"keyboard":[[{"text":"❌ Отмена"}]], "resize_keyboard": True, "one_time_keyboard": False}

def inline_copy_kb():
    return {"inline_keyboard":[[{"text":"📋 Скопировать промпт","callback_data":"copy_prompt"}]]}

# ---------------------------
# State
# ---------------------------
USERS = {}  # chat_id -> state dict
DRAFTS = safe_read_json(DRAFTS_FILE) if os.path.exists(DRAFTS_FILE) else {}

def save_drafts():
    safe_write_json(DRAFTS_FILE, DRAFTS)

# ---------------------------
# Telegram helpers
# ---------------------------
def post(method, payload, timeout=12):
    try:
        return requests.post(URL + method, json=payload, timeout=timeout)
    except Exception as e:
        log_error(f"post error {method}: {e}")
        return None

def send_message(chat_id, text, reply_markup=None, remove_keyboard=False):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if remove_keyboard:
        payload["reply_markup"] = {"remove_keyboard": True}
    elif reply_markup is not None:
        payload["reply_markup"] = reply_markup
    r = post("sendMessage", payload)
    if r is None:
        append_stat(chat_id, "send_fail", text[:80])
        return None
    try:
        j = r.json()
        if not j.get("ok"):
            log_error(f"sendMessage not ok: {r.text if hasattr(r,'text') else j}")
        append_stat(chat_id, "send_ok", text[:80])
        return j
    except Exception as e:
        log_error(f"send_message parse error: {e}")
        return None

def answer_callback(cb_id, text=None):
    payload = {"callback_query_id": cb_id}
    if text:
        payload["text"] = text
    try:
        requests.post(URL + "answerCallbackQuery", json=payload, timeout=8)
    except Exception as e:
        log_error(f"answer_callback error: {e}")

# ---------------------------
# Processing logic
# ---------------------------
def start_chat(chat_id):
    send_message(chat_id, "<b>👋 PromptBinder</b>\nВыберите категорию:", kb_categories())
    append_stat(chat_id, "start", "")

def help_chat(chat_id):
    txt = ("<b>Что умеет PromptBinder</b>\n\n"
           "• Быстро формирует промпты по шаблонам\n"
           "• Категории → выбор задачи → ввод полей → готовый промпт\n\n"
           "Команды: /start /help /cancel")
    send_message(chat_id, txt, kb_categories())
    append_stat(chat_id, "help", "")

def open_category(chat_id, label):
    # match by button or title
    cat = None
    for c in CATEGORIES:
        if label == c.get("button") or label == c.get("title"):
            cat = c; break
    if not cat:
        # also try matching by icon+title
        for c in CATEGORIES:
            alt = f"{c.get('icon','')} {c.get('title')}".strip()
            if label == alt:
                cat = c; break
    if not cat:
        send_message(chat_id, "Не удалось найти категорию. Возврат в меню.", kb_categories())
        return
    send_message(chat_id, f"<b>{cat.get('title')}</b>\nВыберите задачу:", kb_items(cat.get("id")))
    append_stat(chat_id, "open_category", cat.get("id"))

def start_prompt_flow(chat_id, key):
    p = PROMPTS.get(key)
    if not p:
        send_message(chat_id, "Промпт не найден.", kb_categories())
        return
    fields = p.get("fields", []) or []
    USERS[chat_id] = {"state":"filling","prompt_key":key,"fields":fields,"index":0,"data":{}}
    if fields:
        first = fields[0]
        ex = p.get("fields_examples", {}).get(first, "")
        hint = f"\n<i>пример: {ex}</i>" if ex else ""
        send_message(chat_id, f"Введите <b>{first}</b>:{hint}", kb_cancel())
        append_stat(chat_id, "start_prompt", key)
    else:
        template = p.get("template","")
        out = re.sub(r"\{[^}]+\}","",template)
        send_message(chat_id, f"<b>✨ Готово</b>\n<code>{out}</code>", inline_copy_kb(), remove_keyboard=True)
        append_stat(chat_id, "prompt_generated", key)

def finish_prompt(chat_id):
    st = USERS.get(chat_id)
    if not st:
        send_message(chat_id, "Нет активного запроса. /start", kb_categories())
        return
    key = st["prompt_key"]
    p = PROMPTS.get(key, {})
    template = p.get("template","")
    out = template
    for k,v in st.get("data",{}).items():
        out = out.replace("{" + k + "}", v)
    out = re.sub(r"\{[^}]+\}","",out)
    send_message(chat_id, f"<b>✨ Ваш промпт</b>\n\n<code>{out}</code>", inline_copy_kb(), remove_keyboard=True)
    append_stat(chat_id, "prompt_generated", key)
    try:
        del USERS[chat_id]
    except:
        pass
    time.sleep(0.6)
    send_message(chat_id, "Выберите категорию:", kb_categories())

def process_text(chat_id, text):
    text = (text or "").strip()
    append_stat(chat_id, "recv", text[:120])

    # commands
    if text == "/start":
        start_chat(chat_id); return
    if text == "/help" or text == "❓ Что может бот":
        help_chat(chat_id); return
    if text in ("🏠 Домой", "Домой"):
        USERS.pop(chat_id, None); start_chat(chat_id); return
    if text in ("⬅️ Назад", "/back"):
        USERS.pop(chat_id, None); start_chat(chat_id); return
    if text in ("❌ Отмена", "/cancel"):
        USERS.pop(chat_id, None); send_message(chat_id, "Отменено.", kb_categories()); return
    if text == "/export_stats":
        if ADMIN_CHAT_ID and str(chat_id) == str(ADMIN_CHAT_ID):
            if os.path.exists(STATS_FILE):
                try:
                    with open(STATS_FILE, "rb") as f:
                        files = {"document": f}
                        requests.post(URL + "sendDocument", data={"chat_id": chat_id}, files=files, timeout=30)
                except Exception as e:
                    log_error(f"export error: {e}")
            else:
                send_message(chat_id, "Нет stats.csv")
        else:
            send_message(chat_id, "Команда доступна админу.")
        return

    # filling
    if chat_id in USERS and USERS[chat_id].get("state") == "filling":
        st = USERS[chat_id]
        idx = st["index"]
        fields = st["fields"]
        key = st["prompt_key"]
        if idx < len(fields):
            fld = fields[idx]
            st["data"][fld] = text
            DRAFTS[str(chat_id)] = {"prompt": key, "data": st["data"]}
            save_drafts()
            st["index"] = idx + 1
            append_stat(chat_id, "field", f"{fld}={text}", key)
            if st["index"] >= len(fields):
                finish_prompt(chat_id); return
            else:
                nextf = fields[st["index"]]
                ex = PROMPTS.get(key, {}).get("fields_examples", {}).get(nextf, "")
                hint = f"\n<i>пример: {ex}</i>" if ex else ""
                send_message(chat_id, f"Введите <b>{nextf}</b>:{hint}", kb_cancel())
                return

    # category click
    for c in CATEGORIES:
        if text == c.get("button") or text == c.get("title"):
            open_category(chat_id, text); return

    # item click matching (with right-side icon) - ИСПРАВЛЕННЫЙ БЛОК
    for key, p in PROMPTS.items():
        title_clean = strip_leading_icon(p.get("title", "")) or ""
        icon_right = PROMPT_ICONS.get(key, "")
        btn_text = f"{title_clean}{'  ' + icon_right if icon_right else ''}"

        # exact match with button (with icon)
        if text == btn_text:
            start_prompt_flow(chat_id, key)
            return

        # fallback: match without icon
        if text == title_clean or text.lower() == title_clean.lower():
            start_prompt_flow(chat_id, key)
            return

    # numeric map 1..6
    if text.isdigit():
        n = int(text)
        if 1 <= n <= len(CATEGORIES):
            c = CATEGORIES[n-1]
            open_category(chat_id, c.get("button"))
            return

    # fallback
    lang = "ru" if re.search(r"[а-яА-Я]", text) else "en"
    ask = "Выберите категорию из меню 👇" if lang=="ru" else "Please choose a category 👇"
    send_message(chat_id, ask, kb_categories())
# ---------------------------
# Callback processing
# ---------------------------
_last_cb = None
def process_callback(cb):
    global _last_cb
    cid = cb.get("id")
    data = cb.get("data")
    message = cb.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    # debounce
    key = f"{chat_id}:{data}"
    if key == _last_cb:
        answer_callback(cid)
        return
    _last_cb = key
    answer_callback(cid)
    if data == "copy_prompt":
        send_message(chat_id, "📋 Чтобы скопировать — выделите текст и нажмите «Копировать»", kb_categories())
        append_stat(chat_id, "copy", "")

# ---------------------------
# Polling loop
# ---------------------------
def polling():
    offset = 0
    last_ok = time.time()
    req_counter = 0
    log_event("polling_start")
    while True:
        try:
            r = requests.get(URL + "getUpdates", params={"offset": offset, "timeout": 20, "allowed_updates": ["message","callback_query"]}, timeout=30)
            req_counter += 1
            if r.status_code != 200:
                log_error(f"getUpdates status {r.status_code}")
                time.sleep(2)
                continue
            data = r.json()
            if not data.get("ok"):
                log_error(f"getUpdates ok=false: {data}")
                time.sleep(2); continue
            results = data.get("result", [])
            if results:
                last_ok = time.time()
            for upd in results:
                offset = upd["update_id"] + 1
                if "message" in upd:
                    m = upd["message"]
                    chat_id = m.get("chat", {}).get("id")
                    text = m.get("text","")
                    try:
                        process_text(chat_id, text)
                    except Exception as e:
                        log_error(f"process_text error: {e}\n{traceback.format_exc()}")
                elif "callback_query" in upd:
                    try:
                        process_callback(upd["callback_query"])
                    except Exception as e:
                        log_error(f"callback error: {e}\n{traceback.format_exc()}")
            # anti-freeze
            if time.time() - last_ok > 120:
                save_summary(req_counter)
                log_error("No updates >120s — restarting polling")
                raise Exception("poll_freeze")
            if req_counter >= 100:
                save_summary(req_counter)
                req_counter = 0
            time.sleep(0.25)
        except KeyboardInterrupt:
            log_event("stopped_by_keyboard")
            break
        except Exception as e:
            log_error(f"poll loop error: {e}\n{traceback.format_exc()}")
            time.sleep(5)
            continue
    log_event("polling_end")

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    ensure_stats_header()
    log_event("bot_launch_variantC")
    logger.warning("PromptBinder (variant C) starting")
    polling()
