"""
AI Библиотекарь – Сеченовский Университет
Краткие, но содержательные ответы + мультиязычность + перевод истории
"""

import os
import re
import html
import requests
from typing import Optional, List, Dict
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# === Настройки ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not GROQ_API_KEY or not SERPER_API_KEY:
    raise ValueError("❌ Укажи GROQ_API_KEY и SERPER_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"
SERPER_URL = "https://google.serper.dev/search"

with open("knowledge_base.txt", "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = f.read()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_LANGS = {"ru": "русский", "en": "английский", "zh": "китайский"}

def clean_text(text: str) -> str:
    if not text: return ""
    text = html.unescape(text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_with_groq(prompt: str, max_tokens: int = 550) -> str:
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": max_tokens
    }
    try:
        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        return clean_text(r.json()["choices"][0]["message"]["content"].strip())
    except Exception as e:
        print(f"Groq error: {e}")
        return "⚠️ Ошибка. Позвоните +7(499) 246-05-97."

def get_section(header: str) -> str:
    lines = KNOWLEDGE_BASE.split('\n')
    in_section = False
    result = []
    for line in lines:
        if header in line:
            in_section = True
            result.append(line)
        elif in_section:
            if line.startswith("==="): break
            if line.strip(): result.append(line)
    return '\n'.join(result)

def find_context(query: str) -> Optional[str]:
    q = query.lower()
    # Режим работы
    if any(w in q for w in ["время", "работ", "режим", "час", "график", "открыт", "закрыт"]):
        return get_section("=== РЕЖИМ РАБОТЫ ===")
    # Адрес
    if any(w in q for w in ["адрес", "находится", "метро", "зубовский", "парк культуры"]):
        return get_section("=== АДРЕС ===")
    # Контакты
    if any(w in q for w in ["телефон", "почта", "email", "контакт"]):
        return get_section("=== КОНТАКТЫ ===")
    # Запись
    if any(w in q for w in ["записаться", "запись", "стать читателем"]):
        return get_section("=== ЗАПИСЬ В БИБЛИОТЕКУ ===")
    # Кампусная карта
    if any(w in q for w in ["кампусная", "карта", "читательский билет"]):
        return get_section("=== КАМПУСНАЯ КАРТА ===")
    # Получение учебников
    if any(w in q for w in ["получить", "взять", "заказать", "выдача", "книг", "учебник"]):
        return get_section("=== КАК ПОЛУЧИТЬ УЧЕБНИКИ ===")
    # Долги
    if any(w in q for w in ["долг", "просроч", "сдать", "потерял"]):
        return get_section("=== ДОЛГИ И ЗАДОЛЖЕННОСТИ ===")
    # Личный кабинет
    if any(w in q for w in ["личный кабинет", "логин", "пароль"]):
        return get_section("=== ЛИЧНЫЙ КАБИНЕТ ===")
    # Популярные учебники
    if any(w in q for w in ["учебник", "атлас", "анатомия", "гистология", "биохимия"]):
        return get_section("=== ПОПУЛЯРНЫЕ УЧЕБНИКИ ===")
    # Электронные ресурсы
    if any(w in q for w in ["электрон", "znanium", "ивис", "подписк"]):
        return get_section("=== ДОСТУПНЫЕ ЭЛЕКТРОННЫЕ РЕСУРСЫ ===")
    # Руководство
    if any(w in q for w in ["директор", "абрамова", "левин", "руководство"]):
        return get_section("=== РУКОВОДСТВО И АДМИНИСТРАЦИЯ ===")
    # Обратная связь
    if any(w in q for w in ["отзыв", "жалоб", "предложен", "обратная связь"]):
        return get_section("=== ОБРАТНАЯ СВЯЗЬ ===")
    return None

def build_response(query: str, context: str, lang: str) -> str:
    # Дополняем контекст связанной информацией, но без фанатизма
    extra = ""
    q = query.lower()
    if any(w in q for w in ["получить", "взять", "заказать", "выдача", "книг", "учебник"]):
        # Добавим напоминание про кампусную карту и личный кабинет
        extra = "\n\nВажно: " + get_section("=== КАМПУСНАЯ КАРТА ===") + "\n" + get_section("=== ЛИЧНЫЙ КАБИНЕТ ===")
    elif any(w in q for w in ["записаться", "запись"]):
        extra = "\n\nТакже понадобится: " + get_section("=== КАМПУСНАЯ КАРТА ===")

    full_context = context + extra

    lang_map = {
        "ru": "Отвечай на русском языке. Будь вежлив и краток, но включи все необходимые детали (телефоны, адреса, ссылки). Ссылки оформляй в Markdown: [текст](url).",
        "en": "Answer in English. Be concise but include all important details (phones, addresses, links). Use Markdown for links: [text](url).",
        "zh": "用中文回答。简洁但包含所有重要细节（电话、地址、链接）。链接使用Markdown格式：[文本](url)。"
    }
    prompt = f"""
Ты — сотрудник библиотеки Сеченовского университета. Используй ТОЛЬКО информацию ниже.
{lang_map.get(lang, lang_map['ru'])}

Информация:
{full_context}

Вопрос: {query}

Ответ:
"""
    return generate_with_groq(prompt, max_tokens=600)

def translate_text(text: str, target_lang: str) -> str:
    prompt = f"Переведи на {SUPPORTED_LANGS[target_lang]} (только перевод, без пояснений):\n\n{text}"
    return generate_with_groq(prompt, max_tokens=500)

# === Эндпоинты ===
@app.get("/welcome")
async def welcome(lang: str = "ru"):
    welcomes = {
        "ru": "👋 Привет! Я чат-бот библиотеки. Помогу с навигацией.",
        "en": "👋 Hi! I'm the library chatbot. I'll help you navigate.",
        "zh": "👋 你好！我是图书馆聊天机器人。我会帮你导航。"
    }
    return {"response": welcomes.get(lang, welcomes["ru"])}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    message = data.get("message", "").strip()
    lang = data.get("lang", "ru")
    if lang not in SUPPORTED_LANGS: lang = "ru"

    if not message:
        return {"response": "Пожалуйста, задайте вопрос."}

    context = find_context(message)
    if not context:
        # Поиск по сайту (Serper)
        try:
            headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
            payload = {"q": f"site:edu.rucml.ru {message}", "gl": "ru", "hl": "ru", "num": 3}
            r = requests.post(SERPER_URL, headers=headers, json=payload, timeout=8)
            items = r.json().get("organic", [])
            snippets = [clean_text(it.get("snippet", "")) for it in items if it.get("snippet")]
            if snippets:
                context = "\n".join(snippets[:2])
        except:
            context = None

    if not context:
        return {"response": "😔 Не нашёл ответ. Обратитесь к сотруднику: +7(499) 246-05-97."}

    response = build_response(message, context, lang)
    return {"response": response}

@app.post("/translate")
async def translate(request: Request):
    data = await request.json()
    text = data.get("text", "")
    target_lang = data.get("lang", "en")
    if not text or target_lang not in SUPPORTED_LANGS:
        return {"translated": text}
    translated = translate_text(text, target_lang)
    return {"translated": translated}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
