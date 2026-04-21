"""
AI Библиотекарь - Финальная версия с улучшенным поиском и фильтрацией
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

if not all([GROQ_API_KEY, SERPER_API_KEY]):
    raise ValueError("❌ Не все ключи API найдены в переменных окружения!")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"
SERPER_URL = "https://google.serper.dev/search"

with open("knowledge_base.txt", "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = f.read()

app = FastAPI(title="Library AI Bot")

@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Очистка текста от мусора ===
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\sа-яА-ЯёЁa-zA-Z0-9\.,!?;:\-–—«»""''()\[\]{}@/]', '', text, flags=re.IGNORECASE)
    return text.strip()

def generate_with_groq(prompt: str, max_tokens: int = 600) -> str:
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
        return "Извините, произошла техническая ошибка. Пожалуйста, позвоните в библиотеку: +7(499) 246-05-97"

# === Умный поиск по сайту через Serper (с жёсткой фильтрацией) ===
def search_on_website(query: str) -> Optional[str]:
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Приоритетные разделы для поиска
    priority_restrictions = [
        "site:edu.rucml.ru/wlib/documents/",
        "site:edu.rucml.ru/wlib/contacts",
        "site:edu.rucml.ru/wlib/about",
    ]
    
    for restriction in priority_restrictions:
        payload = {
            "q": f"{restriction} {query}",
            "gl": "ru", "hl": "ru", "num": 3
        }
        try:
            response = requests.post(SERPER_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            snippets = []
            for item in data.get("organic", []):
                title = clean_text(item.get("title", ""))
                snippet = clean_text(item.get("snippet", ""))
                link = item.get("link", "")
                
                # Игнорируем новости, партнёрские материалы и т.д.
                exclude_keywords = ["medbasegeotar", "accessmedicine", "prog_sem", "new_books", "elzevir", "double3", "tem_plan", "request1", "онлайн-курсы", "директ-академии"]
                if any(ex in (title + snippet).lower() for ex in exclude_keywords):
                    continue
                
                if snippet and len(snippet) > 25:
                    snippets.append(f"📄 {title}\n{snippet}\n🔗 {link}")
            
            if snippets:
                return "\n\n---\n\n".join(snippets[:2])
        except Exception as e:
            print(f"Ошибка поиска в {restriction}: {e}")
            continue
            
    return None

# === Расширенный локальный поиск с мощным словарём синонимов ===
def search_in_knowledge_base(query: str) -> Optional[str]:
    query_lower = query.lower()
    
    # 1. Поиск книг
    book_keywords = ["учебник", "книга", "атлас", "литература", "автор", "пособие", "руководство", "монография", "издание"]
    if any(kw in query_lower for kw in book_keywords):
        lines = KNOWLEDGE_BASE.split('\n')
        books_section, found_books = False, []
        for line in lines:
            if "=== ПОПУЛЯРНЫЕ УЧЕБНИКИ" in line:
                books_section = True
                continue
            elif books_section:
                if line.startswith("==="): break
                if line.strip():
                    line_lower = line.lower()
                    stop_words = ["учебник", "книга", "атлас", "есть", "ли", "в", "по", "для", "автор", "найти", "пособие"]
                    search_terms = [w for w in query_lower.split() if w not in stop_words]
                    if any(term in line_lower for term in search_terms):
                        found_books.append(line.strip())
        if found_books:
            return clean_text("Найдены следующие учебники:\n" + "\n".join(found_books[:5]))

    # 2. Мега-карта синонимов для всех разделов
    keyword_groups = [
        (["режим", "часы", "работает", "открыта", "закрыта", "график", "во сколько", "время", "расписание", "обед", "перерыв", "выходной", "праздник", "санитарный"], "=== РЕЖИМ РАБОТЫ ==="),
        (["телефон", "контакты", "позвонить", "связаться", "номер", "почта", "email", "mail", "факс", "телефонная книга"], "=== КОНТАКТЫ ==="),
        (["директор", "руководство", "абрамова", "заместитель", "зам", "левин", "начальник", "администрация", "деканат", "ректор", "проректор", "управление", "кадры", "отдел"], "=== РУКОВОДСТВО И АДМИНИСТРАЦИЯ ==="),
        (["кампусная", "карта", "читательский", "билет", "пропуск", "удостоверение", "студенческий"], "=== КАМПУСНАЯ КАРТА ==="),
        (["мфц", "многофункциональный центр"], "Адрес МФЦ: Москва, ул. Трубецкая, д.8, стр.2, вход со двора."),
        (["получить", "выдача", "взять", "заказать", "заказ", "бронь", "учебники", "литературу", "книги"], "=== КАК ПОЛУЧИТЬ УЧЕБНИКИ ==="),
        (["долг", "задолженность", "потерял", "утеряна", "сдать", "просрочка", "штраф", "пени", "возврат"], "=== ДОЛГИ И ЗАДОЛЖЕННОСТИ ==="),
        (["личный кабинет", "логин", "пароль", "авторизация", "вход", "аккаунт", "профиль", "учетная запись", "регистрация"], "=== ЛИЧНЫЙ КАБИНЕТ ==="),
        (["адрес", "находится", "находиться", "местонахождение", "где находится", "проехать", "пройти", "найти", "добраться", "расположение", "метро", "карта", "схема", "маршрут", "парковка"], "=== АДРЕС ==="),
        (["электронные", "ресурсы", "базы", "medbasegeotar", "voka", "знаниум", "ивис", "подписка", "доступ", "удаленка"], "=== ДОСТУПНЫЕ ЭЛЕКТРОННЫЕ РЕСУРСЫ ==="),
        (["обратная связь", "отзыв", "предложение", "жалоба", "пожаловаться", "вопрос", "поддержка", "помощь"], "=== ОБРАТНАЯ СВЯЗЬ ==="),
        (["запись", "записаться", "стать читателем", "читательский билет", "первый раз"], "=== ЗАПИСЬ В БИБЛИОТЕКУ ==="),
        (["документы", "правила", "положение", "устав", "регламент", "инструкция", "бланк", "заявление", "образец"], "=== ДОКУМЕНТЫ И ПРАВИЛА ==="),
        (["новые поступления", "новинки", "поступило", "свежие"], "=== НОВЫЕ ПОСТУПЛЕНИЯ ==="),
    ]
    
    for keywords, section in keyword_groups:
        if any(kw in query_lower for kw in keywords):
            if section.startswith("==="):
                lines = KNOWLEDGE_BASE.split('\n')
                in_section, result = False, []
                for line in lines:
                    if section in line:
                        in_section = True
                        result.append(line)
                    elif in_section:
                        if line.startswith("==="): break
                        if line.strip(): result.append(line)
                return clean_text('\n'.join(result))
            else:
                return clean_text(section)
    return None

# === Генерация финального ответа ===
def generate_ai_response(query: str, context: str, source: str = "локальной базы") -> str:
    prompt = f"""
