"""Скрипт автоматического снятия скриншотов работающего веб-интерфейса ПЗ №7."""

import os
import subprocess
import sys
import time
import urllib.request

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_DIR, "src")
SCREENSHOTS_DIR = os.path.join(PROJECT_DIR, "screenshots")
HELPER_DIR = os.path.abspath(
    os.path.join(PROJECT_DIR, "..", ".agents", "skills", "gost-student-reports", "scripts")
)
sys.path.insert(0, HELPER_DIR)

from screenshot_helper import ScreenshotSession


def wait_for_server(url, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("Сервер Django не успел запуститься.")


def main():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    port = 8017
    base_url = f"http://127.0.0.1:{port}"

    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"],
        cwd=SRC_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        wait_for_server(f"{base_url}/accounts/login/")
        with ScreenshotSession(width=1440, height=950) as session:
            # 1. Авторизация в системе
            session.navigate(f"{base_url}/accounts/login/", wait_seconds=1.2)
            session.eval_js(
                """
                document.querySelector('input[name="username"]').value = 'vlasov';
                document.querySelector('input[name="password"]').value = 'StudentPass123!';
                document.querySelector('form button[type="submit"]').click();
                """,
                wait_after=2.0,
            )

            # Переходим на /tickets/ и ждём подгрузки API
            session.navigate(f"{base_url}/tickets/", wait_seconds=2.0)
            session.capture_screenshot(os.path.join(SCREENSHOTS_DIR, "1_main_dashboard.png"))

            # 2. Демонстрация серверной валидации (слишком короткое название)
            session.eval_js(
                """
                document.getElementById('title').value = 'Тест';
                document.getElementById('create-submit-btn').click();
                """,
                wait_after=1.0,
            )
            session.capture_screenshot(os.path.join(SCREENSHOTS_DIR, "2_validation_error.png"))

            # 3. Успешное создание заявки без перезагрузки страницы
            session.eval_js(
                """
                document.getElementById('title').value = 'Настроить VPN для лаборатории';
                document.getElementById('description').value = 'Нужен доступ к стенду кафедры 317';
                document.getElementById('create-submit-btn').click();
                """,
                wait_after=1.2,
            )
            session.capture_screenshot(os.path.join(SCREENSHOTS_DIR, "3_ticket_created.png"))

            # 4. Модальное окно редактирования и смены статуса
            session.eval_js(
                """
                const btn = document.querySelector('#tickets-list button.btn-outline-primary');
                if (btn) btn.click();
                """,
                wait_after=0.8,
            )
            session.capture_screenshot(os.path.join(SCREENSHOTS_DIR, "4_edit_modal.png"))

            # Закрываем модалку редактирования и открываем модалку удаления
            session.eval_js(
                """
                const closeBtn = document.querySelector('#edit-ticket-modal .btn-close');
                if (closeBtn) closeBtn.click();
                """,
                wait_after=0.6,
            )
            session.eval_js(
                """
                const delBtn = document.querySelector('#tickets-list button.btn-outline-danger');
                if (delBtn) delBtn.click();
                """,
                wait_after=0.8,
            )
            session.capture_screenshot(os.path.join(SCREENSHOTS_DIR, "5_delete_modal.png"))
    finally:
        server.terminate()
        try:
            server.wait(timeout=3.0)
        except Exception:
            server.kill()


if __name__ == "__main__":
    main()
