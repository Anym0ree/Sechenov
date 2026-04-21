"""
AI Библиотекарь — Умный ассистент Фундаментальной библиотеки Сеченовского Университета
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Утилиты ===
def clean_text(text: str) -> str:
    """Очистка текста от HTML-сущностей и лишних символов."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\sа-яА-ЯёЁa-zA-Z0-9\.,!?;:\-–—«»""''()\[\]{}@/]', '', text, flags=re.IGNORECASE)
    return text.strip()

def normalize_query(text: str) -> str:
    """Приведение запроса к нижнему регистру, удаление знаков препинания."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def jaccard_similarity(a: str, b: str) -> float:
    """Простая мера схожести двух строк (коэффициент Жаккара)."""
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

# === Генерация через Groq ===
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

# === Поиск по сайту через Serper ===
def search_on_website(query: str) -> Optional[str]:
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    priority_restrictions = [
        "site:edu.rucml.ru/wlib/documents/",
        "site:edu.rucml.ru/wlib/contacts",
        "site:edu.rucml.ru/wlib/about",
    ]
    for restriction in priority_restrictions:
        payload = {"q": f"{restriction} {query}", "gl": "ru", "hl": "ru", "num": 3}
        try:
            response = requests.post(SERPER_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            snippets = []
            for item in data.get("organic", []):
                title = clean_text(item.get("title", ""))
                snippet = clean_text(item.get("snippet", ""))
                link = item.get("link", "")
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

# === Умный локальный поиск (с нечётким сопоставлением) ===
def search_in_knowledge_base(query: str) -> Optional[str]:
    norm_query = normalize_query(query)
    
    # Поиск учебников (специальная обработка)
    if any(kw in norm_query for kw in ["учебник", "книга", "атлас", "литература", "автор", "пособие", "руководство", "монография"]):
        lines = KNOWLEDGE_BASE.split('\n')
        books_section, found_books = False, []
        for line in lines:
            if "=== ПОПУЛЯРНЫЕ УЧЕБНИКИ" in line:
                books_section = True
                continue
            elif books_section:
                if line.startswith("==="): break
                if line.strip():
                    line_norm = normalize_query(line)
                    # Считаем схожесть с запросом
                    if jaccard_similarity(norm_query, line_norm) > 0.1:
                        found_books.append(line.strip())
        if found_books:
            return clean_text("Найдены следующие учебники:\n" + "\n".join(found_books[:5]))

    # Мега-карта разделов (с синонимами)
    sections_map = [
        (["режим", "часы", "работает", "открыта", "закрыта", "график", "во сколько", "время", "расписание", "обед", "перерыв", "выходной", "праздник", "санитарный"], "=== РЕЖИМ РАБОТЫ ==="),
        (["телефон", "контакты", "позвонить", "связаться", "номер", "почта", "email", "mail", "факс"], "=== КОНТАКТЫ ==="),
        (["директор", "руководство", "абрамова", "заместитель", "зам", "левин", "начальник", "администрация", "деканат", "ректор"], "=== РУКОВОДСТВО И АДМИНИСТРАЦИЯ ==="),
        (["кампусная", "карта", "читательский", "билет", "пропуск", "удостоверение", "студенческий"], "=== КАМПУСНАЯ КАРТА ==="),
        (["мфц", "многофункциональный центр"], "Адрес МФЦ: Москва, ул. Трубецкая, д.8, стр.2, вход со двора."),
        (["получить", "выдача", "взять", "заказать", "заказ", "бронь", "учебники", "литературу", "книги"], "=== КАК ПОЛУЧИТЬ УЧЕБНИКИ ==="),
        (["долг", "задолженность", "потерял", "утеряна", "сдать", "просрочка", "штраф", "пени", "возврат"], "=== ДОЛГИ И ЗАДОЛЖЕННОСТИ ==="),
        (["личный кабинет", "логин", "пароль", "авторизация", "вход", "аккаунт", "профиль", "учетная запись", "регистрация"], "=== ЛИЧНЫЙ КАБИНЕТ ==="),
        (["адрес", "находится", "находиться", "местонахождение", "где находится", "проехать", "пройти", "добраться", "расположение", "метро", "карта", "схема", "маршрут", "парковка"], "=== АДРЕС ==="),
        (["электронные", "ресурсы", "базы", "знаниум", "ивис", "подписка", "доступ", "удаленка"], "=== ДОСТУПНЫЕ ЭЛЕКТРОННЫЕ РЕСУРСЫ ==="),
        (["обратная связь", "отзыв", "предложение", "жалоба", "пожаловаться", "вопрос", "поддержка", "помощь"], "=== ОБРАТНАЯ СВЯЗЬ ==="),
        (["запись", "записаться", "стать читателем", "читательский билет", "первый раз"], "=== ЗАПИСЬ В БИБЛИОТЕКУ ==="),
        (["документы", "правила", "положение", "устав", "регламент", "инструкция", "бланк", "заявление"], "=== ДОКУМЕНТЫ И ПРАВИЛА ==="),
        (["новые поступления", "новинки", "поступило", "свежие"], "=== НОВЫЕ ПОСТУПЛЕНИЯ ==="),
    ]

    best_match = None
    best_score = 0.0

    for keywords, section in sections_map:
        # Проверяем, есть ли точное вхождение хотя бы одного ключевого слова
        if any(kw in norm_query for kw in keywords):
            # Нашли точное совпадение – сразу берём
            best_match = section
            break
        # Иначе вычисляем максимальную схожесть с каждым ключевым словом
        for kw in keywords:
            score = jaccard_similarity(norm_query, kw)
            if score > best_score:
                best_score = score
                best_match = section

    if best_match and best_score >= 0.3:  # порог срабатывания нечёткого поиска
        if best_match.startswith("==="):
            lines = KNOWLEDGE_BASE.split('\n')
            in_section, result = False, []
            for line in lines:
                if best_match in line:
                    in_section = True
                    result.append(line)
                elif in_section:
                    if line.startswith("==="): break
                    if line.strip(): result.append(line)
            return clean_text('\n'.join(result))
        else:
            return clean_text(best_match)

    return None

# === Генерация ответа через ИИ ===
def generate_ai_response(query: str, context: str, source: str = "локальной базы") -> str:
    prompt = f"""
