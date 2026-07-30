from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from .const import DOMAIN, CONF_CONTRACT
from .api import EmatsaApiClient

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Configura los sensores de Ematsa basados en el config flow."""
    config = hass.data[DOMAIN][entry.entry_id]

    # Obtenemos los datos que el usuario metió en la UI
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    contract = config[CONF_CONTRACT]

    session = async_get_clientsession(hass)
    api = EmatsaApiClient(username, password, contract, session)

    # Añadimos la entidad
    async_add_entities([EmatsaConsumoSensor(api, contract)], update_before_add=True)


class EmatsaConsumoSensor(SensorEntity):
    def __init__(self, api, contract):
        self.api = api
        self._attr_name = f"Consumo Ematsa {contract}"
        self._attr_unique_id = f"ematsa_consumo_{contract}"
        self._attr_native_unit_of_measurement = "L" # o "m³" según lo que devuelva la web
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_update(self):
        """Llama a la API para actualizar los datos."""
        # Primero nos autenticamos si no lo estamos
        auth_ok = await self.api.authenticate()
        if auth_ok:
            # Aquí llamarías a la función de la API que raspa el HTML
            datos = await self.api.get_consumos()
            # self._state = extraer_valor(datos) (Lógica a implementar con BeautifulSoup)
            self._state = 150 # Valor de prueba