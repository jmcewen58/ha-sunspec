from __future__ import annotations

import logging

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback

from .const import CONF_PREFIX
from .const import DOMAIN
from .entity import SunSpecEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []
    device_info = await coordinator.api.async_get_device_info()
    prefix = entry.options.get(CONF_PREFIX, entry.data.get(CONF_PREFIX, ""))
    for model_id in coordinator.data.keys():
        model_wrapper = coordinator.data[model_id]
        for key in model_wrapper.getKeys():
            for model_index in range(model_wrapper.num_models):
                data = {
                    "device_info": device_info,
                    "key": key,
                    "model_id": model_id,
                    "model_index": model_index,
                    "model": model_wrapper,
                    "prefix": prefix,
                }

                meta = model_wrapper.getMeta(key)
                sunspec_type = meta.get("type","")
                sunspec_isRW = meta.get("access","") == "RW"
                if (sunspec_type=="enum16") & (sunspec_isRW):
                    _LOGGER.debug(f"Adding select entity: {model_id}-{key}")
                    sensors.append(SunSpecSelect(coordinator, entry, data))

    async_add_devices(sensors)

class SunSpecSelect(SunSpecEntity, SelectEntity):

 #meta:{'access': 'RW', 'desc': 'Commands to PCS. Enumerated value.', 
 # 'label': 'Set Operation', 'name': 'OpCtl', 'size': 1, 
 # 'symbols': [{'label': 'Stop the DER', 'name': 'STOP', 'value': 0}, {'label': 'Start the DER', 'name': 'START', 'value': 1}, {'label': 'Enter Standby Mode', 'name': 'ENTER_STANDBY', 'value': 2}, {'label': 'Exit Standby Mode', 'name': 'EXIT_STANDBY', 'value': 3}], 'type': 'enum16'}


    def __init__(self, coordinator, config_entry, data):
        super().__init__(coordinator, config_entry, data)
        self.use_icon = "mdi:dip-switch" 
        self.enum_value = None
        self._attr_options = []

        self._attr_options = self._point_meta.get("symbols", None)
        self._attr_options = [item["name"] for item in self._attr_options]

        _LOGGER.debug("Valid options for select: %s", self._attr_options)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self.async_write_ha_state()

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return True
        
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

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self.use_icon

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            "integration": DOMAIN,
            "sunspec_key": self.key,
            "raw": self.enum_value
        }
        label = self._meta.get("label", None)
        if label is not None:
            attrs["label"] = label

        return attrs