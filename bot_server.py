"""
AI Библиотекарь - FastAPI сервер для чат-бота
Версия на requests (без openai)
"""

import os
import re
import json
import requests
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# === Настройка ===
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY не найден!")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "google/gemini-2.0-flash-exp:free"

# === Загрузка базы знаний ===
with open("knowledge_base.txt", "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = f.read()

# === FastAPI приложение ===
app = FastAPI(title="Library AI Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Question(BaseModel):
    message: str
    history: Optional[list] = []


class Answer(BaseModel):
    response: str


# === Вызов OpenRouter через requests ===
def call_openrouter(prompt: str, max_tokens: int = 400) -> str:
    """Отправляет запрос к OpenRouter API и возвращает ответ."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Anym0ree/Sechenov",
        "X-Title": "LibraryBot"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Ошибка OpenRouter: {e}")
        return "Извините, произошла ошибка. Пожалуйста, позвоните в библиотеку: +7(499) 246-05-97"


# === Поиск в базе знаний ===
def search_in_knowledge_base(query: str) -> Optional[str]:
    """Поиск по ключевым словам в базе знаний, включая учебники."""
    query_lower = query.lower()
    
    # Проверяем, спрашивают ли про книгу/учебник
    book_keywords = ["учебник", "книга", "атлас", "литература", "автор", "найти", "поиск", "есть ли"]
    is_book_query = any(kw in query_lower for kw in book_keywords)
    
    # Если это запрос о книге, ищем в разделе учебников
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
                if line.strip() and not line.startswith("--"):
                    line_lower = line.lower()
                    stop_words = ["учебник", "книга", "атлас", "есть", "ли", "в", "по", "для", "автор", "найти"]
                    search_terms = [w for w in query_lower.split() if w not in stop_words]
                    
                    if any(term in line_lower for term in search_terms):
                        found_books.append(line.strip())
        
        if found_books:
            return "Найдены следующие учебники:\n" + "\n".join(found_books[:5])
    
    # Карта ключевых слов для общих вопросов
    keywords_map = {
        "режим работы": "=== РЕЖИМ РАБОТЫ ===",
        "часы работы": "=== РЕЖИМ РАБОТЫ ===",
        "во сколько": "=== РЕЖИМ РАБОТЫ ===",
        "санитарный день": "Санитарный день: проводится раз в месяц",
        "телефон": "=== КОНТАКТЫ ===",
        "контакты": "=== КОНТАКТЫ ===",
        "позвонить": "=== КОНТАКТЫ ===",
        "кампусная карта": "=== КАМПУСНАЯ КАРТА ===",
        "получить карту": "=== КАМПУСНАЯ КАРТА ===",
        "мфц": "Адрес МФЦ: Москва, ул. Трубецкая, д.8, стр. 2",
        "учебники": "=== КАК ПОЛУЧИТЬ УЧЕБНИКИ ===",
        "получить книги": "=== КАК ПОЛУЧИТЬ УЧЕБНИКИ ===",
        "долги": "=== ДОЛГИ И ЗАДОЛЖЕННОСТИ ===",
        "задолженность": "=== ДОЛГИ И ЗАДОЛЖЕННОСТИ ===",
        "потерял книгу": "О: Необходимо заменить утерянную литературу",
        "личный кабинет": "=== ЛИЧНЫЙ КАБИНЕТ ===",
        "логин": "Логин: ваша электронная почта, Пароль: часть почты до @ (ЗАГЛАВНЫМИ буквами)",
        "пароль": "Пароль: часть почты до @ (ЗАГЛАВНЫМИ буквами)",
        "первый курс": "=== СТУДЕНТАМ ПЕРВОГО КУРСА ===",
        "первокурсник": "=== СТУДЕНТАМ ПЕРВОГО КУРСА ===",
        "предуниверсарий": "=== ПРЕДУНИВЕРСАРИЙ ===",
        "ресурсы": "=== ДОСТУПНЫЕ РЕСУРСЫ ===",
        "базы данных": "=== ДОСТУПНЫЕ РЕСУРСЫ ===",
        "medbasegeotar": "MedBaseGeotar: справочно-информационная система с ИИ-помощником",
        "voka": "VOKA: интерактивный 3D-атлас анатомии человека",
        "адрес": "Адрес: Зубовский бульвар, д.37, стр.1 (вход с Дашкова переулка)",
        "где находится": "Адрес: Зубовский бульвар, д.37, стр.1 (вход с Дашкова переулка)",
    }
    
    for keyword, section in keywords_map.items():
        if keyword in query_lower:
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


# === Генерация ответа через ИИ ===
def generate_ai_response(query: str, context: Optional[str] = None) -> str:
    if context:
        prompt = f"""
Ты — вежливый и полезный библиотекарь Фундаментальной учебной библиотеки Сеченовского университета.

Используй ТОЛЬКО эту информацию для ответа:
{context}

Вопрос: {query}

Ответь кратко, дружелюбно и по делу. Не придумывай информацию, которой нет в контексте.
Если речь о книгах — перечисли найденные учебники с авторами.
"""
    else:
        prompt = f"""
Ты — вежливый библиотекарь. На вопрос: "{query}" у тебя нет точной информации.
Ответь дружелюбно, что для поиска книг лучше воспользоваться личным кабинетом на сайте http://edu.rucml.ru/ или обратиться к сотруднику библиотеки по телефону +7(499) 246-05-97.
"""
    
    return call_openrouter(prompt, max_tokens=400)


# === Главный эндпоинт ===
@app.post("/chat", response_model=Answer)
async def chat(question: Question):
    user_message = question.message
    
    # 1. Ищем в базе знаний
    kb_result = search_in_knowledge_base(user_message)
    
    if kb_result:
        # 2. Если нашли — просим ИИ красиво оформить
        ai_response = generate_ai_response(user_message, kb_result)
        return Answer(response=ai_response)
    else:
        # 3. Если не нашли — вежливо отправляем к человеку
        ai_response = generate_ai_response(user_message)
        return Answer(response=ai_response)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
