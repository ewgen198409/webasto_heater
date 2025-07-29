"""The Webasto Heater integration."""
import asyncio
import logging
import json
from typing import Dict, Any, Callable, List

import websockets
from websockets.exceptions import WebSocketException, ConnectionClosed, ConnectionClosedOK

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import ConfigEntryNotReady

_LOGGER = logging.getLogger(__name__)

DOMAIN = "webasto_heater"
WEBSOCKET_URL = "ws://{host}:81/"

# Список платформ, которые будут загружены этой интеграцией
PLATFORMS = ["sensor", "binary_sensor", "button", "number"]

# Максимальное количество попыток переподключения
MAX_RECONNECT_ATTEMPTS = 10
RECONNECT_INTERVAL = 5


class WebastoHeaterData:
    """Manages the Webasto heater data and WebSocket connection."""

    def __init__(self, hass: HomeAssistant, host: str):
        """Initialize the data manager."""
        self.hass = hass
        self._host = host
        self._websocket = None
        self._listeners: List[Callable] = []
        self._data: Dict[str, Any] = {}
        self._is_connected = False
        self._reconnect_task = None
        self._stop_event = asyncio.Event()
        self._reconnect_attempts = 0

    @property
    def is_connected(self) -> bool:
        """Return true if WebSocket is connected."""
        return self._is_connected

    @property
    def data(self) -> Dict[str, Any]:
        """Return the latest data from the Webasto heater."""
        return self._data.copy()  # Возвращаем копию для безопасности

    def add_listener(self, update_callback: Callable):
        """Add a callback to be called when data updates."""
        if update_callback not in self._listeners:
            self._listeners.append(update_callback)

    def remove_listener(self, update_callback: Callable):
        """Remove a callback."""
        if update_callback in self._listeners:
            self._listeners.remove(update_callback)

    async def connect(self) -> bool:
        """Initial connection to WebSocket."""
        try:
            await self._connect_websocket()
            return True
        except Exception as err:
            _LOGGER.error("Failed to establish initial connection: %s", err)
            return False

    async def _connect_websocket(self):
        """Connect to the WebSocket server."""
        url = WEBSOCKET_URL.format(host=self._host)
        _LOGGER.debug("Attempting to connect to WebSocket: %s", url)
        
        try:
            # Используем asyncio.wait_for вместо async_timeout
            self._websocket = await asyncio.wait_for(
                websockets.connect(url), timeout=10
            )
            
            self._is_connected = True
            self._reconnect_attempts = 0
            _LOGGER.info("Successfully connected to Webasto heater at %s", url)
            
            # Отправляем GET_SETTINGS сразу после подключения
            await self.send_command("GET_SETTINGS")
            
            # Запускаем прослушивание сообщений
            self.hass.async_create_task(self._listen_for_messages())
            
        except (WebSocketException, asyncio.TimeoutError, OSError) as err:
            _LOGGER.error("Failed to connect to Webasto heater at %s: %s", url, err)
            self._is_connected = False
            self._schedule_reconnect()
        except Exception as err:
            _LOGGER.error("Unexpected error during WebSocket connection: %s", err)
            self._is_connected = False
            self._schedule_reconnect()

    async def _listen_for_messages(self):
        """Listen for messages from the WebSocket server."""
        try:
            while not self._stop_event.is_set() and self._is_connected:
                try:
                    message = await self._websocket.recv()
                    _LOGGER.debug("Received message: %s", message)
                    await self._process_message(message)
                    
                except ConnectionClosedOK:
                    _LOGGER.info("WebSocket connection closed gracefully.")
                    break
                except ConnectionClosed as err:
                    _LOGGER.warning("WebSocket connection closed unexpectedly: %s", err)
                    break
                except asyncio.CancelledError:
                    _LOGGER.debug("WebSocket listener task cancelled.")
                    break
                except Exception as err:
                    _LOGGER.error("WebSocket listening error: %s", err)
                    break
                    
        finally:
            self._is_connected = False
            if not self._stop_event.is_set():
                self._schedule_reconnect()
            await self._close_websocket()

    async def _process_message(self, message: str):
        """Process received message."""
        try:
            data = json.loads(message)
            if "settings" in data:
                # Настройки приходят вложенными в объект "settings"
                self._data.update(data["settings"])
            else:
                # Данные статуса приходят на корневом уровне
                self._data.update(data)
            self._notify_listeners()
            
        except json.JSONDecodeError:
            _LOGGER.warning("Received non-JSON message: %s", message)
            # Обработка старого формата CURRENT_SETTINGS
            if message.startswith("CURRENT_SETTINGS:"):
                self._parse_old_format_settings(message)
                self._notify_listeners()
        except Exception as err:
            _LOGGER.error("Error processing WebSocket message: %s - %s", err, message)

    def _parse_old_format_settings(self, message: str):
        """Parse old-style CURRENT_SETTINGS string and update data."""
        try:
            parts = message.split(':', 1)
            if len(parts) < 2:
                _LOGGER.warning("Invalid old settings format: %s", message)
                return
                
            params_str = parts[1]
            params = params_str.split(',')
            
            for param in params:
                if '=' in param:
                    key, value = param.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Попытка преобразовать в число
                    try:
                        if '.' in value:
                            self._data[key] = float(value)
                        else:
                            self._data[key] = int(value)
                    except ValueError:
                        self._data[key] = value
                        
        except Exception as err:
            _LOGGER.error("Error parsing old settings format: %s - %s", err, message)

    @callback
    def _notify_listeners(self):
        """Notify all registered listeners about data changes."""
        for callback_func in list(self._listeners):
            try:
                self.hass.async_create_task(callback_func())
            except Exception as err:
                _LOGGER.error("Error calling listener callback: %s", err)

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt."""
        if self._stop_event.is_set():
            return

        if self._reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            _LOGGER.error(
                "Maximum reconnection attempts (%d) reached. Stopping reconnection.",
                MAX_RECONNECT_ATTEMPTS
            )
            return

        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            
        self._reconnect_task = self.hass.async_create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        """Loop to attempt reconnection."""
        while (not self._stop_event.is_set() and 
               not self._is_connected and 
               self._reconnect_attempts < MAX_RECONNECT_ATTEMPTS):
            
            self._reconnect_attempts += 1
            _LOGGER.info(
                "Attempting to reconnect (%d/%d) in %d seconds...",
                self._reconnect_attempts,
                MAX_RECONNECT_ATTEMPTS,
                RECONNECT_INTERVAL
            )
            
            await asyncio.sleep(RECONNECT_INTERVAL)
            
            if not self._stop_event.is_set():
                await self._connect_websocket()

    async def send_command(self, command: str) -> bool:
        """Send a command to the Webasto heater via WebSocket."""
        if not self._websocket or not self._is_connected:
            _LOGGER.warning("WebSocket not connected, cannot send command: %s", command)
            return False

        try:
            _LOGGER.debug("Sending command: %s", command)
            await self._websocket.send(command)
            return True
        except WebSocketException as err:
            _LOGGER.error("Failed to send command '%s': %s", command, err)
            self._is_connected = False
            self._schedule_reconnect()
            return False
        except Exception as err:
            _LOGGER.error("Unexpected error sending command '%s': %s", command, err)
            self._is_connected = False
            self._schedule_reconnect()
            return False

    async def _close_websocket(self):
        """Close the WebSocket connection."""
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as err:
                _LOGGER.debug("Error closing WebSocket: %s", err)
            finally:
                self._websocket = None

    async def stop(self):
        """Stop the WebSocket connection."""
        _LOGGER.info("Stopping Webasto WebSocket connection...")
        self._stop_event.set()
        
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
                
        await self._close_websocket()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Webasto Heater component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Webasto Heater from a config entry."""
    host = entry.data.get("host")
    if not host:
        _LOGGER.error("No host configured for Webasto Heater in config entry.")
        return False

    webasto_data = WebastoHeaterData(hass, host)
    
    # Пытаемся установить соединение
    if not await webasto_data.connect():
        raise ConfigEntryNotReady(f"Could not connect to Webasto heater at {host}")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = webasto_data

    # Загружаем платформы
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Регистрируем обработчик остановки
    @callback
    def _handle_stop(event):
        hass.async_create_task(webasto_data.stop())

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _handle_stop)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        webasto_data = hass.data[DOMAIN].pop(entry.entry_id)
        await webasto_data.stop()
    
    return unload_ok