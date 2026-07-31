import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CONTRACT
from .api import EmatsaApiClient

class EmatsaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Maneja el flujo de configuración en 2 pasos."""
    VERSION = 1

    def __init__(self):
        self._username = None
        self._password = None
        self._contracts = []

    async def async_step_user(self, user_input=None):
        """Paso 1: Credenciales de usuario y contraseña."""
        errors = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            session = async_get_clientsession(self.hass)
            api = EmatsaApiClient(self._username, self._password, session)

            # Intentamos autenticar y obtener la lista de contratos
            if await api.authenticate():
                self._contracts = await api.get_contracts()
                if self._contracts:
                    return await self.async_step_contract()
                else:
                    errors["base"] = "no_contracts_found"
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_contract(self, user_input=None):
        """Paso 2: Selección del contrato en un desplegable."""
        if user_input is not None:
            contract_selected = user_input[CONF_CONTRACT]

            # Evitar añadir el mismo contrato dos veces
            await self.async_set_unique_id(f"ematsa_{contract_selected}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Ematsa ({contract_selected})",
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_CONTRACT: contract_selected,
                },
            )

        # Crear el diccionario para el select desplegable (marcando el primero por defecto)
        contracts_schema = vol.Schema({
            vol.Required(CONF_CONTRACT, default=self._contracts[0]): vol.In(self._contracts),
        })

        return self.async_show_form(
            step_id="contract",
            data_schema=contracts_schema,
        )