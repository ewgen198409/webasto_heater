"""Platform for sensor integration."""
import logging
from typing import List, Any, Dict

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature, PERCENTAGE, UnitOfFrequency, UnitOfVolume, UnitOfTime

from . import DOMAIN, WebastoHeaterData

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Webasto Heater sensor platform."""
    webasto_data: WebastoHeaterData = hass.data[DOMAIN][config_entry.entry_id]

    # Добавляем сенсоры
    sensors: List[WebastoHeaterSensor] = [
        WebastoHeaterSensor(
            webasto_data, 
            "exhaust_temp", 
            "Температура выхлопа", 
            UnitOfTemperature.CELSIUS, 
            "mdi:thermometer", 
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "fan_speed", 
            "Скорость вентилятора", 
            PERCENTAGE, 
            "mdi:fan", 
            None,
            SensorStateClass.MEASUREMENT
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "fuel_rate_hz", 
            "Расход топлива (Гц)", 
            UnitOfFrequency.HERTZ, 
            "mdi:fuel", 
            SensorDeviceClass.FREQUENCY,
            SensorStateClass.MEASUREMENT
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "burn_mode", 
            "Режим горения", 
            None, 
            "mdi:tune", 
            None,
            None
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "attempt", 
            "Попытка запуска", 
            None, 
            "mdi:counter", 
            None,
            None
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "message", 
            "Состояние", 
            None, 
            "mdi:information-outline", 
            None,
            None
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "wifi_ssid", 
            "SSID Wi-Fi", 
            None, 
            "mdi:wifi-marker", 
            None,
            None,
            EntityCategory.DIAGNOSTIC
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "wifi_ip", 
            "IP Адрес Wi-Fi", 
            None, 
            "mdi:ip-network", 
            None,
            None,
            EntityCategory.DIAGNOSTIC
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "total_fuel_consumed_liters", 
            "Текущее потребление топлива", 
            UnitOfVolume.LITERS, 
            "mdi:fuel", 
            SensorDeviceClass.VOLUME,
            SensorStateClass.TOTAL_INCREASING
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "fuel_consumption_per_hour", 
            "Расчетный расход за час", 
            f"{UnitOfVolume.LITERS}/{UnitOfTime.HOURS}", 
            "mdi:fuel", 
            None,
            SensorStateClass.MEASUREMENT
        ),
        WebastoHeaterSensor(
            webasto_data, 
            "current_state_text", 
            "Текущий режим", 
            None, 
            "mdi:state-machine", 
            None,
            None
        ),
    ]
    async_add_entities(sensors)

class WebastoHeaterSensor(SensorEntity):
    """Representation of a Webasto Heater Sensor."""

    def __init__(
        self, 
        webasto_data: WebastoHeaterData, 
        key: str, 
        name: str, 
        unit: str, 
        icon: str, 
        device_class: SensorDeviceClass,
        state_class: SensorStateClass = None,
        entity_category: EntityCategory = None
    ):
        """Initialize the sensor."""
        self._webasto_data = webasto_data
        self._key = key
        
        self._attr_name = f"Webasto {name}"
        self._attr_unique_id = f"webasto_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_native_value = None
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
        
        if self._key == "current_state_text":
            # Преобразуем числовой currentState в текстовое значение
            state_value = data.get("currentState")
            state_mapping = {
                0: "HIGH",
                1: "MID", 
                2: "LOW"
            }
            self._attr_native_value = state_mapping.get(state_value, "Неизвестно")
            
        elif self._key == "wifi_status_text":
            # Преобразуем числовой wifi_status в текстовое значение
            status_value = data.get("wifi_status")
            if status_value == 3:
                self._attr_native_value = "Подключено"
            else:
                self._attr_native_value = "Настройка AP"
                
        else:
            # Для всех остальных сенсоров используем значения напрямую
            raw_value = data.get(self._key)
            
            if raw_value is not None:
                # Преобразуем числовые значения
                if isinstance(raw_value, (int, float)):
                    self._attr_native_value = raw_value
                else:
                    # Для строковых значений
                    self._attr_native_value = str(raw_value)
            else:
                self._attr_native_value = None

        self.async_write_ha_state()