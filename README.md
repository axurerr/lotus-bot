# 🌸 LOTUS - Discord Role Management Bot (Python)

Продвинутый бот для управления ролями на **discord.py** с красивым UI, сохранением ролей при выходе/входе и системой логирования.

## ✨ Функции

### 🎭 Роль при входе (`/setstartrole`)
- Автоматически выдаёт указанную роль каждому новому участнику
- Проверка иерархии ролей (бот должен быть выше)
- Отключение через пустой параметр

### 💾 Сохранение ролей (автоматически)
- При выходе участника — все его роли сохраняются в БД
- При повторном входе — роли автоматически восстанавливаются
- Исключения: ботские роли, @everyone, управляемые интеграциями роли

### 🛡️ Исключаемые роли (`/excluderoles`)
- Роли в этом списке **не сохраняются** при выходе
- **Не восстанавливаются** при повторном входе
- Поддержка множественных ролей
- **🎮 Интерактивная панель** с селект-меню для удобного управления

### ⚙️ Настройки (`/settings`)
- Установка канала для логов
- Просмотр текущей конфигурации
- **🎮 Интерактивная панель** с кнопками
- Быстрый доступ к панели исключаемых ролей

### 📋 Логирование
- Вход/выход участников
- Выдача роли входа
- Сохранение/восстановление ролей
- Изменение настроек
- Красивые embed'ы с полной информацией

## 🛠 Установка

### 1. Требования
- **Python 3.10+** (скачай с [python.org](https://python.org))
- **Discord Bot Token** (создай в [Developer Portal](https://discord.com/developers/applications))

### 2. Настройка
```bash
# Перейди в папку бота
cd lotus-bot-py

# Создай виртуальное окружение (рекомендуется)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установи зависимости
pip install -r requirements.txt

# Скопируй пример конфига и заполни
copy .env.example .env
# Отредактируй .env - добавь DISCORD_TOKEN и CLIENT_ID
```

### 3. Запуск
```bash
python main.py
```

## 📁 Структура проекта

```
lotus-bot-py/
├── main.py                 # Точка входа
├── requirements.txt        # Зависимости
├── .env.example            # Пример конфига
├── .env                    # Твой конфиг (НЕ коммить в git!)
├── README.md
├── data/
│   └── lotus.db            # SQLite база (создаётся автоматически)
├── database/
│   └── db.py               # Все SQL запросы (aiosqlite)
├── utils/
│   └── embeds.py           # Утилиты для embed'ов
└── cogs/
    ├── setstartrole.py     # /setstartrole
    ├── excluderoles.py     # /excluderoles (с панелью!)
    ├── settings.py         # /settings (с панелью!)
    └── events.py           # on_member_join / on_member_remove
```

## 🗄 База данных (SQLite + aiosqlite)

Автоматически создаётся в `data/lotus.db`:

| Таблица | Описание |
|---------|----------|
| `guild_settings` | Настройки сервера (роль входа, канал логов) |
| `excluded_roles` | Исключаемые роли для каждого сервера |
| `user_roles` | Сохранённые роли пользователей |
| `action_logs` | История действий для аудита |

## 🔐 Необходимые права бота

В Discord Developer Portal → Bot → Privileged Gateway Intents включи:
- ✅ **Server Members Intent** (для входа/выхода)
- ✅ **Message Content Intent** (для текстовых команд в панелях)

В разрешениях бота на сервере:
- ✅ **Administrator** (или минимально: Manage Roles, View Channels, Send Messages, Embed Links, Manage Guild)

## 📝 Команды

| Команда | Описание | Права |
|---------|----------|-------|
| `/setstartrole [role]` | Установить/убрать роль входа | Administrator |
| `/excluderoles add <role>` | Добавить роль в исключения | Administrator |
| `/excluderoles remove <role>` | Убрать роль из исключений | Administrator |
| `/excluderoles list` | Список исключаемых ролей | Administrator |
| `/excluderoles clear` | Очистить все исключения | Administrator |
| `/excluderoles panel` | 🎮 **Интерактивная панель** | Administrator |
| `/settings logchannel [channel]` | Установить/убрать канал логов | Administrator |
| `/settings view` | Посмотреть настройки | Administrator |
| `/settings panel` | 🎮 **Интерактивная панель** | Administrator |

## 🎨 UI Особенности

- **Embed'ы** с единым стилем (фиолетовый бренд LOTUS)
- **Кнопки** для быстрых действий в панелях настроек
- **Селект-меню** для множественного выбора ролей (до 25 за раз)
- **Эфемерные ответы** (видит только админ)
- **Авто-обновление** панелей после изменений
- **Таймауты** коллекторов (60-120 сек)
- **Ожидание сообщений** для ввода ролей/каналов через чат

## 🐳 Docker (опционально)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```bash
docker build -t lotus-bot-py .
docker run -d --env-file .env lotus-bot-py
```

## 📄 Лицензия

MIT — используй свободно!

---

**Сделано с ❤️ на discord.py**