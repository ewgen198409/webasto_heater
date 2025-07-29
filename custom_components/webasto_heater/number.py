"""Platform for number integration."""
import logging
from typing import List

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature, UnitOfTime

from . import DOMAIN, WebastoHeaterData

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Webasto Heater number platform."""
    webasto_data: WebastoHeaterData = hass.data[DOMAIN][config_entry.entry_id]

    # Добавляем числовые сущности для настроек
    numbers: List[WebastoHeaterNumber] = [
        WebastoHeaterNumber(
            webasto_data, 
            "pump_size", 
            "Размер насоса", 
            10, 100, 1, 
            "mdi:pump"
        ),
        WebastoHeaterNumber(
            webasto_data, 
            "heater_target", 
            "Целевая температура нагревателя", 
            150, 250, 1, 
            "mdi:thermometer-plus", 
            UnitOfTemperature.CELSIUS
        ),
        WebastoHeaterNumber(
            webasto_data, 
            "heater_min", 
            "Минимальная температура нагревателя", 
            140, 240, 1, 
            "mdi:thermometer-minus", 
            UnitOfTemperature.CELSIUS
        ),
        WebastoHeaterNumber(
            webasto_data, 
            "heater_overheat", 
            "Температура перегрева", 
            200, 300, 1, 
            "mdi:thermometer-alert", 
            UnitOfTemperature.CELSIUS
        ),
        WebastoHeaterNumber(
            webasto_data, 
            "heater_warning", 
            "Температура предупреждения", 
            180, 280, 1, 
            "mdi:thermometer-lines", 
            UnitOfTemperature.CELSIUS
        ),
        WebastoHeaterNumber(
            webasto_data, 
            "max_pwm_fan", 
            "Макс. ШИМ вентилятора", 
            0, 255, 1, 
            "mdi:fan-speed-1"
        ),
        WebastoHeaterNumber(
            webasto_data, 
            "glow_brightness", 
            "Яркость свечи накаливания", 
            0, 255, 1, 
            "mdi:lightbulb-on"
        ),
        WebastoHeaterNumber(
            webasto_data, 
            "glow_fade_in_duration", 
            "Время розжига свечи", 
            0, 60000, 100, 
            "mdi:timer-outline", 
            UnitOfTime.MILLISECONDS
        ),
        WebastoHeaterNumber(
            webasto_data, 
            "glow_fade_out_duration", 
            "Время затухания свечи", 
            0, 60000, 100, 
            "mdi:timer-off-outline", 
            UnitOfTime.MILLISECONDS
        ),
    ]
    async_add_entities(numbers)

class WebastoHeaterNumber(NumberEntity):
    """Representation of a Webasto Heater Number entity."""

    def __init__(
        self, 
        webasto_data: WebastoHeaterData, 
        key: str, 
        name: str, 
        min_value: float, 
        max_value: float, 
        step: float, 
        icon: str, 
        unit: str = None
    ):
        """Initialize the number entity."""
        self._webasto_data = webasto_data
        self._key = key
        
        self._attr_name = f"Webasto {name}"
        self._attr_unique_id = f"webasto_{key}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_value = None
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_available = True

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

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        self._webasto_data.add_listener(self._handle_data_update)
        await self._handle_data_update()

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks when entity is removed."""
        self._webasto_data.remove_listener(self._handle_data_update)

    async def _handle_data_update(self):
        """Handle data update from the WebSocket."""
        value = self._webasto_data.data.get(self._key)
        
        if value is not None:
            try:
                # Убеждаемся, что значение находится в допустимых пределах
                numeric_value = float(value)
                self._attr_native_value = max(
                    self._attr_native_min_value,
                    min(self._attr_native_max_value, numeric_value)
                )
            except (ValueError, TypeError) as err:
                _LOGGER.warning(
                    "Invalid value for %s: %s (error: %s)", 
                    self._key, value, err
                )
                self._attr_native_value = None
        else:
            self._attr_native_value = None

        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if not self._webasto_data.is_connected:
            _LOGGER.warning("Cannot set value for %s: WebSocket not connected", self._key)
            return

        # Проверяем, что значение в допустимых пределах
        if not (self._attr_native_min_value <= value <= self._attr_native_max_value):
            _LOGGER.error(
                "Value %s for %s is out of range [%s, %s]",
                value, self._key, self._attr_native_min_value, self._attr_native_max_value
            )
            return

        # Обновляем локальное состояние
        self._attr_native_value = value
        
        # Обновляем данные в WebSocket data manager
        # Это нужно для корректной работы кнопки "Сохранить настройки"
        self._webasto_data._data[self._key] = int(value)
        
        self.async_write_ha_state()
        
        _LOGGER.debug("Set %s to %s (will be saved when 'Save Settings' is pressed)", self._key, value)