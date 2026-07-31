"""Cliente API para Ematsa."""
import logging
import re
import time
import aiohttp
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ca-ES,ca;q=0.9,es-ES;q=0.8,es;q=0.7",
    "Origin": "https://ov.ematsa.cat",
}

MESES_MAP = {
    "ene": 1, "gen": 1, "feb": 2, "febr": 2, "mar": 3, "març": 3,
    "abr": 4, "may": 5, "mai": 5, "jun": 6, "jul": 7, "ago": 8,
    "ag": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12, "des": 12
}


class EmatsaApiClient:
    """Clase para gestionar las peticiones HTTP a la Oficina Virtual de Ematsa."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        contract: str = None,
    ) -> None:
        self.username = username
        self.password = password
        self.contract = contract
        self.session = session
        self.base_url = "https://ov.ematsa.cat"
        self._cache = {}
        self._last_update = 0

    async def authenticate(self) -> bool:
        """Autentica al usuario en el portal de Ematsa."""
        login_page_url = f"{self.base_url}/ca/login"

        try:
            async with self.session.get(login_page_url, headers=HEADERS) as response:
                if response.status != 200:
                    return False

                html = await response.text()
                p_auth = self._extract_p_auth(html)

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
                "_CustomLoginPortlet_login": self.username,
                "_CustomLoginPortlet_password": self.password,
            }

            if self.contract:
                payload["_CustomLoginPortlet_lastContract"] = self.contract

            post_headers = HEADERS.copy()
            post_headers["Referer"] = login_page_url

            async with self.session.post(post_url, data=payload, headers=post_headers) as auth_response:
                return auth_response.status in [200, 302]

        except Exception as err:
            _LOGGER.error("Error conectando a Ematsa: %s", err)
            return False

    def _extract_p_auth(self, html: str) -> str:
        """Extrae el token p_auth del HTML."""
        js_match = re.search(r"Liferay\.authToken\s*=\s*['\"]([^'\"]+)['\"]", html)
        if js_match:
            return js_match.group(1)

        url_match = re.search(r"[?&]p_auth=([a-zA-Z0-9]+)", html)
        if url_match:
            return url_match.group(1)

        soup = BeautifulSoup(html, "html.parser")
        token_input = soup.find("input", {"name": "p_auth"})
        if token_input and "value" in token_input.attrs:
            return token_input["value"]

        return ""

    async def get_contracts(self) -> list:
        """Obtiene la lista de contratos asociados a la cuenta scrapeando el portal."""
        url = f"{self.base_url}/ca/group/ematsa/mis-consumos"
        contratos = set()

        try:
            async with self.session.get(url, headers=HEADERS) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")

                    selects = soup.find_all("select")
                    for select in selects:
                        name = select.get("name", "").lower()
                        id_ = select.get("id", "").lower()

                        if "contract" in name or "contract" in id_ or "contrat" in name:
                            for opt in select.find_all("option"):
                                val = opt.get("value")
                                if val and val.strip().isdigit():
                                    contratos.add(val.strip())

                    if not contratos:
                        match = re.search(r'(?:Contracte|Contrato).*?(\d{6,12})', html, re.IGNORECASE)
                        if match:
                            contratos.add(match.group(1))

        except Exception as e:
            _LOGGER.error("Error al obtener la lista de contratos: %s", e)

        return list(contratos)

    async def get_consumos(self) -> dict:
        """Obtiene la lectura acumulada, el histórico mensual y el diario."""
        current_time = time.time()

        if self._cache and (current_time - self._last_update) < 900:
            return self._cache

        p_auth = ""
        lectura_contador_real = 0.0

        try:
            async with self.session.get(f"{self.base_url}/ca/group/ematsa/mis-consumos", headers=HEADERS) as resp:
                if resp.status == 200:
                    html_base = await resp.text()
                    p_auth = self._extract_p_auth(html_base)

                    match_lectura = re.search(r"(\d+(?:[.,]\d+)?)\s*m³", html_base, re.IGNORECASE)
                    if match_lectura:
                        lectura_contador_real = float(match_lectura.group(1).replace(",", "."))
        except Exception as e:
            _LOGGER.error("Error obteniendo HTML base de Ematsa: %s", e)

        hoy = datetime.now()
        hace_un_ano = hoy.replace(year=hoy.year - 1)
        hace_30_dias = hoy - timedelta(days=30)

        fecha_fin = hoy.strftime("%d/%m/%Y")
        fecha_inicio_mes = hace_un_ano.strftime("%d/%m/%Y")
        fecha_inicio_dia = hace_30_dias.strftime("%d/%m/%Y")

        datos = {
            "lectura_total": lectura_contador_real,
            "consumo_ayer": 0.0,
            "consumo_mes_actual": 0.0,
            "consumo_ultimo_mes": 0.0,
            "historico": [],
            "historico_diario": []
        }

        # 1. Histórico Mensual
        url_mensual = (
            f"{self.base_url}/ca/group/ematsa/mis-consumos"
            "?p_p_id=MisConsumos&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
            f"&p_auth={p_auth}"
            "&_MisConsumos_op=buscarConsumosMensual"
            f"&_MisConsumos_fechaInicio={fecha_inicio_mes}"
            f"&_MisConsumos_fechaFin={fecha_fin}"
            "&_MisConsumos_inicio=0&_MisConsumos_fin=12"
        )

        try:
            async with self.session.get(url_mensual, headers=HEADERS) as response:
                if response.status == 200:
                    try:
                        json_res = await response.json(content_type=None)
                    except Exception:
                        json_res = {}

                    if not isinstance(json_res, dict):
                        json_res = {}

                    lista_consumos = json_res.get("consumos", [])
                    historico_parsed = []

                    for item in lista_consumos:
                        fecha_str = item.get("fechaConsumo", "")
                        consumo_str = item.get("consumo", "0").replace(",", ".")
                        valor_num = float(consumo_str)

                        partes = fecha_str.lower().split()
                        if len(partes) == 2:
                            mes_txt, anio_txt = partes[0], partes[1]
                            num_mes = MESES_MAP.get(mes_txt[:3], 1)
                            fecha_iso = f"{anio_txt}-{num_mes:02d}-01"
                        else:
                            fecha_iso = fecha_str

                        historico_parsed.append({
                            "fecha": fecha_iso,
                            "consumo": valor_num,
                            "etiqueta": fecha_str
                        })

                    datos["historico"] = historico_parsed
                    if historico_parsed:
                        datos["consumo_mes_actual"] = historico_parsed[0]["consumo"]
                    if len(historico_parsed) > 1:
                        datos["consumo_ultimo_mes"] = historico_parsed[1]["consumo"]
        except Exception as err:
            _LOGGER.error("Error obteniendo consumos mensuales: %s", err)

        # 2. Histórico Diario (Limitado a 31 días)
        url_diaria = (
            f"{self.base_url}/ca/group/ematsa/mis-consumos"
            "?p_p_id=MisConsumos&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
            "&p_p_cacheability=cacheLevelPage"
            f"&p_auth={p_auth}"
            "&_MisConsumos_op=buscarConsumosDiaria"
            f"&_MisConsumos_fechaInicio={fecha_inicio_dia}"
            f"&_MisConsumos_fechaFin={fecha_fin}"
            "&_MisConsumos_inicio=0&_MisConsumos_fin=31"
        )

        try:
            async with self.session.get(url_diaria, headers=HEADERS) as response_dia:
                if response_dia.status == 200:
                    try:
                        json_dia = await response_dia.json(content_type=None)
                    except Exception:
                        json_dia = {}

                    if not isinstance(json_dia, dict):
                        json_dia = {}

                    lista_diaria = json_dia.get("consumos", [])
                    historico_diario_parsed = []

                    for item in lista_diaria:
                        fecha_str = item.get("fechaConsumo", "")
                        consumo_str = item.get("consumo", "0").replace(",", ".")
                        valor_num = float(consumo_str)

                        # Traducción robusta del formato "30 de jul. 2026" a YYYY-MM-DD
                        match_f = re.search(r'(\d+)\s+de\s+([a-zA-Zç.]+)\.?\s+(\d{4})', fecha_str.lower())
                        if match_f:
                            d_dia = int(match_f.group(1))
                            m_txt = match_f.group(2)[:3]
                            m_num = MESES_MAP.get(m_txt, 1)
                            a_anio = int(match_f.group(3))
                            fecha_iso = f"{a_anio}-{m_num:02d}-{d_dia:02d}"
                        elif "/" in fecha_str:
                            p = fecha_str.split("/")
                            fecha_iso = f"{p[2]}-{int(p[1]):02d}-{int(p[0]):02d}"
                        else:
                            fecha_iso = fecha_str

                        historico_diario_parsed.append({
                            "fecha": fecha_iso,
                            "consumo": valor_num
                        })

                    datos["historico_diario"] = historico_diario_parsed

                    if historico_diario_parsed:
                        datos["consumo_ayer"] = historico_diario_parsed[-1]["consumo"]

        except Exception as err:
            _LOGGER.error("Error obteniendo consumos diarios: %s", err)

        self._cache = datos
        self._last_update = current_time
        return self._cache