"""Sensor-Entitäten – PM2.5, Temperatur, Luftqualität, Filter, EF04/EF02-Diagnose."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SoehnleAc500ConfigEntry
from .entity import SoehnleAc500Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoehnleAc500ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities([
        AC500PM25Sensor(entry),
        AC500TempSensor(entry),
        AC500AirQualitySensor(entry),
        AC500FilterUsedSensor(entry),
        AC500FilterRemainingSensor(entry),
        AC500FilterPctSensor(entry),
        AC500EF04DiagSensor(entry, 0, "ef04_pair0"),
        AC500EF04DiagSensor(entry, 2, "ef04_pair2"),
        AC500EF04DiagSensor(entry, 3, "ef04_pair3"),
        AC500EF04DiagSensor(entry, 5, "ef04_pair5"),
        AC500EF04DiagSensor(entry, 6, "ef04_pair6"),
        AC500EF04DiagSensor(entry, 7, "ef04_pair7"),
        AC500EF04RawSensor(entry),
        AC500EF03RawSensor(entry),
        AC500D0FFRawSensor(entry, "ffd2"),
        AC500D0FFRawSensor(entry, "ffd3"),
        AC500D0FFRawSensor(entry, "ffd4"),
        AC500D0FFRawSensor(entry, "ffd5"),
        AC500D0FFRawSensor(entry, "fff1"),
    ])


class _SensorBase(SoehnleAc500Entity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: SoehnleAc500ConfigEntry, suffix: str) -> None:
        super().__init__(entry, suffix)


class AC500PM25Sensor(_SensorBase):
    _attr_device_class               = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = "µg/m³"
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 1

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "pm25")
        self._attr_name = "PM2.5"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.state.pm25 if self.coordinator.state.ever_seen else None


class AC500TempSensor(_SensorBase):
    _attr_device_class               = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "temperature")
        self._attr_name = "Temperature"

    @property
    def available(self) -> bool:
        return (
            self.coordinator.state.ever_seen
            and self.coordinator.state.temperature is not None
        )

    @property
    def native_value(self) -> float | None:
        return self.coordinator.state.temperature


# PM2.5-Grenzwerte gemäß WHO 2021 / EPA AQI
def _pm25_to_quality(pm25: float) -> str:
    if pm25 <= 12.0:
        return "good"
    if pm25 <= 35.4:
        return "moderate"
    if pm25 <= 55.4:
        return "unhealthy_sensitive"
    if pm25 <= 150.4:
        return "unhealthy"
    if pm25 <= 250.4:
        return "very_unhealthy"
    return "hazardous"


class AC500AirQualitySensor(SoehnleAc500Entity, SensorEntity):
    """Kategorische Luftqualität abgeleitet aus dem PM2.5-Messwert."""

    _attr_device_class    = SensorDeviceClass.ENUM
    _attr_options         = ["good", "moderate", "unhealthy_sensitive",
                             "unhealthy", "very_unhealthy", "hazardous"]
    _attr_icon            = "mdi:leaf"
    _attr_translation_key = "air_quality"

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "air_quality")

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.state.ever_seen:
            return None
        return _pm25_to_quality(self.coordinator.state.pm25)


class AC500FilterUsedSensor(_SensorBase):
    """Genutzte Filterstunden – aus EF02 p[9:11]."""

    _attr_native_unit_of_measurement = "h"
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 0

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "filter_used_hours")
        self._attr_name = "Filter Used Hours"

    @property
    def available(self) -> bool:
        return (
            self.coordinator.state.ever_seen
            and self.coordinator.state.filter_total_hours > 0
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.state.filter_used_hours


class AC500FilterRemainingSensor(_SensorBase):
    """Verbleibende Filterstunden – berechnet aus EF02-Filterdaten."""

    _attr_native_unit_of_measurement = "h"
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 0

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "filter_remaining_hours")
        self._attr_name = "Filter Remaining Hours"

    @property
    def available(self) -> bool:
        return (
            self.coordinator.state.ever_seen
            and self.coordinator.state.filter_total_hours > 0
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.state.filter_remaining_hours


class AC500FilterPctSensor(_SensorBase):
    """Filternutzung in Prozent – entspricht der App-Anzeige."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon                       = "mdi:air-filter"
    _attr_suggested_display_precision = 1

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "filter_pct_used")
        self._attr_name = "Filter Usage"

    @property
    def available(self) -> bool:
        return (
            self.coordinator.state.ever_seen
            and self.coordinator.state.filter_total_hours > 0
        )

    @property
    def native_value(self) -> float | None:
        return self.coordinator.state.filter_pct_used


class AC500EF04DiagSensor(SoehnleAc500Entity, SensorEntity):
    """Rohwert eines EF04-Paares – Diagnosehilfe für Reverse-Engineering."""

    _attr_state_class    = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon           = "mdi:help-rhombus-outline"

    def __init__(
        self,
        entry: SoehnleAc500ConfigEntry,
        pair_idx: int,
        state_attr: str,
    ) -> None:
        super().__init__(entry, f"ef04_pair{pair_idx}")
        self._state_attr = state_attr
        self._attr_name  = f"EF04 Pair{pair_idx} (raw)"

    @property
    def available(self) -> bool:
        return (
            self.coordinator.state.ever_seen
            and getattr(self.coordinator.state, self._state_attr) is not None
        )

    @property
    def native_value(self) -> int | None:
        return getattr(self.coordinator.state, self._state_attr)


class AC500EF04RawSensor(SoehnleAc500Entity, SensorEntity):
    """Vollständiger EF04-Rohpayload als Hex – zur Analyse von Länge und unbekannten Bytes."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon            = "mdi:format-list-numbered"

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "ef04_raw_hex")
        self._attr_name = "EF04 Raw Payload"

    @property
    def available(self) -> bool:
        return (
            self.coordinator.state.ever_seen
            and self.coordinator.state.ef04_raw_hex is not None
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.state.ef04_raw_hex


class AC500EF03RawSensor(SoehnleAc500Entity, SensorEntity):
    """Vollständiger EF03-Rohpayload als Hex – Zweck der Charakteristik noch unbekannt."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon            = "mdi:help-rhombus-outline"

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "ef03_raw_hex")
        self._attr_name = "EF03 Raw Payload"

    @property
    def available(self) -> bool:
        return self.coordinator.state.ef03_raw_hex is not None

    @property
    def native_value(self) -> str | None:
        return self.coordinator.state.ef03_raw_hex


class AC500D0FFRawSensor(SoehnleAc500Entity, SensorEntity):
    """Rohwert einer d0ff-Charakteristik als Hex – statische Gerätekennung."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon            = "mdi:filter-cog-outline"

    def __init__(self, entry: SoehnleAc500ConfigEntry, char_name: str) -> None:
        super().__init__(entry, f"{char_name}_raw_hex")
        self._char_attr   = f"{char_name}_raw_hex"
        self._attr_name   = f"{char_name.upper()} Raw"

    @property
    def available(self) -> bool:
        return getattr(self.coordinator.state, self._char_attr) is not None

    @property
    def native_value(self) -> str | None:
        return getattr(self.coordinator.state, self._char_attr)
