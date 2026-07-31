"""Botón para forzar la actualización de datos de Ematsa."""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_CONTRACT
from .api import EmatsaApiClient


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Configura el botón de refresco."""
    session = async_get_clientsession(hass)
    api = EmatsaApiClient(
        username=entry.data["username"],
        password=entry.data["password"],
        session=session,
        contract=entry.data[CONF_CONTRACT]
    )
    async_add_entities([EmatsaRefreshButton(api, entry.data[CONF_CONTRACT])])


class EmatsaRefreshButton(ButtonEntity):
    """Botón de actualización manual."""

    def __init__(self, api: EmatsaApiClient, contract: str):
        """Inicializa el botón."""
        self.api = api
        self.contract = contract
        self._attr_name = "Actualizar Datos"
        self._attr_unique_id = f"ematsa_{contract}_refresh_button"
        self._attr_icon = "mdi:refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, contract)},
            name=f"Contrato {contract}",
            manufacturer="Ematsa",
            model="Oficina Virtual Aigua"
        )

    async def async_press(self) -> None:
        """Fuerza la llamada borrando la caché de 15 min."""
        self.api._last_update = 0
        await self.api.authenticate()
        await self.api.get_consumos()
        self.async_write_ha_state()