"""Config flow for Webasto Heater integration."""
import logging
import asyncio
from typing import Any, Dict, Optional

import voluptuous as vol
import websockets
from websockets.exceptions import WebSocketException

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from . import DOMAIN, WEBSOCKET_URL

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required("host"): cv.string,
})

class WebastoHeaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Webasto Heater."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            host = user_input["host"].strip()
            
            # Валидация хоста
            if not host:
                errors["host"] = "empty_host"
            else:
                # Проверяем, не настроена ли уже интеграция с этим хостом
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

                # Тестируем подключение
                if await self._async_test_connection(host):
                    return self.async_create_entry(
                        title=f"Webasto Heater ({host})", 
                        data={"host": host}
                    )
                else:
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", 
            data_schema=DATA_SCHEMA, 
            errors=errors,
            description_placeholders={
                "example_host": "192.168.1.100"
            }
        )

    async def _async_test_connection(self, host: str) -> bool:
        """Test if we can connect to the Webasto heater via WebSocket."""
        url = WEBSOCKET_URL.format(host=host)
        _LOGGER.debug("Testing WebSocket connection to: %s", url)
        
        try:
            # Используем asyncio.wait_for вместо async_timeout
            async with asyncio.timeout(10):
                async with websockets.connect(url) as websocket:
                    # Отправляем тестовую команду для проверки работоспособности
                    await websocket.send("GET_SETTINGS")
                    
                    # Ждем ответа в течение 5 секунд
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        _LOGGER.debug("Received test response: %s", response)
                    except asyncio.TimeoutError:
                        _LOGGER.debug("No response received, but connection established")
                    
                    _LOGGER.info("Successfully tested connection to %s", url)
                    return True
                    
        except (WebSocketException, OSError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Failed to test connection to %s: %s", url, err)
            return False
        except Exception as err:
            _LOGGER.error("Unexpected error during connection test to %s: %s", url, err)
            return False

    async def async_step_import(self, import_config: Dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_config)