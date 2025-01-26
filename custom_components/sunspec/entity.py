"""SunSpecEntity class"""
from __future__ import annotations

import logging
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_sunspec_unique_id
from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__package__)


class SunSpecEntity(CoordinatorEntity):

    #@staticmethod
    #def 
    def __init__(self, coordinator, config_entry, data):
        super().__init__(coordinator)
        self._device_data = data["device_info"]
        self.config_entry = config_entry
        self.model_info = data["model"].getGroupMeta()
        self.model_id = data["model_id"]
        self.model_index = data["model_index"]
        self.model_wrapper = data["model"]
        self.key = data["key"]
        self._meta = self.model_wrapper.getMeta(self.key)
        self._group_meta = self.model_wrapper.getGroupMeta()
        self._point_meta = self.model_wrapper.getPoint(self.key).pdef
        self.use_icon = "mdi:information-outline"

        self._uniqe_id = get_sunspec_unique_id(
            config_entry.entry_id, self.key, self.model_id, self.model_index
        )
        self._device_id = config_entry.entry_id
        name = self._group_meta.get("name", str(self.model_id))
        if self.model_index > 0:
            name = f"{name} {self.model_index}"
        key_parts = self.key.split(":")
        if len(key_parts) > 1:
            name = f"{name} {key_parts[0]} {key_parts[1]}"

        desc = self._meta.get("label", self.key)

        if data["prefix"] != "":
            name = f"{data['prefix']} {name}"

        self._name = f"{name.capitalize()} {desc}"
        _LOGGER.debug(
            "Created entity for %s in model %s using prefix %s: %s uid %s",
            self.key,
            self.model_id,
            data["prefix"],
            self._name,
            self._uniqe_id,
        )

    async def write(self, new_value):
        self.model_wrapper.setValue(self.key, new_value, self.model_index)
        _LOGGER.debug(f"Writing: {new_value}")
        await self.coordinator.api.write(self.model_id, self.model_index)
        await self.coordinator.async_refresh()
        _LOGGER.debug(f"found value: {self.model_wrapper.getValue(self.key, self.model_index)}")
        self.async_write_ha_state()


    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self.config_entry.entry_id

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self.config_entry.entry_id, self.model_info["name"])
            },
            "name": self.model_info["label"],
            "model": self._device_data.getValue("Md"),
            "sw_version": self._device_data.getValue("Vr"),
            "manufacturer": self._device_data.getValue("Mn"),
        }

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self.use_icon

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name


