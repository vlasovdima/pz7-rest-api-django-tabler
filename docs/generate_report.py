"""Скрипт генерации отчёта по ПЗ №7 строго по ГОСТ 7.32-2017."""

import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_WORKSPACE = os.path.dirname(PROJECT_DIR)
HELPER_DIR = os.path.abspath(
    os.path.join(ROOT_WORKSPACE, ".agents", "skills", "gost-student-reports", "scripts")
)
sys.path.insert(0, HELPER_DIR)

from gost_docx import GostReport


def build_report():
    rep = GostReport(base_dir=PROJECT_DIR)

    # 1. Титульный лист
    rep.title_page(
        work_type="Практическое занятие № 7",
        work_subtitle="ОТЧЁТ ПО ПРАКТИЧЕСКОМУ ЗАНЯТИЮ",
        discipline="«Разработка веб-приложений»",
        topic="«Интеграция frontend, backend и базы данных через REST API»",
        student_group="М3О-236БВ-25",
        student_name="Власов Дмитрий",
        teacher_name="Александрова С.С.",
        city="Москва",
        year="2026",
    )

    # 2. Содержание (страница 2)
    rep.toc(
        [
            ("1 Цель работы и общая архитектура приложения", 3),
            ("2 Структура моделей и серверная логика REST API", 4),
            ("3 Клиентский интерфейс на Tabler и JavaScript", 6),
            ("4 Результаты тестирования и проверка целостности данных", 8),
            ("Заключение", 11),
            ("Список использованных источников", 12),
        ]
    )

    # Раздел 1
    rep.heading("1 Цель работы и общая архитектура приложения", level=1)
    rep.para(
        "В седьмом практическом занятии я расширил существующий учебный портал на Django новым "
        "интерактивным разделом «Центр управления заявками». Главная задача состояла в том, чтобы "
        "связать клиентскую часть на Tabler и JavaScript с серверным REST API на Django REST Framework "
        "и базой данных SQLite без полной перезагрузки страницы при каждом действии."
    )
    rep.para(
        "Работа строится по сквозной цепочке: браузер отправляет асинхронный HTTP-запрос через Fetch API "
        "с CSRF-токеном и сессионной cookie. На стороне сервера DRF проверяет права доступа, прогоняет "
        "данные через сериализатор и бизнес-правила, после чего обращается к базе данных через Django ORM. "
        "В ответ клиент получает JSON и сразу перерисовывает таблицу заявок и карточки статистики."
    )

    rep.diagram(
        "Упрощённая схема взаимодействия компонентов приложения",
        """[ Frontend: Tabler + JS (Fetch API + CSRF) ]
                      |
                      v  HTTP-запрос (JSON)
[ REST API: Django REST Framework + SessionAuth ]
                      |
                      v  Валидация + Бизнес-правила
[ Backend: Django ORM (Category, Ticket) ]
                      |
                      v  SQL-запросы
[ База данных: SQLite (db.sqlite3) ]
                      |
                      +--> Ответ API (JSON / HTTP-статус) -> Обновление DOM""",
    )

    # Раздел 2
    rep.heading("2 Структура моделей и серверная логика REST API", level=1)
    rep.para(
        "Для хранения данных в приложении tickets я описал две связанные модели: справочник категорий "
        "Category и основную сущность Ticket. В модели Ticket внешний ключ на категорию задан с параметром "
        "on_delete=PROTECT, поэтому база не даст удалить категорию, пока к ней привязана хотя бы одна заявка. "
        "Поле owner связывает каждую запись с конкретным пользователем, а статусы ограничены перечислением "
        "TextChoices («Новая», «В работе», «Выполнена»)."
    )

    rep.table(
        "Структура моделей приложения tickets",
        ["Модель", "Поле", "Тип и ограничения", "Назначение"],
        [
            ["Category", "name", "CharField(120), unique=True", "Название категории заявки"],
            ["Ticket", "title", "CharField(200)", "Краткий заголовок заявки"],
            ["Ticket", "description", "TextField(blank=True)", "Подробное описание проблемы"],
            ["Ticket", "category", "ForeignKey(Category, PROTECT)", "Ссылка на категорию"],
            ["Ticket", "owner", "ForeignKey(User, CASCADE)", "Автор заявки"],
            ["Ticket", "status", "CharField(20), choices=Status", "Текущий статус: new, progress, done"],
            ["Ticket", "created_at", "DateTimeField(auto_now_add)", "Время создания записи"],
        ],
    )

    rep.para(
        "В файле serializers.py я реализовал проверку входных данных и бизнес-правило переходов. "
        "Во-первых, заголовок заявки очищается от крайних пробелов и должен содержать минимум 5 символов. "
        "Во-вторых, новая заявка всегда создаётся в статусе «Новая», а дальнейшая смена статуса идёт "
        "строго по цепочке: «Новая» -> «В работе» -> «Выполнена». Попытка перепрыгнуть этап сервер отклоняет "
        "с кодом 400 Bad Request, даже если запрос отправили вручную в обход браузера."
    )

    rep.listing(
        "Валидация переходов статусов в TicketSerializer (src/tickets/serializers.py)",
        """def validate(self, attrs):
    if self.instance is None:
        if attrs.get("status", Ticket.Status.NEW) != Ticket.Status.NEW:
            raise serializers.ValidationError(
                {"status": "Новая заявка должна иметь статус «Новая»."}
            )
        return attrs

    old_status = self.instance.status
    new_status = attrs.get("status", old_status)
    allowed = {
        Ticket.Status.NEW: {Ticket.Status.PROGRESS},
        Ticket.Status.PROGRESS: {Ticket.Status.DONE},
        Ticket.Status.DONE: set(),
    }
    if new_status != old_status and new_status not in allowed[old_status]:
        raise serializers.ValidationError(
            {"status": "Недопустимый переход статуса."}
        )
    return attrs""",
    )

    rep.para(
        "Разграничение доступа настроено во вьюсете TicketViewSet. Метод get_queryset() фильтрует "
        "выборку по owner=self.request.user, поэтому чужая заявка при обращении по ID возвращает 404 Not Found. "
        "При создании записи метод perform_create() сам подставляет текущего авторизованного пользователя."
    )

    rep.table(
        "Маршруты REST API и веб-интерфейса",
        ["Метод", "URL-маршрут", "Назначение"],
        [
            ["GET", "/tickets/", "Страница центра управления заявками (требует вход)"],
            ["GET", "/api/categories/", "Получение списка категорий из БД"],
            ["GET", "/api/tickets/", "Получение списка заявок текущего пользователя"],
            ["GET", "/api/tickets/?status=new&search=...", "Фильтрация по статусу и поиск по тексту"],
            ["POST", "/api/tickets/", "Создание новой заявки"],
            ["PATCH", "/api/tickets/{id}/", "Редактирование заявки и смена статуса"],
            ["DELETE", "/api/tickets/{id}/", "Удаление заявки текущего пользователя"],
        ],
    )

    # Раздел 3
    rep.heading("3 Клиентский интерфейс на Tabler и JavaScript", level=1)
    rep.para(
        "Шаблон dashboard.html наследует базовый макет портала на Tabler. Сверху выводятся три карточки "
        "со счётчиками («Всего заявок», «В работе», «Выполнено»), ниже расположена форма создания заявки, "
        "строка поиска, фильтр по статусу и таблица записей. Все пользовательские строки вставляются в DOM "
        "через свойство textContent, чтобы исключить выполнение случайной HTML-разметки."
    )
    rep.para(
        "При разработке клиентского скрипта app.js возникла практическая проблема: стандартная обработка "
        "ошибок DRF возвращает JSON-словарь вида {\"title\": [\"...\"]}, и в раннем варианте пользователь "
        "видел на экране сырой технический текст. Я написал функцию formatApiError(), которая переводит "
        "названия полей на русский язык и собирает понятное сообщение в блоке alert."
    )
    rep.para(
        "Для редактирования и удаления я использовал модальные окна Tabler. В окне редактирования "
        "недопустимые переходы статусов сразу блокируются через атрибут disabled, а при нажатии «Удалить» "
        "открывается отдельное окно подтверждения с кнопкой отмены."
    )

    rep.figure(
        "screenshots/1_main_dashboard.png",
        "Главная страница центра управления заявками на Tabler",
    )
    rep.figure(
        "screenshots/4_edit_modal.png",
        "Модальное окно редактирования заявки и выбора допустимого статуса",
    )
    rep.figure(
        "screenshots/5_delete_modal.png",
        "Модальное окно подтверждения удаления заявки",
    )

    # Раздел 4
    rep.heading("4 Результаты тестирования и проверка целостности данных", level=1)
    rep.para(
        "Чтобы проверить приложение без ручных допущений, я написал скрипт автотестов tests/test_all.py "
        "на базе APIClient из Django REST Framework. При первом запуске миграций выяснилось, что команда "
        "makemigrations не увидела новое приложение без каталога migrations, поэтому я явно вызвал "
        "makemigrations tickets и применил схему к SQLite."
    )
    rep.para(
        "Отдельная серия проверок касалась отклонения некорректных операций: анонимный запрос к /api/tickets/ "
        "получает 403 Forbidden, заголовок короче 5 символов и попытка перескока «Новая -> Выполнена» "
        "отклоняются с кодом 400 Bad Request, а попытка второго пользователя открыть или удалить чужую заявку "
        "завершается ответом 404 Not Found. Целостность связей подтвердилась тестом на ProtectedError: "
        "удалить категорию с привязанной заявкой нельзя."
    )

    rep.figure(
        "screenshots/2_validation_error.png",
        "Отображение серверной ошибки валидации в интерфейсе без технического JSON",
    )
    rep.figure(
        "screenshots/3_ticket_created.png",
        "Успешное создание новой заявки и обновление счётчиков без перезагрузки страницы",
    )

    rep.listing(
        "Протокол прохождения автотестов (python tests/test_all.py)",
        """[OK] Проверка 1: Отказ анонимному пользователю на /api/tickets/ (403 Forbidden)
[OK] Проверка 2: Открытие страницы /tickets/ авторизованным пользователем
[OK] Проверка 3: Загрузка справочника категорий из БД
[OK] Проверка 4: Создание заявки через POST и фактическое сохранение в БД
[OK] Проверка 5: Серверная валидация короткого названия (400 Bad Request)
[OK] Проверка 6: Запрет создания заявки сразу в статусе 'done'
[OK] Проверка 7: Серверный запрет перескока статуса (Новая -> Выполнена)
[OK] Проверка 8: Последовательный переход статуса (Новая -> В работе -> Выполнена)
[OK] Проверка 9: Фильтрация по статусу и текстовый поиск через query_params
[OK] Проверка 10: Изоляция чужих заявок (404 Not Found для другого пользователя)
[OK] Проверка 11: Целостность БД (on_delete=PROTECT на категории)
[OK] Проверка 12: Удаление заявки через DELETE и проверка отсутствия в БД
--------------------------------------------------
Все проверки успешно пройдены (12/12). Ошибок не обнаружено.""",
    )

    rep.github_repo_note("https://github.com/vlasovdima/pz7-rest-api-django-tabler")

    # Заключение
    rep.heading("Заключение", level=1)
    rep.para(
        "В ходе выполнения практического занятия № 7 я разобрался, как организовать полный цикл работы "
        "с данными: от формы на Tabler и асинхронных Fetch-запросов до валидации в сериализаторах DRF "
        "и сохранения в SQLite. Труднее всего было наладить аккуратный разбор ошибок ответа API на клиенте "
        "и согласовать блокировку недопустимых статусов в модальном окне с проверками на сервере. "
        "Все 12 автоматических проверок прошли успешно, интерфейс обновляется без перезагрузки страницы."
    )

    # Список использованных источников
    rep.sources(
        [
            "Django Documentation. Models, Querysets and Migrations [Электронный ресурс]. – URL: https://docs.djangoproject.com/ (дата обращения: 13.11.2026).",
            "Django REST Framework. Serializers, ViewSets and Permissions [Электронный ресурс]. – URL: https://www.django-rest-framework.org/ (дата обращения: 13.11.2026).",
            "Tabler UI Kit Documentation. Components, Forms and Modals [Электронный ресурс]. – URL: https://tabler.io/docs (дата обращения: 13.11.2026).",
            "MDN Web Docs. Using the Fetch API [Электронный ресурс]. – URL: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API (дата обращения: 13.11.2026).",
        ]
    )

    out_docs = os.path.join(PROJECT_DIR, "docs", "Отчет_ПЗ7_Власов_М3О-236БВ-25.docx")
    out_root = os.path.join(ROOT_WORKSPACE, "Отчет_ПЗ7_Власов_М3О-236БВ-25.docx")
    rep.save(out_docs)
    rep.save(out_root)


if __name__ == "__main__":
    build_report()
