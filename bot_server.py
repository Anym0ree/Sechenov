"""
AI Библиотекарь — Версия для демонстрации
Короткое приветствие и развёрнутые ответы по книгам.
"""

import os
import re
import html
import requests
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# === Настройки ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not GROQ_API_KEY:
    GROQ_API_KEY = "dummy"
if not SERPER_API_KEY:
    SERPER_API_KEY = "dummy"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"
SERPER_URL = "https://google.serper.dev/search"

with open("knowledge_base.txt", "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = f.read()

app = FastAPI(title="Library AI Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Получение секции по заголовку ===
def get_section(section_header: str) -> str:
    lines = KNOWLEDGE_BASE.split('\n')
    in_section = False
    result = []
    for line in lines:
        if section_header in line:
            in_section = True
            result.append(line)
        elif in_section:
            if line.startswith("==="):
                break
            if line.strip():
                result.append(line)
    return '\n'.join(result)

# === Очистка текста ===
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# === Генерация через Groq (или fallback) ===
def generate_with_groq(prompt: str, max_tokens: int = 600) -> str:
    if GROQ_API_KEY == "dummy":
        return "⚠️ API ключ не настроен. Информация:\n" + prompt.split("Контекст:")[-1].strip()
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }
    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return clean_text(response.json()["choices"][0]["message"]["content"].strip())
    except Exception as e:
        print(f"Ошибка Groq: {e}")
        return "Извините, ошибка. Вот что удалось найти:\n" + prompt.split("Контекст:")[-1].strip()

# === Поиск по сайту (запасной) ===
def search_on_website(query: str) -> Optional[str]:
    if SERPER_API_KEY == "dummy":
        return None
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": f"site:edu.rucml.ru {query}", "gl": "ru", "hl": "ru", "num": 3}
    try:
        response = requests.post(SERPER_URL, headers=headers, json=payload, timeout=10)
        data = response.json()
        snippets = []
        for item in data.get("organic", []):
            snippet = clean_text(item.get("snippet", ""))
            if snippet:
                snippets.append(snippet)
        return "\n".join(snippets[:2]) if snippets else None
    except:
        return None

# === Поиск ответа с составными секциями ===
def find_answer(query: str) -> Optional[str]:
    q = query.lower()
    
    # === ПОЛУЧЕНИЕ КНИГ (составной ответ) ===
    book_get_keywords = ["получить", "взять", "заказать", "выдача", "как получить книги", "как взять учебник", "заказ книг", "получение литературы"]
    if any(kw in q for kw in book_get_keywords):
        sections = []
        # Кампусная карта
        card = get_section("=== КАМПУСНАЯ КАРТА ===")
        if card:
            sections.append("📇 КАМПУСНАЯ КАРТА (читательский билет):\n" + card)
        # Личный кабинет
        lk = get_section("=== ЛИЧНЫЙ КАБИНЕТ ===")
        if lk:
            sections.append("💻 ЛИЧНЫЙ КАБИНЕТ:\n" + lk)
        # Как получить учебники
        howto = get_section("=== КАК ПОЛУЧИТЬ УЧЕБНИКИ ===")
        if howto:
            sections.append("📚 ПОШАГОВАЯ ИНСТРУКЦИЯ:\n" + howto)
        if sections:
            return "\n\n".join(sections)
    
    # === ВРЕМЯ РАБОТЫ ===
    work_keywords = ["время", "работ", "режим", "час", "график", "открыт", "закрыт", "расписание"]
    if any(kw in q for kw in work_keywords):
        section = get_section("=== РЕЖИМ РАБОТЫ ===")
        if section:
            return section

    # === АДРЕС ===
    addr_keywords = ["адрес", "находится", "проехать", "метро", "зубовский", "парк культуры"]
    if any(kw in q for kw in addr_keywords):
        section = get_section("=== АДРЕС ===")
        if section:
            return section

    # === КОНТАКТЫ ===
    contact_keywords = ["телефон", "почта", "email", "контакт", "позвонить"]
    if any(kw in q for kw in contact_keywords):
        section = get_section("=== КОНТАКТЫ ===")
        if section:
            return section

    # === РУКОВОДСТВО ===
    chief_keywords = ["директор", "абрамова", "левин", "руководство"]
    if any(kw in q for kw in chief_keywords):
        section = get_section("=== РУКОВОДСТВО И АДМИНИСТРАЦИЯ ===")
        if section:
            return section

    # === ЗАПИСЬ ===
    reg_keywords = ["записаться", "запись", "стать читателем"]
    if any(kw in q for kw in reg_keywords):
        section = get_section("=== ЗАПИСЬ В БИБЛИОТЕКУ ===")
        if section:
            return section

    # === КАМПУСНАЯ КАРТА (отдельно) ===
    card_keywords = ["кампусная", "карта", "читательский билет"]
    if any(kw in q for kw in card_keywords):
        section = get_section("=== КАМПУСНАЯ КАРТА ===")
        if section:
            return section

    # === УЧЕБНИКИ (список) ===
    book_keywords = ["учебник", "книга", "атлас", "литература"]
    if any(kw in q for kw in book_keywords):
        section = get_section("=== ПОПУЛЯРНЫЕ УЧЕБНИКИ ===")
        if section:
            return section

    # === ЭЛЕКТРОННЫЕ РЕСУРСЫ ===
    eres_keywords = ["электрон", "znanium", "ивис", "эко-вектор", "подписка"]
    if any(kw in q for kw in eres_keywords):
        section = get_section("=== ДОСТУПНЫЕ ЭЛЕКТРОННЫЕ РЕСУРСЫ ===")
        if section:
            return section

    # === ДОЛГИ ===
    debt_keywords = ["долг", "задолженность", "сдать", "просроч"]
    if any(kw in q for kw in debt_keywords):
        section = get_section("=== ДОЛГИ И ЗАДОЛЖЕННОСТИ ===")
        if section:
            return section

    # Если локально не нашли — ищем в интернете
    return search_on_website(query)

# === Генерация ответа через ИИ ===
def generate_response(query: str, context: str) -> str:
    prompt = f"""
Ты — дружелюбный и полезный библиотекарь. Ответь на вопрос пользователя, используя ТОЛЬКО информацию ниже.
Если контекст содержит несколько блоков (например, про кампусную карту, личный кабинет и получение книг), объясни последовательность действий.
Не добавляй лишнего.

Контекст:
{context}

Вопрос: {query}
Ответ (на русском):
"""
    return generate_with_groq(prompt)

# === Эндпоинты ===
@app.get("/welcome")
async def welcome(lang: str = "ru"):
    # Короткое приветствие
    return {"response": "👋 Привет! Я чат-бот библиотеки Сеченовского Университета. Помогу с режимом работы, получением книг, адресом и контактами. Спрашивай!"}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return {"response": "👋 Задайте вопрос о библиотеке."}

    context = find_answer(user_message)
    if not context:
        return {"response": "😔 Не нашёл ответ. Позвоните +7(499) 246-05-97."}

    response = generate_response(user_message, context)
    return {"response": response}

@app.get("/health")
async def health():
    return {"status": "ok"}
