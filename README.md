# Webasto Heater Integration for Home Assistant

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-000000?style=for-the-badge&logo=home-assistant&logoColor=white)
![HACS](https://img.shields.io/badge/HACS-Custom%20Integration-orange?style=for-the-badge&logo=home-assistant&logoColor=white)

Эта интеграция позволяет управлять и мониторить ваш автономный отопитель Webasto через контроллер на ESP8266, интегрируя его в Home Assistant.

## ✨ Особенности

* Мониторинг в реальном времени: температура выхлопа, скорость вентилятора, расход топлива и т.д.
* Управление режимами работы (включение/выключение, прокачка топлива).
* Настройка параметров отопителя: размер насоса, целевая температура, яркость свечи накаливания и другие.
* Визуальная карточка Lovelace для удобного управления.

## 🚀 Установка

### Через HACS (рекомендуется)

1.  Убедитесь, что у вас установлен [HACS](https://hacs.xyz/).
2.  В Home Assistant, перейдите в **HACS -> Integrations -> Трехточечное меню (вверху справа) -> Custom repositories**.
3.  Вставьте URL вашего репозитория GitHub: `https://github.com/your_username/webasto_heater` и выберите **Category: Integration**. Нажмите "Add repository".
4.  В Home Assistant, перейдите в **HACS -> Frontend -> Трехточечное меню (вверху справа) -> Custom repositories**.
5.  Вставьте URL вашего репозитория GitHub: `https://github.com/your_username/webasto_heater` и выберите **Category: Lovelace**. В поле **"Path"** введите `lovelace-webasto-heater-card/webastoheater-card.js`. Нажмите "Add repository".
6.  Перезагрузите Home Assistant.

### Вручную

1.  Создайте каталог `custom_components/webasto_heater/` в вашей конфигурационной папке Home Assistant.
2.  Скопируйте все файлы из каталога `custom_components/webasto_heater/` вашего репозитория в только что созданный каталог.
3.  Создайте каталог `www/community/lovelace-webasto-heater-card/` в вашей конфигурационной папке Home Assistant.
4.  Скопируйте файл `webastoheater-card.js` из каталога `lovelace-webasto-heater-card/` вашего репозитория в `www/community/lovelace-webasto-heater-card/`.
5.  Добавьте следующую строку в ваш файл `configuration.yaml` или через UI:
    ```yaml
    lovelace:
      resources:
        - url: /hacsfiles/lovelace-webasto-heater-card/webastoheater-card.js
          type: module
    ```
    (Если вы используете HACS, этот шаг не требуется для карточки, так как HACS добавит ресурс автоматически).
6.  Перезагрузите Home Assistant.

## ⚙️ Настройка интеграции

1.  После перезагрузки Home Assistant, перейдите в **Настройки -> Устройства и службы -> Добавить интеграцию**.
2.  Найдите "Webasto Heater" и следуйте инструкциям для ввода IP-адреса вашего устройства.

## 🖼️ Использование карточки Lovelace

Как только интеграция настроена, вы можете добавить пользовательскую карточку на вашу панель Lovelace.

1.  Откройте панель Lovelace.
2.  Нажмите на три точки в правом верхнем углу и выберите **"Редактировать панель"**.
3.  Нажмите **"Добавить карточку"**.
4.  Выберите **"Custom: Webasto Heater Card"** или **"Custom: custom-element"** и вставьте следующую конфигурацию:

    ```yaml
    type: custom:webastoheater-card
    entity_prefix: webasto
    # Или укажите сущности явно:
    # burn_entity: binary_sensor.webasto_heater_burn_active
    # ... и так далее для всех нужных сущностей
    ```

    Вы можете использовать `entity_prefix` если все ваши сущности имеют общий префикс, или указать каждую сущность явно, как показано в `webastoheater-card.js`.

    Пример конфигурации для карточки с префиксом:
    ```yaml
    type: custom:webastoheater-card
    entity_prefix: webasto
    ```
    Это позволит карточке автоматически находить сущности с префиксом `webasto`, такие как `webasto_heater_exhaust_temp`, `webasto_heater_burn_active` и т.д.

## Troubleshooting

* **"Не удается подключиться к устройству"**: Убедитесь, что IP-адрес введен верно и ESP8266 с Webasto-контроллером доступен в вашей сети. Проверьте фаерволлы.
* **Карточка не отображается**: Убедитесь, что вы правильно добавили ресурс Lovelace. Проверьте консоль браузера на наличие ошибок.

---
**Разработал:** [Ваше Имя / Ваш GitHub Username](https://github.com/your_username)
