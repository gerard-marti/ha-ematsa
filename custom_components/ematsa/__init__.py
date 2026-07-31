"""Inicialización de la integración de Ematsa."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CONTRACT
from .api import EmatsaApiClient

PLATFORMS = ["sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura la integración desde la entrada de interfaz gráfica."""
    hass.data.setdefault(DOMAIN, {})

    # 1. Inicializamos el cliente API con los datos guardados en el config_flow
    session = async_get_clientsession(hass)
    api = EmatsaApiClient(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=session,
        contract=entry.data.get(CONF_CONTRACT)
    )

    # 2. Autenticamos y hacemos la primera lectura de datos antes de crear los sensores
    await api.authenticate()
    await api.get_consumos()

    # 3. Guardamos la instancia de la API en memoria para que sensor.py la encuentre
    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarga la integración y limpia la memoria."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok