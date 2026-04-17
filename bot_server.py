"""
AI Библиотекарь - Финальная версия с исправленным поиском адреса
"""

import os
import requests
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY не найден в переменных окружения!")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"

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

def generate_with_groq(prompt: str, max_tokens: int = 400) -> str:
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL_NAME, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": max_tokens}
    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Ошибка Groq: {e}")
        return "Извините, произошла техническая ошибка. Пожалуйста, позвоните в библиотеку: +7(499) 246-05-97"

def is_library_related(query: str) -> bool:
    library_keywords = [
        "библиотека", "книга", "учебник", "читальный", "абонемент", "кампусная", "карта", "мфц",
        "режим", "часы", "работает", "телефон", "адрес", "долг", "задолженность", "ресурс",
        "анатомия", "физиология", "гистология", "фармакология", "сеченов", "медицинский",
        "сан", "день", "открыта", "закрыта", "время", "получить", "взять", "сдать",
        "найти", "проехать", "пройти", "добраться", "находится", "расположение", "где"
    ]
    return any(kw in query.lower() for kw in library_keywords)

def search_in_knowledge_base(query: str) -> Optional[str]:
    query_lower = query.lower()
    
    book_keywords = ["учебник", "книга", "атлас", "литература", "автор"]
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
                    stop_words = ["учебник", "книга", "атлас", "есть", "ли", "в", "по", "для", "автор", "найти"]
                    search_terms = [w for w in query_lower.split() if w not in stop_words]
                    if any(term in line_lower for term in search_terms):
                        found_books.append(line.strip())
        if found_books:
            return "Найдены следующие учебники:\n" + "\n".join(found_books[:5])
    
    keyword_groups = [
        (["режим работы", "часы работы", "во сколько", "время работы", "работает", "открыта", "закрыта", "график"], "=== РЕЖИМ РАБОТЫ ==="),
        (["санитарный день", "санитарный"], "Санитарный день: проводится раз в месяц (даты объявляются на сайте)"),
        (["телефон", "контакты", "позвонить", "связаться", "номер"], "=== КОНТАКТЫ ==="),
        (["кампусная карта", "получить карту", "карта мир", "читательский билет"], "=== КАМПУСНАЯ КАРТА ==="),
        (["мфц"], "Адрес МФЦ: Москва, ул. Трубецкая, д.8, стр. 2"),
        (["получить учебники", "выдача книг", "взять книгу", "как получить"], "=== КАК ПОЛУЧИТЬ УЧЕБНИКИ ==="),
        (["долги", "задолженность", "потерял книгу", "утеряна", "сдать книги"], "=== ДОЛГИ И ЗАДОЛЖЕННОСТИ ==="),
        (["личный кабинет", "логин", "пароль", "авторизация", "войти"], "=== ЛИЧНЫЙ КАБИНЕТ ==="),
        (["адрес", "где находится", "как проехать", "как пройти", "место", "найти библиотеку", "добраться", "расположение", "как найти"], "=== АДРЕС ==="),
        (["электронные ресурсы", "базы данных", "medbasegeotar", "voka", "знаниум", "ивис"], "=== ДОСТУПНЫЕ ЭЛЕКТРОННЫЕ РЕСУРСЫ ==="),
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
                return '\n'.join(result)
            else:
                return section
    return None

def generate_ai_response(query: str, context: Optional[str] = None) -> str:
    if context:
        prompt = f"""
Ты — строгий и точный виртуальный библиотекарь. Отвечай ТОЛЬКО на основе информации ниже. НЕ ДОМЫСЛИВАЙ.

Информация:
{context}

Вопрос: {query}

Твой ответ:
"""
        return generate_with_groq(prompt, max_tokens=400)
    else:
        return "К сожалению, в моей базе знаний нет ответа на этот вопрос. Рекомендую обратиться к сотруднику библиотеки лично или по телефону +7(499) 246-05-97."

@app.options("/chat")
async def options_chat():
    return {"message": "OK"}



@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
