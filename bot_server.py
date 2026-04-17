"""
AI Библиотекарь - FastAPI сервер для чат-бота
Версия с прямым вызовом Google Gemini API (без Pydantic)
"""

import os
import json
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

# === Настройка Gemini ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY не найден в переменных окружения!")

genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"
model = genai.GenerativeModel(MODEL_NAME)

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

# === Вызов Google Gemini API ===
def generate_with_gemini(prompt: str, max_tokens: int = 400) -> str:
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"Ошибка Gemini: {e}")
        return "Извините, произошла ошибка. Пожалуйста, позвоните в библиотеку: +7(499) 246-05-97"

# === Поиск в базе знаний ===
def search_in_knowledge_base(query: str) -> Optional[str]:
    query_lower = query.lower()
    
    book_keywords = ["учебник", "книга", "атлас", "литература", "автор", "найти", "поиск", "есть ли"]
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
                if line.strip() and not line.startswith("--"):
                    line_lower = line.lower()
                    stop_words = ["учебник", "книга", "атлас", "есть", "ли", "в", "по", "для", "автор", "найти"]
                    search_terms = [w for w in query_lower.split() if w not in stop_words]
                    
                    if any(term in line_lower for term in search_terms):
                        found_books.append(line.strip())
        
        if found_books:
            return "Найдены следующие учебники:\n" + "\n".join(found_books[:5])
    
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
    
    return generate_with_gemini(prompt, max_tokens=400)

# === Эндпоинты ===
@app.options("/chat")
async def options_chat():
    return {"message": "OK"}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "")
    
    kb_result = search_in_knowledge_base(user_message)
    
    if kb_result:
        ai_response = generate_ai_response(user_message, kb_result)
    else:
        ai_response = generate_ai_response(user_message)
        
    return {"response": ai_response}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
