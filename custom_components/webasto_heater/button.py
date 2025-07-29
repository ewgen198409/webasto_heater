"""Platform for button integration."""
import logging
from typing import List, Dict, Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, WebastoHeaterData

_LOGGER = logging.getLogger(__name__)

# Словарь для сопоставления внутренних ключей настроек с суффиксами entity_id в Home Assistant
# Эти суффиксы должны соответствовать транслитерированным именам из strings.json
SETTING_ENTITIES = {
    "pump_size": "razmer_nasosa",
    "heater_target": "tselevaia_temperatura_nagrevatelia",
    "heater_min": "minimalnaia_temperatura_nagrevatelia",
    "heater_overheat": "temperatura_peregreva",
    "heater_warning": "temperatura_preduprezhdenia",
    "max_pwm_fan": "maks_shim_ventilatora",
    "glow_brightness": "iarkost_svechi_nakalivaniia",
    "glow_fade_in_duration": "vremia_rozzhiga_svechi",
    "glow_fade_out_duration": "vremia_zatukhaniia_svechi",
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Webasto Heater button platform."""
    webasto_data: WebastoHeaterData = hass.data[DOMAIN][config_entry.entry_id]

    # Добавляем кнопки
    buttons: List[WebastoHeaterButton] = [
        WebastoHeaterButton(webasto_data, "toggle_burn", "Включить / Выключить", "ENTER"),
        WebastoHeaterButton(webasto_data, "up_mode", "Режим Вверх", "UP"),
        WebastoHeaterButton(webasto_data, "down_mode", "Режим Вниз", "DOWN"),
        WebastoHeaterButton(webasto_data, "fuel_pump", "Прокачка топлива", "FP"),
        WebastoHeaterButton(webasto_data, "clear_fail", "Сбросить ошибку", "CF"),
        WebastoHeaterSaveSettingsButton(webasto_data), # Отдельная кнопка для сохранения настроек
        WebastoHeaterButton(webasto_data, "reset_settings", "Сбросить настройки", "RESET_SETTINGS"),
        WebastoHeaterButton(webasto_data, "load_settings", "Загрузить настройки", "GET_SETTINGS"),
        WebastoHeaterButton(webasto_data, "reset_wifi", "Сбросить Wi-Fi", "RESET_WIFI"),
        WebastoHeaterButton(webasto_data, "reboot_esp", "Перезагрузить ESP", "REBOOT_ESP"),
        WebastoHeaterButton(webasto_data, "reset_fuel_consumption", "Сбросить потребление топлива", "RESET_FUEL_CONSUMPTION"),
        WebastoHeaterButton(webasto_data, "enable_logging", "Включить логирование", "LOG_ON"),
        WebastoHeaterButton(webasto_data, "disable_logging", "Выключить логирование", "LOG_OFF"),
    ]
    async_add_entities(buttons)


class WebastoHeaterButton(ButtonEntity):
    """Representation of a Webasto Heater Button."""

    def __init__(self, webasto_data: WebastoHeaterData, key: str, name: str, command: str):
        """Initialize the button."""
        self._webasto_data = webasto_data
        self._key = key
        self._command = command
        self._attr_name = f"Webasto {name}"
        self._attr_unique_id = f"webasto_{key}" # Используем оригинальный ключ для unique_id
        
        # Устанавливаем иконку на основе ключа, если она не задана явно в strings.json
        # Home Assistant автоматически подбирает иконку, если она есть в strings.json
        # или если device_class соответствует. Можно задать явно, если нужно.
        # self._attr_icon = icon # Если иконка передается
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "webasto_heater_main")},
            name="Webasto Heater",
            manufacturer="Custom",
            model="ESP8266 Webasto",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._webasto_data.is_connected

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Button %s pressed. Sending command: %s", self._key, self._command)
        success = await self._webasto_data.send_command(self._command)
        if success:
            _LOGGER.info("Successfully sent command: %s", self._command)
        else:
            _LOGGER.error("Failed to send command: %s", self._command)

class WebastoHeaterSaveSettingsButton(ButtonEntity):
    """Representation of a button to save settings to the Webasto heater."""

    def __init__(self, webasto_data: WebastoHeaterData):
        """Initialize the save settings button."""
        self._webasto_data = webasto_data
        self._attr_name = "Webasto Сохранить настройки"
        self._attr_unique_id = "webasto_save_settings"
        self._attr_icon = "mdi:content-save-outline" # Можно задать иконку явно

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "webasto_heater_main")},
            name="Webasto Heater",
            manufacturer="Custom",
            model="ESP8266 Webasto",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._webasto_data.is_connected

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Save settings button pressed.")
        settings_values = []
        missing_entities = []

        # Собираем текущие значения из всех number сущностей
        for esp_key, ha_entity_suffix in SETTING_ENTITIES.items():
            entity_id = f"number.{DOMAIN}_{ha_entity_suffix}"
            state = self.hass.states.get(entity_id)
            if state:
                try:
                    # Убедимся, что отправляем целое число, как ожидает ESP
                    # Используем int() для преобразования, так как ESP ожидает целые числа
                    value = int(float(state.state))
                    settings_values.append(f"{esp_key}={value}")
                except (ValueError, TypeError) as err:
                    _LOGGER.error(
                        "Invalid value for %s: %s (error: %s)",
                        entity_id, state.state, err
                    )
                    # Если значение невалидно, прерываем сохранение, чтобы не отправлять некорректные данные
                    return
            else:
                missing_entities.append(entity_id)

        if missing_entities:
            _LOGGER.error(
                "Cannot save settings: missing entities: %s",
                ", ".join(missing_entities)
            )
            return

        if not settings_values:
            _LOGGER.warning("No settings to save. settings_values is empty.")
            return

        # Формируем команду в том же формате, что и веб-интерфейс: "SET:param1=value1,param2=value2,..."
        full_command = "SET:" + ",".join(settings_values)

        _LOGGER.debug("Attempting to send save settings command: %s", full_command)
        success = await self._webasto_data.send_command(full_command)
        if success:
            _LOGGER.info("Successfully sent save settings command: %s", full_command)
        else:
            _LOGGER.error("Failed to send save settings command: %s", full_command)

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        # Этот метод нужен для того, чтобы Home Assistant знал, что сущность добавлена
        # и мог отслеживать ее доступность.
        pass

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks when entity is removed."""
        # Этот метод нужен для очистки ресурсов, если сущность удаляется.
        pass