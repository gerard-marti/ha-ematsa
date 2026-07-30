import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_CONTRACT
from .api import EmatsaApiClient # Importamos tu cliente API

# Definimos los campos del formulario
DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Required(CONF_CONTRACT): str,
})

class EmatsaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Maneja el flujo de configuración de la UI."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Aquí podríamos probar si las credenciales son correctas antes de guardar
            # usando aiohttp.ClientSession de Home Assistant

            # Si todo va bien, creamos la entrada en HA:
            return self.async_create_entry(
                title=f"Ematsa ({user_input[CONF_CONTRACT]})",
                data=user_input
            )

        # Si no hay input o hay errores, mostramos el formulario
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )