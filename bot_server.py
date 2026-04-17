"""
AI Библиотекарь - Финальная версия
Строгий и честный бот, работающий только на проверенной базе знаний
"""

import os
import requests
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# === Настройка Groq ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY не найден в переменных окружения!")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"

# === Загрузка базы знаний ===
with open("knowledge_base.txt", "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = f.read()

# === FastAPI приложение ===
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

# === Вызов Groq API ===
def generate_with_groq(prompt: str, max_tokens: int = 400) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,  # Минимальная температура для максимальной точности
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Ошибка Groq: {e}")
        return "Извините, произошла техническая ошибка. Пожалуйста, позвоните в библиотеку: +7(499) 246-05-97"

# === Проверка, относится ли вопрос к библиотеке ===
def is_library_related(query: str) -> bool:
    library_keywords = [
        "библиотека", "книга", "учебник", "читальный", "абонемент", "кампусная", "карта", "мфц",
        "режим", "часы", "работает", "телефон", "адрес", "долг", "задолженность", "ресурс",
        "анатомия", "физиология", "гистология", "фармакология", "сеченов", "медицинский",
        "сан", "день", "открыта", "закрыта", "время", "получить", "взять", "сдать"
    ]
    query_lower = query.lower()
    return any(kw in query_lower for kw in library_keywords)

# === Улучшенный поиск в базе знаний ===
def search_in_knowledge_base(query: str) -> Optional[str]:
    query_lower = query.lower()
    
    # Проверяем запросы о книгах
    book_keywords = ["учебник", "книга", "атлас", "литература", "автор"]
    is_book_query = any(kw in query_lower for kw in book_keywords)
    
    if is_book_query:
        lines = KNOWLEDGE_BASE.split('\n')
        books_section = False
        found_books = []
        
        for line in lines:
            if "=== ПОПУЛЯРНЫЕ УЧЕБНИКИ" in line:
                books_section = True
                continue
            elif books_section:
                if line.startswith("==="):
                    break
                if line.strip():
                    line_lower = line.lower()
                    stop_words = ["учебник", "книга", "атлас", "есть", "ли", "в", "по", "для", "автор", "найти"]
                    search_terms = [w for w in query_lower.split() if w not in stop_words]
                    
                    if any(term in line_lower for term in search_terms):
                        found_books.append(line.strip())
        
        if found_books:
            return "Найдены следующие учебники:\n" + "\n".join(found_books[:5])
    
    # Карта ключевых слов
    keyword_groups = [
        (["режим работы", "часы работы", "во сколько", "время работы", "работает", "открыта", "закрыта", "график"], "=== РЕЖИМ РАБОТЫ ==="),
        (["санитарный день", "санитарный"], "Санитарный день: проводится раз в месяц (даты объявляются на сайте)"),
        (["телефон", "контакты", "позвонить", "связаться", "номер"], "=== КОНТАКТЫ ==="),
        (["кампусная карта", "получить карту", "карта мир", "читательский билет"], "=== КАМПУСНАЯ КАРТА ==="),
        (["мфц"], "Адрес МФЦ: Москва, ул. Трубецкая, д.8, стр. 2"),
        (["получить учебники", "выдача книг", "взять книгу", "как получить"], "=== КАК ПОЛУЧИТЬ УЧЕБНИКИ ==="),
        (["долги", "задолженность", "потерял книгу", "утеряна", "сдать книги"], "=== ДОЛГИ И ЗАДОЛЖЕННОСТИ ==="),
        (["личный кабинет", "логин", "пароль", "авторизация", "войти"], "=== ЛИЧНЫЙ КАБИНЕТ ==="),
        (["адрес", "где находится", "как проехать", "как пройти", "место"], "=== АДРЕС ==="),
        (["электронные ресурсы", "базы данных", "medbasegeotar", "voka", "знаниум", "ивис"], "=== ДОСТУПНЫЕ ЭЛЕКТРОННЫЕ РЕСУРСЫ ==="),
    ]
    
    for keywords, section in keyword_groups:
        if any(kw in query_lower for kw in keywords):
            if section.startswith("==="):
                lines = KNOWLEDGE_BASE.split('\n')
                in_section = False
                result = []
                for line in lines:
                    if section in line:
                        in_section = True
                        result.append(line)
                    elif in_section:
                        if line.startswith("==="):
                            break
                        if line.strip():
                            result.append(line)
                return '\n'.join(result)
            else:
                return section
    
    return None

# === Генерация ответа через ИИ (только на основе контекста) ===
def generate_ai_response(query: str, context: Optional[str] = None) -> str:
    if context:
        prompt = f"""
Ты — строгий и точный виртуальный библиотекарь Фундаментальной учебной библиотеки Сеченовского университета.

ТВОИ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе информации, предоставленной ниже.
2. НЕ ДОМЫСЛИВАЙ и НЕ ПРИДУМЫВАЙ факты.
3. Если в информации нет точного ответа — честно скажи об этом.
4. Будь вежлив, но краток.

ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ:
{context}

ВОПРОС ПОСЕТИТЕЛЯ: {query}

ТВОЙ ОТВЕТ (строго по информации выше):
"""
    else:
        return "К сожалению, в моей базе знаний нет ответа на этот вопрос. Рекомендую обратиться к сотруднику библиотеки лично или по телефону +7(499) 246-05-97."
    
    return generate_with_groq(prompt, max_tokens=400)

# === Эндпоинты ===
@app.options("/chat")
async def options_chat():
    return {"message": "OK"}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return {"response": "Пожалуйста, задайте вопрос."}
    
    # Проверяем, относится ли вопрос к библиотеке
    if not is_library_related(user_message):
        return {"response": "Я отвечаю только на вопросы о библиотеке Сеченовского университета. Пожалуйста, задайте вопрос о режиме работы, книгах или услугах."}
    
    # Ищем в базе знаний
    kb_result = search_in_knowledge_base(user_message)
    
    if kb_result:
        ai_response = generate_ai_response(user_message, kb_result)
    else:
        ai_response = "К сожалению, в моей базе знаний нет ответа на этот вопрос. Рекомендую обратиться к сотруднику библиотеки лично или по телефону +7(499) 246-05-97."
        
    return {"response": ai_response}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
