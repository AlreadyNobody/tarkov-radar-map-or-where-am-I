import subprocess
import sys
import os
import time
import json

# Функция для установки пакета через pip
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


# Пытаемся импортировать необходимые модули; если не удаётся – устанавливаем их
try:
    import pyautogui
except ImportError:
    print("pyautogui не найден, устанавливаю...")
    install("pyautogui")
    import pyautogui

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("playwright не найден, устанавливаю...")
    install("playwright")
    from playwright.sync_api import sync_playwright

try:
    import keyboard
except ImportError:
    print("keyboard не найден, устанавливаю...")
    install("keyboard")
    import keyboard

# Устанавливаем браузеры для Playwright
print("Устанавливаю браузеры для Playwright...")
subprocess.check_call([sys.executable, "-m", "playwright", "install"])

CONFIG_FILE = "config.json"
new_map_flag = False  # Глобальный флаг для выбора новой карты


# Функция для отладки: выводит имя каждой нажатой клавиши (при необходимости)
def debug_key(event):
    print("DEBUG: Нажата клавиша:", event.name)

# Если нужно отладить, можно раскомментировать следующую строку:
# keyboard.hook(debug_key)


def load_config():
    """Загружает конфигурацию из файла, если он существует."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Ошибка загрузки конфигурации:", e)
    return None


def save_config(config):
    """Сохраняет конфигурацию в файл."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Ошибка сохранения конфигурации:", e)


def get_config():
    """
    Если конфигурация уже существует, возвращает её.
    Иначе запрашивает путь к папке Документов и клавишу для скриншотов у пользователя,
    сохраняет и возвращает полученные настройки.
    """
    config = load_config()
    if not config:
        while True:
            documents_path = input("Укажите полный путь к папке Документов: ").strip()
            if os.path.isdir(documents_path):
                break
            else:
                print("Указанный путь не существует или не является папкой. Попробуйте еще раз.")
        screenshot_key = input("Укажите клавишу для скриншотов в Таркове (по умолчанию HOME): ").strip()
        if not screenshot_key:
            screenshot_key = "home"
        config = {
            "documents_path": documents_path,
            "screenshot_key": screenshot_key.lower()
        }
        save_config(config)
    return config


def get_newest_file(folder):
    """
    Возвращает имя самого нового файла в папке (без пути) или None, если файлов нет.
    """
    try:
        files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        if not files:
            return None
        newest = max(files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
        return newest
    except Exception as e:
        print("Ошибка при получении файлов из папки:", e)
        return None


def choose_map():
    """
    Выводит меню выбора карты и возвращает выбранное имя карты,
    которое подставляется в URL после /maps/.
    """
    maps = [
        {"name": "ground-zero", "desc": "эпицентр"},
        {"name": "woods",       "desc": "лес"},
        {"name": "factory",     "desc": "завод"},
        {"name": "customs",     "desc": "таможня"},
        {"name": "interchange", "desc": "развязка"},
        {"name": "shoreline",   "desc": "берег"},
        {"name": "reserve",     "desc": "резерв"},
        {"name": "lighthouse",  "desc": "маяк"},
        {"name": "streets",     "desc": "улицы таркова"},
        {"name": "lab",         "desc": "лаба"}
    ]
    print("\nВыберите карту (введите номер):")
    for idx, m in enumerate(maps):
        print(f"{idx} - {m['desc']}")

    while True:
        try:
            choice = int(input("Введите Id карты: ").strip())
            if 0 <= choice < len(maps):
                selected = maps[choice]["name"]
                print(f"Вы выбрали: {maps[choice]['desc']} ({selected})")
                return selected
            else:
                print("Неверный номер карты. Попробуйте еще раз.")
        except ValueError:
            print("Введите числовое значение.")


# Обработчик горячей клавиши F2 – устанавливает флаг для выбора новой карты
def on_f2():
    global new_map_flag
    new_map_flag = True


def non_blocking_wait(total_seconds, interval=0.2):
    """Осуществляет ожидание total_seconds, проверяя каждые interval секунд."""
    elapsed = 0
    while elapsed < total_seconds:
        time.sleep(interval)
        elapsed += interval


def main():
    global new_map_flag
    config = get_config()
    documents_path = config["documents_path"]
    screenshot_key = config["screenshot_key"]

    # Изначально выбираем карту
    selected_map = choose_map()
    url = f"https://tarkov-market.com/maps/{selected_map}"
    print(f"\nОткрывается страница: {url}")

    with sync_playwright() as p:
        # Запуск Chromium в maximized режиме
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        # Используем реальные размеры окна ОС, задавая no_viewport=True
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        # Переход на сайт с выбранной картой
        page.goto(url)
        page.wait_for_load_state("networkidle", timeout=60000)
        non_blocking_wait(3)

        # Ждем появления и кликаем по первичному элементу
        selector_button = "#__nuxt > div > div > div.page-content > div > div > div.panel_top > div > div.d-flex.ml-15.fs-0 > button"
        page.wait_for_selector(selector_button, state="visible", timeout=30000)
        page.click(selector_button)
        print("Первичный клик выполнен\n")

        # Запоминаем последний файл в папке для обнаружения изменений
        last_file = get_newest_file(documents_path)
        selector_input = "#__nuxt > div > div > div.page-content > div > div > div.panel_top > div > div.d-flex.ml-15.fs-0 > input[type=text]"

        # Регистрируем горячую клавишу F2; если отладка покажет другое имя, замените "f2" на нужное
        keyboard.add_hotkey("f2", on_f2)
        print("Нажмите F2 для выбора новой карты\n")

        try:
            while True:
                # Если флаг выбранной новой карты установлен, переходим к выбору новой карты
                if new_map_flag:
                    new_map_flag = False
                    print("Горячая клавиша F2 сработала – выбор новой карты")
                    selected_map = choose_map()
                    url = f"https://tarkov-market.com/maps/{selected_map}"
                    print(f"Переход на страницу: {url}")
                    page.goto(url)
                    page.wait_for_load_state("networkidle", timeout=60000)
                    non_blocking_wait(3)
                    page.wait_for_selector(selector_button, state="visible", timeout=30000)
                    page.click(selector_button)
                    print("Первичный клик выполнен для новой карты\n")
                    non_blocking_wait(2)

                # Имитация нажатия клавиши для создания скриншота
                pyautogui.press(screenshot_key)
                print(f"Нажата клавиша {screenshot_key.upper()} на ПК")

                non_blocking_wait(1)

                # Проверка наличия нового файла в указанной папке
                new_file = get_newest_file(documents_path)
                if new_file and new_file != last_file:
                    last_file = new_file
                    js_code = f"""
                    () => {{
                        const input = document.querySelector('{selector_input}');
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeInputValueSetter.call(input, "{new_file}");
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                    """
                    page.evaluate(js_code)
                    print(f"Обнаружен новый файл: {new_file} и его имя вставлено с триггерами")

                    # Удаляем файл после вставки
                    file_path = os.path.join(documents_path, new_file)
                    try:
                        os.remove(file_path)
                        print(f"Файл '{new_file}' удалён из папки.")
                    except Exception as e:
                        print(f"Ошибка при удалении файла '{new_file}':", e)

                    non_blocking_wait(5)
        except KeyboardInterrupt:
            print("Остановка цикла по запросу пользователя.")

        input("Нажмите Enter для закрытия браузера...")
        browser.close()


if __name__ == "__main__":
    main()
