# LightLauncher

Легковесный лаунчер для Minecraft с графическим интерфейсом на PyQt6.

## Возможности

- Запуск Minecraft (релизы, снапшоты, старые беты/альфы)
- Установка и скачивание версий
- Настройка выделяемой оперативной памяти
- Автопоиск Java
- Discord Rich Presence (показывает текущую версию)
- Консоль отладки Minecraft (опционально)
- Кэширование списка версий и фонового изображения
- Открытие папки с игрой

## Установка

```bash
git clone https://github.com/RanoGames/LightLauncher.git
cd LightLauncher
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

## Структура проекта

```
LightLauncher/
├── main.py          # Основной файл лаунчера
├── design.py        # UI-разметка (сгенерирована из design.ui)
├── design.ui        # Исходный файл Qt Designer
├── mclovin.ico      # Иконка приложения
├── folder.png       # Иконка кнопки "Открыть папку"
├── crash_log.txt    # Логи ошибок (генерируется автоматически)
├── requirements.txt # Зависимости
├── LICENSE          # Лицензия
└── README.md        # Этот файл
```

## Системные требования

- Python 3.8+
- Java (автоматически寻找.minecraft_launcher_lib.utils.get_java_executable)
- ~200 МБ свободного места для установки Minecraft

## Лицензия

MIT
