"""Platform for binary sensor integration."""
import logging
from typing import List

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, WebastoHeaterData

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Webasto Heater binary sensor platform."""
    webasto_data: WebastoHeaterData = hass.data[DOMAIN][config_entry.entry_id]

    # Добавляем бинарные сенсоры
    binary_sensors: List[WebastoHeaterBinarySensor] = [
        WebastoHeaterBinarySensor(
            webasto_data, 
            "burn", 
            "Горение активно", 
            "mdi:fire", 
            BinarySensorDeviceClass.RUNNING
        ),
        WebastoHeaterBinarySensor(
            webasto_data, 
            "webasto_fail", 
            "Ошибка Webasto", 
            "mdi:alert-circle", 
            BinarySensorDeviceClass.PROBLEM
        ),
        WebastoHeaterBinarySensor(
            webasto_data, 
            "debug_glow_plug_on", 
            "Свеча накаливания", 
            "mdi:lightbulb-on-outline", 
            BinarySensorDeviceClass.LIGHT,
            EntityCategory.DIAGNOSTIC
        ),
        WebastoHeaterBinarySensor(
            webasto_data, 
            "fuel_pumping_active", 
            "Прокачка топлива", 
            "mdi:pump", 
            BinarySensorDeviceClass.RUNNING
        ),
        WebastoHeaterBinarySensor(
            webasto_data, 
            "logging_enabled", 
            "Логирование включено", 
            "mdi:file-document-outline", 
            BinarySensorDeviceClass.RUNNING,
            EntityCategory.DIAGNOSTIC
        ),
        WebastoHeaterBinarySensor(
            webasto_data, 
            "wifi_connected_status", 
            "Wi-Fi подключен", 
            "mdi:wifi", 
            BinarySensorDeviceClass.CONNECTIVITY,
            EntityCategory.DIAGNOSTIC
        ),
    ]
    async_add_entities(binary_sensors)

class WebastoHeaterBinarySensor(BinarySensorEntity):
    """Representation of a Webasto Heater Binary Sensor."""

    def __init__(
        self, 
        webasto_data: WebastoHeaterData, 
        key: str, 
        name: str, 
        icon: str, 
        device_class: BinarySensorDeviceClass,
        entity_category: EntityCategory = None
    ):
        """Initialize the binary sensor."""
        self._webasto_data = webasto_data
        self._key = key
        
        self._attr_name = f"Webasto {name}"
        self._attr_unique_id = f"webasto_{key}"
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_is_on = None
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
        data = self._webasto_data.data
        
        if self._key == "wifi_connected_status":
            # Специальная обработка для статуса Wi-Fi (3 = подключено)
            wifi_status = data.get("wifi_status")
            self._attr_is_on = wifi_status == 3
        else:
            # Для остальных binary sensor используем значения напрямую
            value = data.get(self._key)
            if isinstance(value, bool):
                self._attr_is_on = value
            elif isinstance(value, int):
                self._attr_is_on = bool(value)
            elif isinstance(value, str):
                # Обработка строковых значений
                self._attr_is_on = value.lower() in ('true', '1', 'on', 'yes')
            else:
                self._attr_is_on = bool(value) if value is not None else None

        self.async_write_ha_state()