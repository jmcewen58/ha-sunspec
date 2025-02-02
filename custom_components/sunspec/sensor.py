"""Sensor platform for SunSpec."""
import logging
from typing import override

from homeassistant.components.sensor import (
    RestoreSensor, SensorDeviceClass, SensorEntity, SensorStateClass
)

from .entity import SunSpecEntity, HA_META

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    await SunSpecEntity.async_setup_entry(hass, entry, async_add_devices, create_device_callback)


def create_device_callback(coordinator, entry, data, meta):
    sunspec_unit = meta.get("units", "")
    ha_meta = HA_META.get(sunspec_unit, [sunspec_unit, None, None])
    device_class = ha_meta[2]
    if (meta.get("type","")=="bitfield32enum16"):
        return SunSpecSensor(coordinator, entry, data)
    elif (meta.get("access","") == "RW"):
        return None
    elif device_class == SensorDeviceClass.ENERGY:
        return SunSpecEnergySensor(coordinator, entry, data)
    else:
        return SunSpecSensor(coordinator, entry, data)


class SunSpecSensor(SunSpecEntity, SensorEntity):
    """sunspec Sensor class."""

    def __init__(self, coordinator, config_entry, data):
        super().__init__(coordinator, config_entry, data)
        self._options = []
        # Used if this is an energy sensor and the read value is 0
        # Updated wheneve the value read is not 0
        self.lastKnown = None
        self._assumed_state = False

        vtype = self._meta["type"]
        if vtype=="string":
            self.use_device_class = None
            self.unit = None
        if vtype in ("enum16", "bitfield32"):
            self._options = self._point_meta.get("symbols", None)
            if self._options is None:
                self.use_device_class = None
            else:
                self._options = [item["name"] for item in self._options]
                self._options.append("")

        _LOGGER.debug(
            "Created sensor entity for %s device class %s unit %s",
            self.key,
            self.use_device_class,
            self.unit,
        )
        if (self._options):
            _LOGGER.debug("Valid options for ENUM: %s", self._options)

    # def async_will_remove_from_hass(self):
    #    _LOGGER.debug(f"Will remove sensor {self._uniqe_id}")

    @property
    def options(self):
        if self.device_class != SensorDeviceClass.ENUM:
            return None
        return self._options

    @property
    def assumed_state(self):
        return self._assumed_state

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            val = self.coordinator.data[self.model_id].getValue(
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
        vtype = self._meta["type"]
        if vtype in ("enum16", "bitfield32"):
            symbols = self._point_meta.get("symbols", None)
            if symbols is None:
                return val
            if vtype == "enum16":
                symbol = list(filter(lambda s: s["value"] == val, symbols))
                if len(symbol) == 1:
                    return symbol[0]["name"][:255]
                else:
                    return None
            else:
                symbols = list(
                    filter(lambda s: (val >> int(s["value"])) & 1 == 1, symbols)
                )
                if len(symbols) > 0:
                    return ",".join(map(lambda s: s["name"], symbols))[:255]
                return ""
        return val

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        # if self.unit == "":
        #     _LOGGER.debug(f"UNIT IS NONT FOR {self.name}")
        #    return None
        return self.unit

    @property
    def device_class(self):
        """Return de device class of the sensor."""
        return self.use_device_class

    @property
    def state_class(self):
        """Return de device class of the sensor."""
        if self.unit == "" or self.unit is None:
            return None
        if self.device_class == SensorDeviceClass.ENERGY:
            return SensorStateClass.TOTAL_INCREASING
        return SensorStateClass.MEASUREMENT

    @override
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = self._base_extra_state_attrs
        if (attrs is not None):
            if (self._options):
                attrs["options"] = self._options
            attrs["raw"] = self.coordinator.data[self.model_id].getValueRaw(
                self.key, self.model_index
            )
        return attrs

class SunSpecEnergySensor(SunSpecSensor, RestoreSensor):
    def __init__(self, coordinator, config_entry, data):
        super().__init__(coordinator, config_entry, data)
        self.last_known_value = None

    @property
    def native_value(self):
        val = super().native_value
        # For an energy sensor a value of 0 woulld mess up long term stats because of how total_increasing works
        if val == 0:
            _LOGGER.debug(
                "Returning last known value instead of 0 for {self.name) to avoid resetting total_increasing counter"
            )
            self._assumed_state = True
            return self.lastKnown
        self.lastKnown = val
        self._assumed_state = False
        return val

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"{self.name} Fetch last known state")
        state = await self.async_get_last_sensor_data()
        if state:
            _LOGGER.debug(
                f"{self.name} Got last known value from state: {state.native_value}"
            )
            self.last_known_value = state.native_value
        else:
            _LOGGER.debug(f"{self.name} No previous state was found")
