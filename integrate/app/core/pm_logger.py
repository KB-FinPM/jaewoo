from datetime import datetime


def now_text() -> str:
    return datetime.now().strftime('%H:%M:%S')


def log_step(message: str):
    print(f'[{now_text()}] {message}')


def log_info(message: str):
    print(f'[{now_text()}] {message}')
