from __future__ import annotations

import logging

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback

from .entity import SunSpecEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup select platform."""
    await SunSpecEntity.async_setup_entry(hass, entry, async_add_devices, create_device_callback)

def create_device_callback(coordinator, entry, data, meta):
    if (meta.get("type","")=="enum16") & (meta.get("access","") == "RW"):
        return SunSpecSelect(coordinator, entry, data)
    return None

class SunSpecSelect(SunSpecEntity, SelectEntity):

    def __init__(self, coordinator, config_entry, data):
        super().__init__(coordinator, config_entry, data)
        self._attr_icon = "mdi:dip-switch" 
        self.enum_value = None
        self._attr_options = []

        self._attr_options = self._point_meta.get("symbols", None)
        self._attr_options = [item["name"] for item in self._attr_options]

        _LOGGER.debug("Valid options for select: %s", self._attr_options)
        self._attr_extra_state_attributes["options"] = self._attr_options

    # def async_will_remove_from_hass(self):
    #    _LOGGER.debug(f"Will remove sensor {self._uniqe_id}")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        symbols = self._point_meta.get("symbols", None)
        if symbols is None:
            _LOGGER.error("No symbols to convert option")
            return
        symbol = list(filter(lambda s: s["name"] == option, symbols))
        if len(symbol) == 1:
            val = symbol[0]["value"]
            await self.write(val)
        else:
            _LOGGER.error("Invalid option selected.")
            return

    @callback
    def async_check_significant_change(
        hass: HomeAssistant,
        old_state: str,
        old_attrs: dict,
        new_state: str,
        new_attrs: dict,
        **kwargs: Any,
    ) -> bool | None:
        """Test if state significantly changed."""
        return old_state != new_state

    @property
    def current_option(self):
        """Return the state of the sensor."""
        try:
            val = self.coordinator.data[self.model_id].getValue(
                self.key, self.model_index
            )
        except KeyError:
            _LOGGER.error("Model %s not found", self.model_id)
            return None
        self.enum_value = val
        symbols = self._point_meta.get("symbols", None)
        if symbols is None:
            return None
        symbol = list(filter(lambda s: s["value"] == val, symbols))
        if len(symbol) == 1:
            self._attr_current_option = symbol[0]["name"][:255]
            return self._attr_current_option
        return None

