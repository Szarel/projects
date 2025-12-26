import json
from typing import Any, Dict

from google import genai

from app.core.config import settings


def _client() -> genai.Client | None:
    api_key = settings.gemini_api_key
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def extract_contract_fields(text: str) -> Dict[str, Any]:
    """Use Gemini to extract contract fields from raw PDF text.

    Returns empty dict on missing config or errors. Expected keys:
    - arrendatario_nombre, arrendatario_rut
    - propietario_nombre, propietario_rut
    - fecha_inicio, fecha_fin (YYYY-MM-DD)
    - dia_pago (int 1-31)
    - renta_mensual (number)
    - moneda (CLP/UF)
    - direccion
    """
    client = _client()
    if not client or not text.strip():
        return {}

    prompt = (
        "Eres un extractor de contratos de arriendo en Chile. Devuelve SOLO JSON con estas claves exactas: "
        "arrendatario_nombre, arrendatario_rut, propietario_nombre, propietario_rut, fecha_inicio (YYYY-MM-DD), "
        "fecha_fin (YYYY-MM-DD), dia_pago (1-31), renta_mensual (numero, en CLP), moneda (CLP o UF), direccion. "
        "Reglas: 1) No inventes datos; si no esta, usa null. 2) Formato fecha ISO YYYY-MM-DD. 3) Si hay rango, usa inicio mas temprano y fin mas tardio del contrato. "
        "4) Dia de pago: si dice 'primeros dias habiles' o similar, usa 5. 5) renta_mensual: toma el monto principal de arriendo (el mayor si hay varios) en CLP, sin puntos ni simbolos. "
        "6) RUT: usa el que aparezca (formato 9.999.999-9); no generes uno. 7) direccion: texto breve de direccion del inmueble. "
        "Devuelve un JSON plano sin texto adicional ni backticks."
    )

    try:
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=[prompt, f"Texto del contrato:\n{text[:12000]}"]
        )
        content = (resp.text or "").strip()
        if not content:
            return {}
        if content.startswith("`"):
            content = content.strip("` ")
        if content.lower().startswith("json"):
            content = content[4:].strip()
        return json.loads(content)
    except Exception:
        return {}
