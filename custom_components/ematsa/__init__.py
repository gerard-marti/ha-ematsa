from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura Ematsa a partir de una entrada de configuración (UI)."""
    hass.data.setdefault(DOMAIN, {})

    # Guardamos los datos de configuración (usuario, pass, contrato) en la memoria de HA
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Le decimos a HA que cargue la plataforma de sensores (sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarga la integración si el usuario la elimina."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok