import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.components.number import (
    NumberEntity
)

from .entity import SunSpecEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback):
    await SunSpecEntity.async_setup_entry(hass, entry, async_add_devices, create_device_callback)

def create_device_callback(coordinator, entry, data, meta):
    if (meta.get("access","") == "RW") & (meta.get("type","") not in ("enum16","bitfield32")):
        return SunSpecNumberEntity(coordinator, entry, data)
    return None

class SunSpecNumberEntity(NumberEntity, SunSpecEntity):
    """ Implementation of writable number for SunSpec """

    def __init__(self, coordinator, config_entry, data):
        super().__init__(coordinator, config_entry, data)

    @property
    def native_step(self) -> float:
        return 1
    
    @property
    def native_value(self) -> str | float:
        try:
            return self.coordinator.data[self.model_id].getValue(
                self.key, self.model_index
            )
        except KeyError:
            _LOGGER.warning("Model %s not found", self.model_id)
            return None
        except OverflowError:
            _LOGGER.warning(
                "Math overflow error when retreiving calculated value for %s", self.key
            )
            return None
        
    @property
    def mode(self) -> str:
        return "box"

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return True
        
    async def async_set_native_value(self, value: float) -> None:
        await self.write(value)

        await self.coordinator.async_refresh()