Ты — строгий и полезный виртуальный библиотекарь. Твоя задача — дать точный ответ, основанный ИСКЛЮЧИТЕЛЬНО на предоставленной информации. Не добавляй ничего от себя. Если в информации нет ответа, честно скажи об этом и предложи обратиться к сотруднику.

**Правила для ссылок:**
- Оформляй их в формате Markdown: [Название документа](ссылка).

**Источник информации:** {source}
**Контекст:** {context}
**Вопрос:** {query}

**Твой ответ:**
"""
    return generate_with_groq(prompt, max_tokens=600)

# === Эндпоинты ===
@app.get("/welcome")
async def welcome():
    return {
        "response": (
            "👋 Здравствуйте! Я — виртуальный помощник Фундаментальной учебной библиотеки Сеченовского Университета.\n\n"
            "Я помогу вам узнать:\n"
            "• режим работы и адрес;\n"
            "• как записаться и получить учебники;\n"
            "• контакты, руководство, правила;\n"
            "• наличие популярных учебников и электронных ресурсов.\n\n"
            "Просто напишите свой вопрос, и я постараюсь найти ответ. "
            "Если я что-то упущу — всегда можно обратиться к сотруднику по телефону +7(499) 246‑05‑97."
        )
    }

@app.options("/chat")
async def options_chat():
    return {"message": "OK"}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()
    
    # Если сообщение пустое — можно вернуть короткое приветствие
    if not user_message:
        return {"response": (
            "👋 Здравствуйте! Я — виртуальный библиотекарь. "
            "Спросите меня о режиме работы, адресе, записи, учебниках или контактах — я постараюсь помочь!"
        )}
    
    # 1. Локальный поиск
    local_result = search_in_knowledge_base(user_message)
    if local_result:
        return {"response": generate_ai_response(user_message, local_result, "локальной базы знаний")}
    
    # 2. Поиск по сайту
    web_result = search_on_website(user_message)
    if web_result:
        return {"response": generate_ai_response(user_message, web_result, "поиска по сайту")}
    
    # 3. Не найдено
    return {"response": "К сожалению, я не нашел ответ на ваш вопрос. Рекомендую обратиться к сотруднику библиотеки лично или по телефону +7(499) 246-05-97."}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
