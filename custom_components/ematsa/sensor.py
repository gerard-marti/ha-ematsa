from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CONTRACT
from .api import EmatsaApiClient

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    config = hass.data[DOMAIN][entry.entry_id]

    session = async_get_clientsession(hass)
    api = EmatsaApiClient(
        username=config["username"],
        password=config["password"],
        contract=config[CONF_CONTRACT],
        session=session
    )

    async_add_entities([EmatsaConsumoSensor(api, config[CONF_CONTRACT])], update_before_add=True)


class EmatsaConsumoSensor(SensorEntity):
    """Representación del sensor de agua de Ematsa."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS  # m³

    def __init__(self, api: EmatsaApiClient, contract: str):
        self.api = api
        self.contract = contract
        self._attr_name = f"Consumo Agua Ematsa {contract}"
        self._attr_unique_id = f"ematsa_consumo_{contract}"
        self._state = None
        self._extra_attributes = {}

    @property
    def native_value(self):
        return self._state

    @property
    def extra_state_attributes(self):
        """Devuelve los datos de histórico como atributos adicionales."""
        return self._extra_attributes

    async def async_update(self):
        """Actualiza el estado del sensor raspando los datos."""
        auth_ok = await self.api.authenticate()
        if auth_ok:
            datos = await self.api.get_consumos()
            self._state = datos.get("lectura_total")
            self._extra_attributes = datos.get("historico", {})