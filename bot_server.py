"""
AI Библиотекарь — Мультиязычный ассистент Фундаментальной библиотеки Сеченовского Университета
Поддерживает русский (ru), английский (en), китайский (zh).
"""

import os
import re
import html
import requests
from typing import Optional, List, Tuple, Dict
from fastapi import FastAPI, Request, Query
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Языковые настройки ===
SUPPORTED_LANGUAGES = {"ru", "en", "zh"}

# Словари переводов статических сообщений
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "welcome": {
        "ru": (
            "👋 Добро пожаловать в Фундаментальную учебную библиотеку Сеченовского Университета!\n\n"
            "Я — ваш виртуальный помощник. Я могу:\n"
            "• подсказать режим работы и адрес;\n"
            "• объяснить, как записаться и получить учебники;\n"
            "• рассказать о контактах, руководстве и правилах;\n"
            "• помочь найти популярные учебники и электронные ресурсы.\n\n"
            "Просто напишите свой вопрос, и я постараюсь быстро найти ответ. "
            "Если потребуется помощь сотрудника — звоните +7(499) 246-05-97."
        ),
        "en": (
            "👋 Welcome to the Fundamental Educational Library of Sechenov University!\n\n"
            "I am your virtual assistant. I can help you with:\n"
            "• Opening hours and address;\n"
            "• How to register and borrow textbooks;\n"
            "• Contacts, administration, and rules;\n"
            "• Finding popular textbooks and electronic resources.\n\n"
            "Just type your question, and I will try to find the answer quickly. "
            "If you need staff assistance, please call +7(499) 246-05-97."
        ),
        "zh": (
            "👋 欢迎来到谢切诺夫大学基础教学图书馆！\n\n"
            "我是您的虚拟助手。我可以帮助您：\n"
            "• 查询开放时间和地址；\n"
            "• 了解如何注册和借阅教科书；\n"
            "• 获取联系方式、管理人员信息和规章制度；\n"
            "• 查找热门教科书和电子资源。\n\n"
            "只需输入您的问题，我会尽快为您查找答案。"
            "如果您需要工作人员帮助，请致电 +7(499) 246-05-97。"
        )
    },
    "empty_message": {
        "ru": "👋 Здравствуйте! Я — виртуальный библиотекарь. Спросите меня о режиме работы, адресе, записи, учебниках или контактах — я с радостью помогу!",
        "en": "👋 Hello! I'm a virtual librarian. Ask me about opening hours, address, registration, textbooks or contacts — I'll be happy to help!",
        "zh": "👋 您好！我是虚拟图书馆员。请向我询问开放时间、地址、注册、教科书或联系方式——我很乐意为您提供帮助！"
    },
    "not_found": {
        "ru": "😔 К сожалению, я не смог найти ответ на ваш вопрос. Пожалуйста, обратитесь к сотруднику библиотеки лично или по телефону +7(499) 246-05-97.",
        "en": "😔 Unfortunately, I couldn't find an answer to your question. Please contact the library staff in person or by phone +7(499) 246-05-97.",
        "zh": "😔 抱歉，我未能找到您问题的答案。请亲自联系图书馆工作人员或致电 +7(499) 246-05-97。"
    },
    "error": {
        "ru": "Извините, произошла техническая ошибка. Пожалуйста, позвоните в библиотеку: +7(499) 246-05-97",
        "en": "Sorry, a technical error occurred. Please call the library: +7(499) 246-05-97",
        "zh": "抱歉，发生技术错误。请致电图书馆：+7(499) 246-05-97"
    }
}

def get_translation(key: str, lang: str) -> str:
    """Получить перевод для заданного ключа и языка (fallback на русский)."""
    if lang not in SUPPORTED_LANGUAGES:
        lang = "ru"
    return TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS[key]["ru"])

# === Утилиты ===
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\sа-яА-ЯёЁa-zA-Z0-9\.,!?;:\-–—«»""''()\[\]{}@/]', '', text, flags=re.IGNORECASE)
    return text.strip()

