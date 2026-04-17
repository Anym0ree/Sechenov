// Скрипт для внедрения чат-бота через консоль браузера
// Скопируй ВСЁ и вставь в консоль (F12 → Console)

(function() {
    // URL твоего сервера на BotHost (замени на свой после деплоя)
    const SERVER_URL = "https://your-bot.bothost.com/chat";
    
    // Создаём стили для виджета
    const style = document.createElement('style');
    style.textContent = `
        @keyframes jump {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        
        .lib-bot-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            font-family: 'Segoe UI', 'Arial', sans-serif;
        }
        
        .lib-bot-button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #1a5276, #2980b9);
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: transform 0.2s;
            animation: jump 2s ease-in-out infinite;
        }
        
        .lib-bot-button:hover {
            transform: scale(1.1);
            animation: none;
        }
        
        .lib-bot-button svg {
            width: 35px;
            height: 35px;
            fill: white;
        }
        
        .lib-bot-chat {
            position: absolute;
            bottom: 80px;
            right: 0;
            width: 350px;
            height: 500px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 5px 30px rgba(0,0,0,0.3);
            display: none;
            flex-direction: column;
            overflow: hidden;
        }
        
        .lib-bot-chat.active {
            display: flex;
        }
        
        .lib-bot-header {
            background: linear-gradient(135deg, #1a5276, #2980b9);
            color: white;
            padding: 15px;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .lib-bot-header-avatar {
            width: 30px;
            height: 30px;
            background: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .lib-bot-messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            background: #f5f5f5;
        }
        
        .lib-bot-message {
            margin-bottom: 12px;
            display: flex;
        }
        
        .lib-bot-message.bot {
            justify-content: flex-start;
        }
        
        .lib-bot-message.user {
            justify-content: flex-end;
        }
        
        .lib-bot-message-content {
            max-width: 80%;
            padding: 10px 15px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .lib-bot-message.bot .lib-bot-message-content {
            background: white;
            border-bottom-left-radius: 5px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        .lib-bot-message.user .lib-bot-message-content {
            background: #2980b9;
            color: white;
            border-bottom-right-radius: 5px;
        }
        
        .lib-bot-input-area {
            padding: 15px;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
        }
        
        .lib-bot-input {
            flex: 1;
            padding: 10px 15px;
            border: 1px solid #ddd;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
        }
        
        .lib-bot-input:focus {
            border-color: #2980b9;
        }
        
        .lib-bot-send {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: #2980b9;
            border: none;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }
        
        .lib-bot-send:hover {
            background: #1a5276;
        }
        
        .lib-bot-close {
            margin-left: auto;
            cursor: pointer;
            opacity: 0.7;
        }
        
        .lib-bot-close:hover {
            opacity: 1;
        }
        
        .lib-bot-typing {
            padding: 10px 15px;
            background: white;
            border-radius: 18px;
            display: inline-block;
        }
        
        .lib-bot-typing span {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #999;
            margin: 0 2px;
            animation: typing 1.4s infinite;
        }
        
        .lib-bot-typing span:nth-child(2) { animation-delay: 0.2s; }
        .lib-bot-typing span:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
            30% { transform: translateY(-5px); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
    
    // Создаём HTML виджета
    const widgetHTML = `
        <div class="lib-bot-container">
            <div class="lib-bot-chat" id="libBotChat">
                <div class="lib-bot-header">
                    <div class="lib-bot-header-avatar">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="#2980b9">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                        </svg>
                    </div>
                    <span>🤖 Библиотекарь</span>
                    <div class="lib-bot-close" onclick="document.getElementById('libBotChat').classList.remove('active')">✕</div>
                </div>
                <div class="lib-bot-messages" id="libBotMessages">
                    <div class="lib-bot-message bot">
                        <div class="lib-bot-message-content">
                            👋 Здравствуйте! Я виртуальный помощник библиотеки. Задайте мне вопрос о режиме работы, получении книг, кампусной карте или доступных ресурсах!
                        </div>
                    </div>
                </div>
                <div class="lib-bot-input-area">
                    <input type="text" class="lib-bot-input" id="libBotInput" placeholder="Введите вопрос..." />
                    <button class="lib-bot-send" id="libBotSend">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="lib-bot-button" id="libBotButton">
                <svg viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                </svg>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', widgetHTML);
    
    // Логика работы
    const chatWindow = document.getElementById('libBotChat');
    const button = document.getElementById('libBotButton');
    const messagesContainer = document.getElementById('libBotMessages');
    const input = document.getElementById('libBotInput');
    const sendButton = document.getElementById('libBotSend');
    
    button.addEventListener('click', () => {
        chatWindow.classList.toggle('active');
    });
    
    async function sendMessage() {
        const message = input.value.trim();
        if (!message) return;
        
        // Показываем сообщение пользователя
        messagesContainer.innerHTML += `
            <div class="lib-bot-message user">
                <div class="lib-bot-message-content">${message}</div>
            </div>
        `;
        input.value = '';
        
        // Показываем индикатор печати
        messagesContainer.innerHTML += `
            <div class="lib-bot-message bot" id="typingIndicator">
                <div class="lib-bot-message-content lib-bot-typing">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        try {
            const response = await fetch('${SERVER_URL}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });
            const data = await response.json();
            
            // Убираем индикатор печати
            document.getElementById('typingIndicator')?.remove();
            
            // Показываем ответ бота
            messagesContainer.innerHTML += `
                <div class="lib-bot-message bot">
                    <div class="lib-bot-message-content">${data.response}</div>
                </div>
            `;
        } catch (error) {
            document.getElementById('typingIndicator')?.remove();
            messagesContainer.innerHTML += `
                <div class="lib-bot-message bot">
                    <div class="lib-bot-message-content">⚠️ Ошибка соединения. Попробуйте позже.</div>
                </div>
            `;
        }
        
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    sendButton.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    console.log('✅ Библиотекарь загружен! Нажмите на иконку в правом нижнем углу.');
})();
