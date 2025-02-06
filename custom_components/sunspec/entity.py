"""SunSpecEntity class
This class has been significantly beefed up, moving much of the code from sensor to the this base class.
That allows us to leverage it for our new platforms that we've added.
"""
from __future__ import annotations

import logging
import inspect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorDeviceClass


from homeassistant.const import (DEGREE, PERCENTAGE, UnitOfReactivePower, UnitOfApparentPower,UnitOfDataRate,
UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfFrequency, UnitOfIrradiance, UnitOfLength,
UnitOfPower, UnitOfPressure, UnitOfSpeed, UnitOfTemperature, UnitOfTime)

from . import get_sunspec_unique_id
from .const import DOMAIN, CONF_PREFIX

_LOGGER: logging.Logger = logging.getLogger(__package__)

ICON_DEFAULT = "mdi:information-outline"
ICON_AC_AMPS = "mdi:current-ac"
ICON_DC_AMPS = "mdi:current-dc"
ICON_VOLT = "mdi:lightning-bolt"
ICON_POWER = "mdi:solar-power"
ICON_FREQ = "mdi:sine-wave"
ICON_ENERGY = "mdi:solar-panel"
ICON_TEMP = "mdi:thermometer"

HA_META = {
    "A": [UnitOfElectricCurrent.AMPERE, ICON_AC_AMPS, SensorDeviceClass.CURRENT],
    "HPa": [UnitOfPressure.HPA, ICON_DEFAULT, None],
    "Hz": [UnitOfFrequency.HERTZ, ICON_FREQ, None],
    "Mbps": [UnitOfDataRate.MEGABITS_PER_SECOND, ICON_DEFAULT, None],
    "V": [UnitOfElectricPotential.VOLT, ICON_VOLT, SensorDeviceClass.VOLTAGE],
    "VA": [UnitOfApparentPower.VOLT_AMPERE, ICON_POWER, None],
    "VAr": [UnitOfReactivePower.VOLT_AMPERE_REACTIVE, ICON_POWER, None],
    "W": [UnitOfPower.WATT, ICON_POWER, SensorDeviceClass.POWER],
    "kW": [UnitOfPower.KILO_WATT, ICON_POWER, SensorDeviceClass.POWER],
    "W/m2": [UnitOfIrradiance.WATTS_PER_SQUARE_METER, ICON_DEFAULT, None],
    "Wh": [UnitOfEnergy.WATT_HOUR, ICON_ENERGY, SensorDeviceClass.ENERGY],
    "WH": [UnitOfEnergy.WATT_HOUR, ICON_ENERGY, SensorDeviceClass.ENERGY],
    "bps": [UnitOfDataRate.BITS_PER_SECOND, ICON_DEFAULT, None],
    "deg": [DEGREE, ICON_TEMP, SensorDeviceClass.TEMPERATURE],
    "Degrees": [DEGREE, ICON_TEMP, SensorDeviceClass.TEMPERATURE],
    "C": [UnitOfTemperature.CELSIUS, ICON_TEMP, SensorDeviceClass.TEMPERATURE],
    "kWh": [UnitOfEnergy.KILO_WATT_HOUR, ICON_ENERGY, SensorDeviceClass.ENERGY],
    "m/s": [UnitOfSpeed.METERS_PER_SECOND, ICON_DEFAULT, None],
    "mSecs": [UnitOfTime.MILLISECONDS, ICON_DEFAULT, None],
    "meters": [UnitOfLength.METERS, ICON_DEFAULT, None],
    "mm": [UnitOfLength.MILLIMETERS, ICON_DEFAULT, None],
    "%": [PERCENTAGE, ICON_DEFAULT, None],
    "Secs": [UnitOfTime.SECONDS, ICON_DEFAULT, None],
    "enum16": [None, ICON_DEFAULT, SensorDeviceClass.ENUM],
    "bitfield32": [None, ICON_DEFAULT, None],
}


class SunSpecEntity(CoordinatorEntity):

    @staticmethod
    async def async_setup_entry(hass, entry, async_add_devices, create_device):
        """Setup sensor platform."""
        coordinator = hass.data[DOMAIN][entry.entry_id]
        sensors = []
        platform = inspect.getmodule(create_device).__name__
        platform = platform.replace("custom_components.","")
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
                    device = create_device(coordinator, entry, data, meta)
                    if (device is not None):
                        sensors.append(device)
                        _LOGGER.debug(f"{platform} adding {type(device).__name__}: {model_id}-{key}")
                    else:
                        _LOGGER.debug(f"{platform} skipping entity: {model_id}-{key}")

        async_add_devices(sensors)


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
        sunspec_unit = self._meta.get("units", self._meta.get("type", ""))
        ha_meta = HA_META.get(sunspec_unit, [sunspec_unit, ICON_DEFAULT, None])
        self._attr_native_unit_of_measurement = ha_meta[0]
        self.use_icon = ha_meta[1]
        self.use_device_class = ha_meta[2]

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

        if self._attr_native_unit_of_measurement == UnitOfElectricCurrent.AMPERE and "DC" in self.name:
            self.use_icon = ICON_DC_AMPS

        _LOGGER.debug(
            "Created entity for %s in model %s using prefix %s: %s uid %s",
            self.key,
            self.model_id,
            data["prefix"],
            self._name,
            self._uniqe_id,
        )
        _LOGGER.debug(self._meta)
        self._base_extra_state_attrs = self.create_extra_state_attributes()

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
        return self._uniqe_id
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

    def create_extra_state_attributes(self):
        """Create the state attributes."""
        attrs = {
            "integration": DOMAIN,
            "sunspec_key": self.key,
        }
        label = self._meta.get("label", None)
        if label is not None:
            attrs["label"] = label

        attrs["raw"] = self.coordinator.data[self.model_id].getValueRaw(
            self.key, self.model_index
        )

        desc = self._meta.get("desc", None)
        if desc is not None:
            attrs["description"] = desc
        
        return attrs




