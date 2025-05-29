import asyncio
import random
import time
from playwright.async_api import async_playwright
from stockfish import Stockfish

class SETTING:
    thinking_time = 900
    threads = 8 # Количество задействованных ядер Stockfish'ом
    puzzle_mode = True
    depth = None # Можно задать глубину

class Parser:
    def __init__(self):
        self.default_configs = {
            "common": {
                "user_agents": [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                ],
                "headers": [
                    {
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    },
                ],
            }
        }
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    async def setup_browser(self):
        if self.browser:
            await self.browser.close()
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--window-size=1366,768'
            ]
        )
        context_args = {
            "viewport": {"width": 1566, "height": 868},
            "user_agent": random.choice(self.default_configs["common"]["user_agents"]),
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
        }
        self.context = await self.browser.new_context(**context_args)
        await self.context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US', 'en'] });
        """)
        self.page = await self.context.new_page()
        print("Playwright успешно настроен")
        return self.page

    async def emulate_human_behavior(self):
        await asyncio.sleep(random.uniform(0.5, 1))
        for _ in range(random.randint(2, 4)):
            x, y = random.randint(100, 1000), random.randint(100, 700)
            await self.page.mouse.move(x, y, steps=5)
            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def close(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except Exception as err:
            print(f"Ошибка при закрытии Playwright: {err}")

class Chess(Parser):
    def __init__(self):
        super().__init__()
        self.stockfish = Stockfish(path="C:/Program Files (x86)/stockfish/stockfish.exe")
        self.board_state = None
        self.square_size = None
        self.board_width = None
        self.orientation = None
        self.board_rect = None

    def initialize_stockfish(self):
        self.stockfish.set_skill_level(20)
        self.stockfish.set_depth(SETTING.depth)

    def _coords_to_square(self, x, y, square_size, orientation='white'):
        try:
            x, y = float(x), float(y)
            if orientation == 'black':
                col = min(max(7 - int(x // square_size), 0), 7)
                row = min(max(7 - int(y // square_size), 0), 7)
            else:
                col = min(max(int(x // square_size), 0), 7)
                row = min(max(7 - int(y // square_size), 0), 7)
            files = 'abcdefgh'
            square = f"{files[col]}{row + 1}"
            return square
        except Exception as e:
            print(f"Ошибка преобразования координат: x={x}, y={y}, ошибка: {e}")
            return None

    def _square_to_coords(self, square):
        try:
            col = ord(square[0]) - ord('a')
            row = int(square[1]) - 1
            if self.orientation == 'white':
                x = col * self.square_size
                y = (7 - row) * self.square_size
            else:
                x = (7 - col) * self.square_size
                y = row * self.square_size
            x += self.square_size / 2
            y += self.square_size / 2
            return {'x': x, 'y': y}
        except Exception as e:
            print(f"Ошибка преобразования клетки {square} в координаты: {e}")
            return None

    def _detect_castling_rights(self, board):
        result = ''
        if board[0][4] == 'K':
            if board[0][7] == 'R': result += 'K'
            if board[0][0] == 'R': result += 'Q'
        if board[7][4] == 'k':
            if board[7][7] == 'r': result += 'k'
            if board[7][0] == 'r': result += 'q'
        return result if result else '-'

    async def _parse_board_to_fen(self):
        try:
            t_start = time.time()
            board = [[' ' for _ in range(8)] for _ in range(8)]
            piece_map = {
                'white king': 'K', 'white queen': 'Q', 'white rook': 'R', 'white bishop': 'B',
                'white knight': 'N', 'white pawn': 'P',
                'black king': 'k', 'black queen': 'q', 'black rook': 'r', 'black bishop': 'b',
                'black knight': 'n', 'black pawn': 'p'
            }

            if self.orientation is None or SETTING.puzzle_mode:
                orientation = await self.page.evaluate('''() => {
                    const wrap = document.querySelector('.cg-wrap');
                    return wrap && wrap.classList.contains('orientation-black') ? 'black' : 'white';
                }''')
                self.orientation = orientation
                print(f"Ориентация доски: {self.orientation}")

            if self.board_width is None:
                size = await self.page.evaluate('''() => {
                    const container = document.querySelector('cg-container');
                    return container ? parseFloat(getComputedStyle(container).width) : 436.0;
                }''')
                self.board_width = size
                self.square_size = self.board_width / 8
                print(f"Размер доски: {self.board_width}px, square_size: {self.square_size}px")

            pieces = await self.page.evaluate('''() => {
                return Array.from(document.querySelectorAll('cg-board piece')).map(p => ({
                    class: p.className,
                    transform: p.style.transform
                }));
            }''')
            last_moves = await self.page.evaluate('''() => {
                return Array.from(document.querySelectorAll('cg-board square.last-move')).map(s => s.style.transform);
            }''')

            for piece in pieces:
                if 'ghost' in piece['class']:
                    continue
                class_name = piece['class'].replace(' dragging', '').replace(' ghost', '')
                if not piece['transform'] or 'translate' not in piece['transform']:
                    continue
                coords = piece['transform'].split('(')[1].split(')')[0].split(',')
                x = float(coords[0].replace('px', '').strip())
                y = float(coords[1].replace('px', '').strip())
                square = self._coords_to_square(x, y, self.square_size, self.orientation)
                if not square:
                    continue
                col = ord(square[0]) - ord('a')
                row = int(square[1]) - 1
                if class_name in piece_map:
                    if board[row][col] != ' ':
                        print(f"❗ Клетка {square} уже занята {board[row][col]}, не перезаписываем {piece_map[class_name]}")
                        continue
                    board[row][col] = piece_map[class_name]

            fen_rows = []
            if self.orientation == 'black':
                for row in range(8):
                    empty = 0
                    fen_row = ''
                    for col in range(8):
                        piece = board[row][col]
                        if piece == ' ':
                            empty += 1
                        else:
                            if empty > 0:
                                fen_row += str(empty)
                                empty = 0
                            fen_row += piece
                    if empty > 0:
                        fen_row += str(empty)
                    fen_rows.append(fen_row)
            else:
                for row in range(7, -1, -1):
                    empty = 0
                    fen_row = ''
                    for col in range(8):
                        piece = board[row][col]
                        if piece == ' ':
                            empty += 1
                        else:
                            if empty > 0:
                                fen_row += str(empty)
                                empty = 0
                            fen_row += piece
                    if empty > 0:
                        fen_row += str(empty)
                    fen_rows.append(fen_row)
            piece_placement = '/'.join(fen_rows)

            my_color = 'w' if self.orientation == 'white' else 'b'
            active_color = 'w'
            if last_moves:
                print(f"Обнаружены last-move: {len(last_moves)} клеток\n", last_moves)
                found_exact = False

                # Сначала пытаемся найти фигуру точно на одной из last-move клеток
                for transform in last_moves:
                    if 'translate' not in transform:
                        continue
                    coords = transform.split('(')[1].split(')')[0].split(',')
                    x = float(coords[0].replace('px', '').strip())
                    y = float(coords[1].replace('px', '').strip())
                    square = self._coords_to_square(x, y, self.square_size, self.orientation)
                    print(f"Last-move клетка: {square} (x={x}, y={y})")

                    for piece in pieces:
                        if 'transform' not in piece or 'translate' not in piece['transform']:
                            continue
                        piece_x = float(piece['transform'].split('(')[1].split(')')[0].split(',')[0].replace('px', '').strip())
                        piece_y = float(piece['transform'].split('(')[1].split(')')[0].split(',')[1].replace('px', '').strip())
                        if abs(piece_x - x) < 0.1 and abs(piece_y - y) < 0.1:
                            class_name = piece['class'].replace(' dragging', '').replace(' ghost', '')
                            print(f"Фигура на last-move: {class_name}")
                            if 'white' in class_name:
                                active_color = 'b'
                            elif 'black' in class_name:
                                active_color = 'w'
                            found_exact = True
                            break
                    if found_exact:
                        break

                # Если точная фигура не найдена — ищем ближайшую к любой клетке. Это значит была рокировка и фигур нету на пунктах назначения. 
                # Например Ke1=>Kg1 Rh8=>Rf1, клетки в last move будет e1 и h8, но фигур там уже не будет
                if not found_exact:
                    print("Фигура на last-move не найдена, ищем ближайшие фигуры")
                    for transform in last_moves:
                        if 'translate' not in transform:
                            continue
                        coords = transform.split('(')[1].split(')')[0].split(',')
                        x = float(coords[0].replace('px', '').strip())
                        y = float(coords[1].replace('px', '').strip())
                        square = self._coords_to_square(x, y, self.square_size, self.orientation)

                        for piece in pieces:
                            if 'transform' not in piece or 'translate' not in piece['transform']:
                                continue
                            piece_x = float(piece['transform'].split('(')[1].split(')')[0].split(',')[0].replace('px', '').strip())
                            piece_y = float(piece['transform'].split('(')[1].split(')')[0].split(',')[1].replace('px', '').strip())
                            if abs(piece_x - x) <= 2 * self.square_size and abs(piece_y - y) <= 2 * self.square_size:
                                class_name = piece['class'].replace(' dragging', '').replace(' ghost', '')
                                piece_square = self._coords_to_square(piece_x, piece_y, self.square_size, self.orientation)
                                print(f"Найдена ближайшая фигура: {class_name} на {piece_square} (x={piece_x}, y={piece_y})")
                                if 'white' in class_name:
                                    active_color = 'b'
                                elif 'black' in class_name:
                                    active_color = 'w'
                                found_exact = True
                                break
                        if found_exact:
                            break

                if not found_exact:
                    print("Фигура на last-move и ближайшие не найдены, используем цвет по умолчанию: w")

            castling = self._detect_castling_rights(board)
            en_passant = '-'
            halfmove = '0'
            fullmove = '1'

            fen = f"{piece_placement} {active_color} {castling} {en_passant} {halfmove} {fullmove}"
            print(f"Сформирован FEN: {fen}, время: {(time.time() - t_start):.3f}s")
            return fen
        except Exception as e:
            print(f"Ошибка парсинга FEN: {e}")
            return None


    async def get_board_position(self):
        try:
            t_start = time.time()
            if not self.page or self.page.is_closed():
                print("Страница закрыта, невозможно получить позицию")
                return None
            await self.page.wait_for_selector('cg-board', timeout=5000)
            fen = await self._parse_board_to_fen()
            if fen:
                self.board_state = fen
                print(f"Текущая позиция (FEN): {fen}, время: {(time.time() - t_start):.3f}s")
            return fen
        except Exception as e:
            print(f"Ошибка получения позиции: {e}")
            return None

    async def get_best_move(self, fen, think_time=30):
        try:
            t_start = time.time()
            if not self.stockfish.is_fen_valid(fen):
                print(f"Некорректный FEN: {fen}")
                return None
            self.stockfish.set_fen_position(fen)
            best_move = self.stockfish.get_best_move_time(think_time)
            print(f"Лучший ход от Stockfish: {best_move}, время: {(time.time() - t_start):.3f}s")
            return best_move
        except Exception as e:
            print(f"Ошибка получения хода от Stockfish: {e}")
            return None

    async def make_move(self, move):
        try:
            t_start = time.time()
            if not move:
                print("Ход не определён (move is None)")
                return False

            source_square = move[:2]
            target_square = move[2:4]
            print(f"Попытка выполнить ход: {move} ({source_square} -> {target_square})")

            if not self.page or self.page.is_closed():
                print("Страница закрыта, невозможно выполнить ход")
                return False

            source_coords = self._square_to_coords(source_square)
            target_coords = self._square_to_coords(target_square)

            if source_coords and target_coords:
                if self.board_rect is None:
                    self.board_rect = await self.page.evaluate('''
                        () => {
                            const board = document.querySelector('cg-board');
                            if (!board) return { left: 0, top: 0 };
                            const rect = board.getBoundingClientRect();
                            return { left: rect.left, top: rect.top };
                        }
                    ''')
                source_x = self.board_rect['left'] + source_coords['x']
                source_y = self.board_rect['top'] + source_coords['y']
                target_x = self.board_rect['left'] + target_coords['x']
                target_y = self.board_rect['top'] + target_coords['y']

                print(f"Экранные координаты: {source_square} -> ({source_x}, {source_y}), {target_square} -> ({target_x}, {target_y})")

                await self.page.mouse.move(source_x, source_y, steps=5)
                await self.page.mouse.down()
                await self.page.mouse.move(target_x, target_y, steps=5)
                await self.page.mouse.up()
                print(f"Выполнен ход: {move}, время: {(time.time() - t_start):.3f}s")
                return True
            else:
                print(f"Не удалось вычислить координаты: source={source_coords}, target={target_coords}")
                return False
        except Exception as e:
            print(f"Ошибка выполнения хода: {e}")
            return False

    async def is_my_turn(self, fen):
        try:
            t_start = time.time()
            active_color = fen.split(' ')[1]
            my_color = 'w' if self.orientation == 'white' else 'b'
            is_my_turn = active_color == my_color
            print(f"Проверка хода: активный цвет={active_color}, мой цвет={my_color}, мой ход={is_my_turn}, время: {(time.time() - t_start):.3f}s")
            return is_my_turn
        except Exception as e:
            print(f"Ошибка проверки хода: {e}")
            return False

    async def wait_for_opponent(self):
        try:
            t_start = time.time()
            current_fen = await self.get_board_position()
            if not current_fen:
                print("Не удалось получить начальную позицию")
                return False
            start_time = time.time()
            while time.time() - start_time < 30:
                if not self.page or self.page.is_closed():
                    print("Страница закрыта, ожидание прервано")
                    return False
                new_fen = await self.get_board_position()
                if not new_fen:
                    print("Не удалось получить новую позицию")
                    return False
                if new_fen != current_fen:
                    print(f"Ход противника обнаружен, время: {(time.time() - t_start):.3f}s")
                    if await self.is_my_turn(new_fen):
                        return True
                await asyncio.sleep(0.1)
            print("Таймаут ожидания хода противника")
            return False
        except Exception as e:
            print(f"Ошибка ожидания хода: {e}")
            return False

    async def wait_for_game_start(self):
        try:
            print("Ожидаем начала игры...")
            await self.page.wait_for_load_state('domcontentloaded', timeout=30000)
            await self.page.wait_for_selector('cg-board', timeout=30000)
            start_time = time.time()
            opponent = await self.page.query_selector('a.user-link, div.player, div.user-info')
            while not opponent and time.time() - start_time < 30:
                await asyncio.sleep(1)
                opponent = await self.page.query_selector('a.user-link, div.player, div.user-info')
            if opponent:
                print("Противник подключился, игра началась")
                await asyncio.sleep(random.uniform(1, 2))
                return True
            else:
                print("Таймаут ожидания противника")
                return False
        except Exception as e:
            print(f"Ошибка ожидания начала игры: {e}")
            return False

    async def start(self):
        try:
            await self.setup_browser()
            self.initialize_stockfish()

            self.stockfish.update_engine_parameters({
                "Threads": SETTING.threads,
                "Hash": 128
            })

            await self.page.goto("https://lichess.org/storm", wait_until="domcontentloaded")
            await self.emulate_human_behavior()

            same_fen_count = 0
            last_fen = None

            while True:
                t_start = time.time()
                if not self.page or self.page.is_closed():
                    print("Страница закрыта, завершаем")
                    break

                fen = await self.get_board_position()
                if not fen:
                    print("Не удалось получить позицию")
                    continue

                if fen == last_fen:
                    same_fen_count += 1
                else:
                    same_fen_count = 0
                    last_fen = fen

                if same_fen_count >= 5:
                    print("FEN не меняется 5 итераций — сохраняем и рестартим.")
                    with open("failed_fen.txt", "w", encoding="utf-8") as f:
                        f.write(fen)
                    html_content = await self.page.content()
                    with open("failed_position.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    return

                print(f"Решаем задачу, FEN: {fen}")
                if not self.stockfish.is_fen_valid(fen):
                    print(f"Некорректный FEN: {fen} — сохраняем и выходим.")
                    with open("failed_fen.txt", "w", encoding="utf-8") as f:
                        f.write(fen)
                    html_content = await self.page.content()
                    with open("failed_position.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    break

                try:
                    self.stockfish.set_fen_position(fen)
                    best_move = self.stockfish.get_best_move_time(SETTING.thinking_time)
                    print(f"Лучший ход от Stockfish: {best_move}")
                except Exception as e:
                    print(f"Stockfish крэшнулся: {e}")
                    try:
                        self.stockfish = Stockfish(path="C:/Program Files (x86)/stockfish/stockfish.exe")
                        self.initialize_stockfish()
                    except Exception as inner:
                        print(f"Не удалось пересоздать движок: {inner}")
                    continue


                if not await self.make_move(best_move):
                    print("Ход не выполнен")
                    continue

                # ⬇️ Обработка превращения (если ход включает превращение)
                if len(best_move) == 5 and best_move[4] in 'qrbn':
                    promo_letter = best_move[4]
                    promo_map = {'q': 'queen', 'r': 'rook', 'b': 'bishop', 'n': 'knight'}
                    piece_name = promo_map.get(promo_letter)
                    if piece_name:
                        selector = f'#promotion-choice piece.{piece_name}'
                        try:
                            piece_element = await self.page.query_selector(selector)
                            if piece_element:
                                square_element = await piece_element.evaluate_handle('node => node.parentElement')
                                await square_element.click()
                                print(f"Выбрана фигура для превращения: {piece_name}")
                            else:
                                print(f"Не удалось найти фигуру {piece_name} для превращения")
                        except Exception as e:
                            print(f"Ошибка при выборе фигуры {piece_name}: {e}")
                    else:
                        print(f"Неизвестный символ превращения: {promo_letter}")
                
                try:
                    # Дождаться обновления DOM после хода — кол-во <piece> должно измениться
                    await self.page.wait_for_function(
                        "(() => document.querySelectorAll('cg-board piece').length !== window.__lastPieceCount)",
                        timeout=2000
                    )
                except:
                    print("DOM, похоже, не обновился вовремя.")

                # сохранить актуальное число фигур
                await self.page.evaluate("window.__lastPieceCount = document.querySelectorAll('cg-board piece').length")

                self.orientation = None
                print(f"Общее время хода: {(time.time() - t_start):.3f}s")
                await asyncio.sleep(0.1) 

        except Exception as e:
            print(f"Ошибка в игровом цикле: {e}")
        finally:
            print("Закрываемся")
            await asyncio.sleep(300)
            await self.close()



if __name__ == "__main__":
    asyncio.run(Chess().start())