Ты — заботливый и вежливый виртуальный библиотекарь Фундаментальной учебной библиотеки Сеченовского Университета.
Твоя задача — дать чёткий и полезный ответ, основанный ТОЛЬКО на предоставленном контексте.
Не выдумывай факты, не добавляй лишней информации.
Если в контексте есть ссылки, оформляй их в формате Markdown: [название](ссылка).
Старайся отвечать дружелюбно, можно использовать эмодзи, но не перебарщивай.

Источник: {source}
Контекст:
{context}

Вопрос пользователя: {query}

Твой ответ:
"""
    return generate_with_groq(prompt, max_tokens=600)

# === Эндпоинты ===
@app.get("/welcome")
async def welcome():
    return {
        "response": (
            "👋 Добро пожаловать в Фундаментальную учебную библиотеку Сеченовского Университета!\n\n"
            "Я — ваш виртуальный помощник. Я могу:\n"
            "• подсказать режим работы и адрес;\n"
            "• объяснить, как записаться и получить учебники;\n"
            "• рассказать о контактах, руководстве и правилах;\n"
            "• помочь найти популярные учебники и электронные ресурсы.\n\n"
            "Просто напишите свой вопрос, и я постараюсь быстро найти ответ. "
            "Если потребуется помощь сотрудника — звоните +7(499) 246-05-97."
        )
    }

@app.options("/chat")
async def options_chat():
    return {"message": "OK"}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return {"response": (
            "👋 Здравствуйте! Я — виртуальный библиотекарь. "
            "Спросите меня о режиме работы, адресе, записи, учебниках или контактах — я с радостью помогу!"
        )}

    # 1. Локальный поиск
    local_result = search_in_knowledge_base(user_message)
    if local_result:
        return {"response": generate_ai_response(user_message, local_result, "локальной базы знаний")}

    # 2. Поиск по сайту
    web_result = search_on_website(user_message)
    if web_result:
        return {"response": generate_ai_response(user_message, web_result, "поиска по сайту библиотеки")}

    # 3. Ничего не найдено
    return {"response": (
        "😔 К сожалению, я не смог найти ответ на ваш вопрос. "
        "Пожалуйста, обратитесь к сотруднику библиотеки лично или по телефону +7(499) 246-05-97."
    )}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