def normalize_query(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def jaccard_similarity(a: str, b: str) -> float:
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def contains_any_word(text: str, words: List[str]) -> bool:
    text_norm = normalize_query(text)
    for w in words:
        if re.search(rf'\b{re.escape(w)}\b', text_norm):
            return True
    return False

# === Генерация через Groq (с языком) ===
def generate_with_groq(prompt: str, lang: str = "ru", max_tokens: int = 600) -> str:
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
        return get_translation("error", lang)

# === Поиск по сайту (только русскоязычный, результат будет переведён LLM) ===
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

# === Локальный поиск (аналогично, только по русской базе) ===
def search_in_knowledge_base(query: str) -> Optional[str]:
    norm_query = normalize_query(query)

    # Ключевые слова на русском (т.к. база на русском)
    book_intent_words = [
        "учебник", "учебники", "учебного", "учебную", "учебной",
        "книга", "книги", "книгу", "книгой", "книжку", "книжка",
        "атлас", "атласа", "атласу", "атласом",
        "литература", "литературы", "литературе", "литературой",
        "пособие", "пособия", "пособию", "пособием",
        "руководство", "руководства", "руководству",
        "монография", "монографии", "монографию",
        "издание", "издания", "издании",
        "автор", "автора", "авторы",
        "методичка", "методички", "методичку",
        "практикум", "практикума",
        "задачник", "задачника",
        "хрестоматия", "хрестоматии",
    ]
    if contains_any_word(norm_query, book_intent_words):
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
                    line_norm = normalize_query(line)
                    authors_from_line = re.findall(r'[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}', line)
                    all_words_line = set(re.findall(r'[а-яё]+', line_norm))
                    query_words = set(re.findall(r'[а-яё]+', norm_query))
                    if query_words & all_words_line:
                        found_books.append(line.strip())
                    for author_part in ["привес", "лысенков", "бушкович", "сапин", "синельников",
                                        "покровский", "коротько", "березов", "коровкин",
                                        "афанасьев", "юрина", "струков", "серов", "харкевич", "поздеев"]:
                        if author_part in norm_query and author_part in line_norm:
                            found_books.append(line.strip())
                            break
        if found_books:
            found_books = list(dict.fromkeys(found_books))
            return clean_text("Найдены следующие учебники:\n" + "\n".join(found_books[:5]))
        return clean_text("Пожалуйста, уточните название или автора учебника. Популярные учебники можно посмотреть в разделе «Популярные учебники» на сайте.")

    sections_map: List[Tuple[List[str], str]] = [
        (["режим", "часы", "работает", "открыта", "закрыта", "график", "во сколько", "время",
          "расписание", "обед", "перерыв", "выходной", "праздник", "санитарный", "санитарный день",
          "работа библиотеки", "когда открывается", "когда закрывается", "до скольки", "со скольки",
          "часы работы", "график работы", "режим работы", "рабочие часы", "время работы", "подскажи режим"],"=== РЕЖИМ РАБОТЫ ==="),
        (["телефон", "контакты", "позвонить", "связаться", "номер", "почта", "email", "mail",
          "факс", "телефонная книга", "контактная информация", "телефоны", "адрес электронной почты",
          "как связаться", "куда звонить"], "=== КОНТАКТЫ ==="),
        (["директор", "руководство", "абрамова", "заместитель", "зам", "левин", "начальник",
          "администрация", "деканат", "ректор", "проректор", "управление", "кадры", "отдел",
          "кто директор", "фамилия директора", "заместитель директора"], "=== РУКОВОДСТВО И АДМИНИСТРАЦИЯ ==="),
        (["кампусная", "карта", "читательский", "билет", "пропуск", "удостоверение", "студенческий",
          "кампусную карту", "читательский билет", "студенческий билет", "электронный пропуск",
          "получить карту", "оформить билет", "кампусная карта где получить"], "=== КАМПУСНАЯ КАРТА ==="),
        (["мфц", "многофункциональный центр", "центр обслуживания", "получить кампусную карту мфц"],
         "Адрес МФЦ: Москва, ул. Трубецкая, д.8, стр.2, вход со двора."),
        (["получить", "выдача", "взять", "заказать", "заказ", "бронь", "учебники", "литературу",
          "книги", "получение книг", "как получить учебники", "заказ учебников", "бронирование книг",
          "взять книги", "получить литературу"], "=== КАК ПОЛУЧИТЬ УЧЕБНИКИ ==="),
        (["долг", "задолженность", "потерял", "утеряна", "сдать", "просрочка", "штраф", "пени",
          "возврат", "вернуть книги", "срок сдачи", "книговозвратчик", "просроченные книги",
          "что делать если потерял книгу"], "=== ДОЛГИ И ЗАДОЛЖЕННОСТИ ==="),
        (["личный кабинет", "логин", "пароль", "авторизация", "вход", "аккаунт", "профиль",
          "учетная запись", "регистрация", "войти в личный кабинет", "как зайти в лк",
          "пароль от личного кабинета", "логин для входа"], "=== ЛИЧНЫЙ КАБИНЕТ ==="),
        (["адрес", "находится", "находиться", "местонахождение", "где находится", "проехать",
          "пройти", "добраться", "расположение", "метро", "карта", "схема", "маршрут", "парковка",
          "как найти библиотеку", "как пройти", "станция метро", "ближайшее метро", "Зубовский бульвар"],
         "=== АДРЕС ==="),
        (["электронные", "ресурсы", "базы", "знаниум", "ивис", "подписка", "доступ", "удаленка",
          "электронная библиотека", "znanium", "ivis", "эко-вектор", "удалённый доступ",
          "как зайти в электронную библиотеку", "доступ к базам"], "=== ДОСТУПНЫЕ ЭЛЕКТРОННЫЕ РЕСУРСЫ ==="),
        (["обратная связь", "отзыв", "предложение", "жалоба", "пожаловаться", "вопрос", "поддержка",
          "помощь", "написать отзыв", "оставить жалобу", "форма обратной связи"], "=== ОБРАТНАЯ СВЯЗЬ ==="),
        (["запись", "записаться", "стать читателем", "читательский билет", "первый раз",
          "как записаться в библиотеку", "правила записи", "запись в библиотеку"],
         "=== ЗАПИСЬ В БИБЛИОТЕКУ ==="),
        (["документы", "правила", "положение", "устав", "регламент", "инструкция", "бланк",
          "заявление", "образец", "правила пользования", "положение о библиотеке", "выписка из правил"],
         "=== ДОКУМЕНТЫ И ПРАВИЛА ==="),
        (["новые поступления", "новинки", "поступило", "свежие", "новые книги", "что нового"],
         "=== НОВЫЕ ПОСТУПЛЕНИЯ ==="),
    ]

    best_match = None
    best_score = 0.0

    for keywords, section in sections_map:
        if contains_any_word(norm_query, keywords):
            best_match = section
            break
        for kw in keywords:
            score = jaccard_similarity(norm_query, kw)
            if score > best_score:
                best_score = score
                best_match = section

    if best_match and best_score >= 0.25:
        if best_match.startswith("==="):
            lines = KNOWLEDGE_BASE.split('\n')
            in_section, result = False, []
            for line in lines:
                if best_match in line:
                    in_section = True
                    result.append(line)
                elif in_section:
                    if line.startswith("==="):
                        break
                    if line.strip():
                        result.append(line)
            return clean_text('\n'.join(result))
        else:
            return clean_text(best_match)

    return None

# === Генерация ответа через ИИ с учётом языка ===
def generate_ai_response(query: str, context: str, source: str, lang: str) -> str:
    # Промпт с требованием отвечать на нужном языке
    language_instruction = {
        "ru": "Отвечай на русском языке.",
        "en": "Answer in English. Translate any Russian context into English naturally.",
        "zh": "用中文回答。将俄语内容自然地翻译成中文。"
    }
    prompt = f"""
Ты — заботливый и вежливый виртуальный библиотекарь Фундаментальной учебной библиотеки Сеченовского Университета.
Твоя задача — дать чёткий и полезный ответ, основанный ТОЛЬКО на предоставленном контексте.
Не выдумывай факты, не добавляй лишней информации.
Если в контексте есть ссылки, оформляй их в формате Markdown: [название](ссылка).
{language_instruction.get(lang, language_instruction["ru"])}

Источник: {source}
Контекст:
{context}

Вопрос пользователя: {query}

Твой ответ:
"""
    return generate_with_groq(prompt, lang, max_tokens=600)

# === Эндпоинты ===
@app.get("/welcome")
async def welcome(lang: str = Query("ru", description="Язык приветствия (ru, en, zh)")):
    if lang not in SUPPORTED_LANGUAGES:
        lang = "ru"
    return {"response": get_translation("welcome", lang)}

@app.options("/chat")
async def options_chat():
    return {"message": "OK"}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()
    lang = data.get("lang", "ru")
    if lang not in SUPPORTED_LANGUAGES:
        lang = "ru"

    if not user_message:
        return {"response": get_translation("empty_message", lang)}

    # 1. Локальный поиск (всегда на русском, т.к. база русская)
    local_result = search_in_knowledge_base(user_message)
    if local_result:
        return {"response": generate_ai_response(user_message, local_result, "локальной базы знаний", lang)}

    # 2. Поиск по сайту
    web_result = search_on_website(user_message)
    if web_result:
        return {"response": generate_ai_response(user_message, web_result, "поиска по сайту библиотеки", lang)}

    # 3. Ничего не найдено
    return {"response": get_translation("not_found", lang)}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
