"""Cliente API para Ematsa."""
import logging
import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


class EmatsaApiClient:
    """Clase para gestionar las peticiones HTTP a la Oficina Virtual de Ematsa."""

    def __init__(
        self,
        username: str,
        password: str,
        contract: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Inicializa el cliente de la API."""
        self.username = username
        self.password = password
        self.contract = contract
        self.session = session
        self.base_url = "https://ov.ematsa.cat"

    async def authenticate(self) -> bool:
        """Autentica al usuario en el portal de Ematsa."""
        login_page_url = f"{self.base_url}/ca/login"

        try:
            # 1. Obtener la página para extraer token o cookies de sesión preliminares
            async with self.session.get(login_page_url) as response:
                if response.status != 200:
                    _LOGGER.error("No se pudo cargar la página de login de Ematsa")
                    return False
                html = await response.text()
                p_auth = self._extract_p_auth(html)

            # 2. Enviar petición POST de login
            post_url = (
                f"{login_page_url}?p_p_id=CustomLoginPortlet"
                "&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view"
                "&_CustomLoginPortlet_javax.portlet.action=%2Flogin%2Flogin"
                f"&p_auth={p_auth}"
            )

            payload = {
                "saveLastPath": "false",
                "redirect": "",
                "doActionAfterLogin": "false",
                "_CustomLoginPortlet_lastContract": self.contract,
                "_CustomLoginPortlet_login": self.username,
                "_CustomLoginPortlet_password": self.password,
            }

            async with self.session.post(post_url, data=payload) as auth_response:
                if auth_response.status in [200, 302]:
                    _LOGGER.info("Autenticación en Ematsa exitosa")
                    return True

                _LOGGER.error(
                    "Error de autenticación en Ematsa: estado %s",
                    auth_response.status,
                )
                return False

        except Exception as err:
            _LOGGER.error("Error conectando a Ematsa: %s", err)
            return False

    def _extract_p_auth(self, html: str) -> str:
        """Extrae el token p_auth del HTML (Liferay)."""
        soup = BeautifulSoup(html, "html.parser")

        # Intentar extraer el token del formulario o variables Liferay
        # Por defecto retornamos cadena vacía si no lo encuentra para evitar crash
        token_input = soup.find("input", {"name": "p_auth"})
        if token_input and "value" in token_input.attrs:
            return token_input["value"]

        return ""

    async def get_consumos(self) -> float:
        """Obtiene los datos de consumo de agua."""
        url_consumos = f"{self.base_url}/ca/group/ematsa/mis-consumos"
        try:
            async with self.session.get(url_consumos) as response:
                if response.status == 200:
                    html = await response.text()
                    # Aquí irá el rascado de datos con BeautifulSoup
                    return 0.0
        except Exception as err:
            _LOGGER.error("Error al obtener datos de consumo: %s", err)

        return 0.0