# ПЗ №7. Интеграция frontend, backend и базы данных через REST API

Студент: Власов Дмитрий (группа М3О-236БВ-25)  
Дисциплина: Разработка веб-приложений

## Описание проекта

Интерактивный раздел «Центр управления заявками», интегрированный в учебный портал на Django с использованием Django REST Framework, JavaScript (Fetch API + CSRF) и Tabler UI.

Реализованные возможности:
- Связанные модели `Category` и `Ticket` (внешний ключ с `on_delete=PROTECT` и привязкой к владельцу `owner`).
- REST API на базе DRF (`/api/categories/`, `/api/tickets/`, фильтрация по статусу и поиск).
- Серверная валидация длины заголовка (минимум 5 символов) и бизнес-правило последовательного перехода статусов (`Новая -> В работе -> Выполнена`).
- Разграничение доступа: сессионная аутентификация и изоляция заявок по текущему пользователю.
- Асинхронный интерфейс на Tabler без перезагрузки страницы, с модальными окнами редактирования и подтверждения удаления.

## Запуск проекта

1. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Применить миграции и загрузить тестовые данные:
   ```bash
   cd src
   python manage.py makemigrations
   python manage.py migrate
   python manage.py seed_demo
   python manage.py seed_tickets
   ```
3. Запустить сервер разработки:
   ```bash
   python manage.py runserver
   ```
4. Открыть в браузере `http://127.0.0.1:8000/tickets/` (тестовый вход: `vlasov` / `StudentPass123!`).

## Запуск автотестов

```bash
python tests/test_all.py
```

## Репозиторий

Исходный код проекта доступен на GitHub: https://github.com/vlasovdima/pz7-rest-api-django-tabler
