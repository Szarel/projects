import json
from datetime import datetime
from typing import Any, Dict

from google import genai

from app.core.config import settings


_NAME_PREFIXES = [
    "entre",
    "con",
    "y",
    "el",
    "la",
    "don",
    "doña",
    "sr",
    "sra",
    "sr.",
    "sra.",
]


def _clean_name(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = name.strip().strip(",;:.- ")
    parts = cleaned.split()
    # Drop leading prefixes/titles/connectors
    while parts and parts[0].lower().strip(". ") in _NAME_PREFIXES:
        parts.pop(0)
    cleaned = " ".join(parts)
    return cleaned or None


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
        "Eres un extractor de contratos de arriendo en Chile. Devuelve SOLO un JSON plano con estas claves exactas: "
        "arrendatario_nombre, arrendatario_rut, propietario_nombre, propietario_rut, fecha_inicio (YYYY-MM-DD), "
        "fecha_fin (YYYY-MM-DD), dia_pago (1-31), renta_mensual (numero en CLP), moneda (CLP o UF), direccion. "
        "Reglas: 1) No inventes; si falta, usa null. 2) Fechas en ISO; si hay rango, usa inicio mas temprano y fin mas tardio del contrato. "
        "3) Dia de pago: si dice 'primeros dias habiles', usa 5. 4) Renta: monto principal de arriendo (el mayor si hay varios), en CLP, sin simbolos ni puntos. "
        "5) RUT: usa el que aparezca (formato 9.999.999-9), no generes uno. 6) Direccion: texto breve del inmueble. "
        "7) Nombres: elimina conectores ('entre', 'con', 'y'), articulos ('el', 'la'), titulos ('don', 'doña', 'sr', 'sra'). Devuelve solo el nombre completo o razon social tal como aparece, sin palabras extra. "
        "Ejemplo de salida: {\"arrendatario_nombre\": \"Intendencia Regional de Atacama\", \"arrendatario_rut\": \"60.511.030-4\", \"propietario_nombre\": \"Hector Patricio Olave Fara\", \"propietario_rut\": \"9.647.123-8\", \"fecha_inicio\": \"2003-04-01\", \"fecha_fin\": \"2003-12-31\", \"dia_pago\": 5, \"renta_mensual\": 350000, \"moneda\": \"CLP\", \"direccion\": \"Colipi 611, Copiapo, Atacama\"}. "
        "Devuelve solo JSON, sin texto extra ni backticks."
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
        data = json.loads(content)
        if isinstance(data, dict):
            data["arrendatario_nombre"] = _clean_name(data.get("arrendatario_nombre"))
            data["propietario_nombre"] = _clean_name(data.get("propietario_nombre"))
        return data
    except Exception:
        return {}


def extract_payment_from_image(raw: bytes, mime_type: str | None = None) -> Dict[str, Any]:
    """Use Gemini to read a payment receipt image and return structured fields.

    Expected keys: monto_pagado (number), fecha_pago (YYYY-MM-DD), medio_pago (str|None), referencia (str|None).
    Returns empty dict on missing config or errors.
    """
    client = _client()
    if not client or not raw:
        return {}

    mime = mime_type or "image/jpeg"
    prompt = (
        "Eres un lector de comprobantes de pago en Chile. Devuelve SOLO un JSON plano con estas claves exactas: "
        "monto_pagado (numero, CLP, sin puntos), fecha_pago (YYYY-MM-DD), medio_pago (texto corto como 'transferencia' o banco), "
        "referencia (codigo de transaccion u observacion). Si falta un dato usa null. No inventes montos."
    )

    def _first_text(resp: Any) -> str:
        try:
            for cand in getattr(resp, "candidates", []) or []:
                parts = getattr(getattr(cand, "content", None), "parts", []) or []
                for p in parts:
                    txt = getattr(p, "text", None)
                    if txt:
                        return str(txt)
        except Exception:
            return ""
        return ""

    def _parse_response(resp: Any) -> Dict[str, Any]:
        content = (getattr(resp, "text", "") or _first_text(resp) or "").strip()
        if not content:
            return {}
        if content.startswith("`"):
            content = content.strip("` ")
        if content.lower().startswith("json"):
            content = content[4:].strip()
        data = json.loads(content)
        if not isinstance(data, dict):
            return {}
        raw_date = data.get("fecha_pago")
        if raw_date:
            try:
                parsed = datetime.fromisoformat(str(raw_date)).date()
                data["fecha_pago"] = parsed.isoformat()
            except Exception:
                data["fecha_pago"] = None
        return data

    try:
        # Try sending raw bytes first.
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=[{"role": "user", "parts": [prompt, {"inline_data": {"mime_type": mime, "data": raw}}]}],
        )
        data = _parse_response(resp)
        if data:
            return data
        # Fallback: if empty, retry once (some clients require bytes-like again).
        resp2 = client.models.generate_content(
            model=settings.gemini_model,
            contents=[{"role": "user", "parts": [prompt, {"inline_data": {"mime_type": mime, "data": raw}}]}],
        )
        return _parse_response(resp2)
    except Exception:
        return {}
