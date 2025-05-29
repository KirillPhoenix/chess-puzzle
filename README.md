# Chess Puzzle Solver

Chess Puzzle Solver — это Python-скрипт, использующий Playwright и Stockfish для автоматического решения шахматных задач на [Lichess Storm](https://lichess.org/storm).

## Возможности
- Автоматическое распознавание шахматной позиции на странице Lichess Storm с помощью Playwright.
- Генерация FEN (Forsyth-Edwards Notation) на основе текущей позиции.
- Вычисление лучшего хода с использованием шахматного движка Stockfish.
- Выполнение хода на доске с эмуляцией человеческого поведения (движение мыши).
- Поддержка превращения пешек (выбор фигуры при достижении последней горизонтали).
- Логирование для отладки и сохранение проблемных позиций.

## Требования
- Python 3.8+
- Установленный шахматный движок Stockfish (Windows: [скачать](https://stockfishchess.org/download/))
- Браузер Chromium (устанавливается автоматически через Playwright)

## Установка
1. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/your-username/chess-puzzle-solver.git
   cd chess-puzzle-solver
   ```

2. **Создайте виртуальное окружение** (рекомендуется):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Установите зависимости**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Установите Stockfish**:
   - Скачайте Stockfish для Windows с [официального сайта](https://stockfishchess.org/download/).
   - Распакуйте архив и укажите путь к `stockfish.exe` в коде (по умолчанию: `C:/Program Files (x86)/stockfish/stockfish.exe`).
   - Для других ОС измените путь в строке:
     ```python
     self.stockfish = Stockfish(path="path/to/stockfish")
     ```

5. **Установите Playwright и браузер**:
   ```bash
   playwright install
   ```

## Использование
1. **Настройте параметры в `SETTING`**:
   - `thinking_time`: Время (в миллисекундах) для анализа хода Stockfish (по умолчанию 900 мс).
   - `threads`: Количество ядер для Stockfish (по умолчанию 8).
   - `puzzle_mode`: Установлено в `True` для работы с задачами.
   - `depth`: Глубина анализа Stockfish (по умолчанию `None`).

   Пример:
   ```python
   class SETTING:
       thinking_time = 900
       threads = 8
       puzzle_mode = True
       depth = None
   ```

2. **Запустите скрипт**:
   ```bash
   python chess_bot.py
   ```

3. **Следуйте инструкциям**:
   - Скрипт откроет браузер и перейдет на [Lichess Storm](https://lichess.org/storm).
   - Бот начнет решать задачи автоматически.
   - Логи выводятся в консоль, включая FEN, лучший ход и время выполнения.
   - Если позиция не меняется 5 раз, бот сохраняет FEN в `failed_fen.txt` и HTML-страницу в `failed_position.html`.

## Отладка
- **Логи**: Скрипт логирует FEN, координаты ходов, ошибки Stockfish и Playwright.
- **Сохранение ошибок**:
  - Некорректные FEN сохраняются в `failed_fen.txt`.
  - HTML-страница с проблемной позицией сохраняется в `failed_position.html`.
- **Проблемы с FEN**:
  - Проверьте путь к Stockfish.
  - Убедитесь, что страница Lichess Storm загрузилась корректно.
- **Проблемы с ходами**:
  - Проверьте логи для ошибок в `make_move`.
  - Убедитесь, что `cg-board` виден в DOM.

## Ограничения
- Проект оптимизирован для Lichess Storm и может не работать на других страницах Lichess.

## Этическое использование
Этот проект предназначен для решения шахматных задач. Адаптирование и использование бота для читинга в рейтинговых играх на Lichess или других платформах **строго запрещено** и может привести к блокировке аккаунта. Уважайте правила платформы и сообщества.

## Лицензия
[MIT License](LICENSE)

---
**Примечание**: Этот проект является демонстрацией автоматизации и не поощряет нарушение правил Lichess. Используйте ответственно!
