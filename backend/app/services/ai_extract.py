import json
from typing import Any, Dict

from openai import OpenAI

from app.core.config import settings


def _client() -> OpenAI | None:
    if not settings.ai_api_key:
        return None
    try:
        return OpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url)
    except Exception:
        return None


def extract_contract_fields(text: str) -> Dict[str, Any]:
    """Use LLM to extract contract fields from raw PDF text.

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

    system = (
        "Eres un extractor de datos de contratos de arriendo en Chile. Devuelve un JSON compacto con campos "
        "arrendatario_nombre, arrendatario_rut, propietario_nombre, propietario_rut, fecha_inicio (YYYY-MM-DD), "
        "fecha_fin (YYYY-MM-DD), dia_pago (1-31), renta_mensual (numero), moneda (CLP/UF), direccion. "
        "Si no sabes un campo, deja null."
    )
    user = f"Texto del contrato:\n{text[:12000]}"

    try:
        resp = client.chat.completions.create(
            model=settings.ai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        content = resp.choices[0].message.content if resp.choices else None
        if not content:
            return {}
        content = content.strip()
        if content.startswith("`"):
            content = content.strip("` ")
        if content.lower().startswith("json"):
            content = content[4:].strip()
        return json.loads(content)
    except Exception:
        return {}
