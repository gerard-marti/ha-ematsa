"""Sensor platform for Ematsa integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "lectura_total": {
        "name": "Lectura Contador",
        "device_class": SensorDeviceClass.WATER,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit_of_measurement": UnitOfVolume.CUBIC_METERS,
        "icon": "mdi:water",
    },
    "consumo_ayer": {
        "name": "Consumo Ayer",
        "device_class": SensorDeviceClass.WATER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit_of_measurement": UnitOfVolume.CUBIC_METERS,
        "icon": "mdi:water-minus",
    },
    "consumo_mes_actual": {
        "name": "Consumo Mes Actual",
        "device_class": SensorDeviceClass.WATER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit_of_measurement": UnitOfVolume.CUBIC_METERS,
        "icon": "mdi:water-percent",
    },
    "consumo_ultimo_mes": {
        "name": "Consumo Último Mes",
        "device_class": SensorDeviceClass.WATER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit_of_measurement": UnitOfVolume.CUBIC_METERS,
        "icon": "mdi:water-check",
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Configura las entidades de sensor desde una entrada de configuración."""
    domain_data = hass.data.get("ematsa", {})
    api = domain_data.get(entry.entry_id) or domain_data.get("api")

    if not api and hasattr(entry, "runtime_data"):
        api = entry.runtime_data

    entities = [
        EmatsaSensor(api, entry, key, config)
        for key, config in SENSOR_TYPES.items()
    ]
    async_add_entities(entities, update_before_add=True)


class EmatsaSensor(SensorEntity):
    """Representación de un sensor de Ematsa."""

    _attr_has_entity_name = True

    def __init__(self, api, entry: ConfigEntry, key: str, config: Dict[str, Any]) -> None:
        """Inicializa el sensor."""
        self.api = api
        self.entry = entry
        self.key = key

        contract = entry.data.get("contract") or entry.data.get("username") or entry.entry_id

        self._attr_name = config["name"]
        self._attr_unique_id = f"{contract}_{key}"
        self._attr_device_class = config.get("device_class")
        self._attr_state_class = config.get("state_class")
        self._attr_native_unit_of_measurement = config.get("unit_of_measurement")
        self._attr_icon = config.get("icon")

        self._attr_device_info = DeviceInfo(
            identifiers={("ematsa", str(contract))},
            name=f"Contrato {contract}",
            manufacturer="Ematsa",
            model="Contador de Agua",
        )

    @property
    def native_value(self) -> Optional[float]:
        """Devuelve el valor actual del sensor."""
        if not self.api or not getattr(self.api, "_cache", None):
            return None
        return self.api._cache.get(self.key)

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Devuelve los históricos mensual y diario en los atributos del sensor."""
        if self.key == "lectura_total" and self.api and getattr(self.api, "_cache", None):
            return {
                "historico_mensual": self.api._cache.get("historico", []),
                "historico_diario": self.api._cache.get("historico_diario", []),
            }
        return None

    async def async_update(self) -> None:
            """Actualiza los datos desde la API."""
            if self.api:
                await self.api.authenticate() # Forzamos refrescar la cookie de sesión
                await self.api.get_consumos()