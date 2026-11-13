"""Автотесты для проверки REST API, бизнес-правил, валидации и прав доступа в ПЗ №7."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.insert(0, SRC_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.test import override_settings
from rest_framework.test import APIClient

from tickets.models import Category, Ticket


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
def run_checks():
    results = []

    # Готовим изолированных тестовых пользователей и категорию
    user_a, _ = User.objects.get_or_create(username="qa_user_a")
    user_a.set_password("TestPass123!")
    user_a.save()

    user_b, _ = User.objects.get_or_create(username="qa_user_b")
    user_b.set_password("TestPass123!")
    user_b.save()

    cat, _ = Category.objects.get_or_create(name="QA Тестовая категория")

    # Чистим возможные хвосты от прошлых прогонов
    Ticket.objects.filter(owner__in=[user_a, user_b]).delete()

    anon_client = APIClient()
    client_a = APIClient()
    client_b = APIClient()

    # 1. Анонимный доступ к API должен отклоняться (403 для SessionAuthentication)
    resp = anon_client.get("/api/tickets/")
    assert resp.status_code in (401, 403), f"Ожидался отказ для анонима, получено {resp.status_code}"
    results.append("Проверка 1: Отказ анонимному пользователю на /api/tickets/ (403 Forbidden)")

    # 2. Открытие HTML-страницы управления заявками после входа
    client_a.force_login(user_a)
    client_b.force_login(user_b)
    page_resp = client_a.get("/tickets/")
    assert page_resp.status_code == 200, f"Страница /tickets/ вернула {page_resp.status_code}"
    results.append("Проверка 2: Открытие страницы /tickets/ авторизованным пользователем")

    # 3. Получение категорий из БД
    cat_resp = client_a.get("/api/categories/")
    assert cat_resp.status_code == 200
    cat_names = [c["name"] for c in cat_resp.json()]
    assert "QA Тестовая категория" in cat_names
    results.append("Проверка 3: Загрузка справочника категорий из БД")

    # 4. Создание заявки и проверка сохранения в БД
    create_resp = client_a.post(
        "/api/tickets/",
        {"title": "  Настроить резервное копирование  ", "description": "Ежедневный бэкап", "category": cat.id},
        format="json",
    )
    assert create_resp.status_code == 201, f"Ошибка создания: {create_resp.data}"
    created = create_resp.json()
    ticket_id = created["id"]
    assert created["title"] == "Настроить резервное копирование"
    assert created["status"] == "new"
    assert Ticket.objects.filter(id=ticket_id, owner=user_a).exists()
    results.append("Проверка 4: Создание заявки через POST и фактическое сохранение в БД")

    # 5. Серверная валидация короткого названия (< 5 символов)
    short_resp = client_a.post(
        "/api/tickets/",
        {"title": "Тест", "category": cat.id},
        format="json",
    )
    assert short_resp.status_code == 400
    assert "title" in short_resp.json()
    results.append("Проверка 5: Серверная валидация короткого названия (400 Bad Request)")

    # 6. Запрет создания заявки сразу со статусом, отличным от "Новая"
    bad_init_resp = client_a.post(
        "/api/tickets/",
        {"title": "Сразу выполненная заявка", "category": cat.id, "status": "done"},
        format="json",
    )
    assert bad_init_resp.status_code == 400
    assert "status" in bad_init_resp.json()
    results.append("Проверка 6: Запрет создания заявки сразу в статусе 'done'")

    # 7. Запрет прямого перехода Новая -> Выполнена
    skip_resp = client_a.patch(
        f"/api/tickets/{ticket_id}/",
        {"status": "done"},
        format="json",
    )
    assert skip_resp.status_code == 400
    assert "status" in skip_resp.json()
    results.append("Проверка 7: Серверный запрет перескока статуса (Новая -> Выполнена)")

    # 8. Корректная последовательная смена статуса: Новая -> В работе -> Выполнена
    prog_resp = client_a.patch(f"/api/tickets/{ticket_id}/", {"status": "progress"}, format="json")
    assert prog_resp.status_code == 200 and prog_resp.json()["status"] == "progress"
    done_resp = client_a.patch(f"/api/tickets/{ticket_id}/", {"status": "done"}, format="json")
    assert done_resp.status_code == 200 and done_resp.json()["status"] == "done"
    assert Ticket.objects.get(id=ticket_id).status == "done"
    results.append("Проверка 8: Последовательный переход статуса (Новая -> В работе -> Выполнена)")

    # 9. Фильтрация по статусу и поиск
    filt_resp = client_a.get("/api/tickets/?status=done&search=резервное")
    assert filt_resp.status_code == 200
    assert len(filt_resp.json()) == 1
    results.append("Проверка 9: Фильтрация по статусу и текстовый поиск через query_params")

    # 10. Изоляция данных между пользователями (чужая заявка возвращает 404)
    foreign_get = client_b.get(f"/api/tickets/{ticket_id}/")
    foreign_del = client_b.delete(f"/api/tickets/{ticket_id}/")
    assert foreign_get.status_code == 404
    assert foreign_del.status_code == 404
    results.append("Проверка 10: Изоляция чужих заявок (404 Not Found для другого пользователя)")

    # 11. Защита целостности: нельзя удалить категорию, пока к ней привязаны заявки (PROTECT)
    protected_triggered = False
    try:
        cat.delete()
    except ProtectedError:
        protected_triggered = True
    assert protected_triggered, "Ожидалось ProtectedError при удалении используемой категории"
    results.append("Проверка 11: Целостность БД (on_delete=PROTECT на категории)")

    # 12. Удаление заявки владельцем и проверка удаления из БД
    del_resp = client_a.delete(f"/api/tickets/{ticket_id}/")
    assert del_resp.status_code == 204
    assert not Ticket.objects.filter(id=ticket_id).exists()
    results.append("Проверка 12: Удаление заявки через DELETE и проверка отсутствия в БД")

    # Убираем временную категорию после удаления заявки
    cat.delete()

    for line in results:
        print(f"[OK] {line}")
    print("-" * 50)
    print(f"Все проверки успешно пройдены ({len(results)}/{len(results)}). Ошибок не обнаружено.")


if __name__ == "__main__":
    run_checks()
