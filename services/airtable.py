"""
services/airtable.py — Cliente asíncrono para la API REST de Airtable.
Usa httpx para todas las llamadas. Los nombres de campo se usan tal cual
(useColumnId=false por defecto en la API de Airtable).
"""
import httpx
import config

_BASE_URL = f"https://api.airtable.com/v0/{config.AIRTABLE_BASE_ID}"
_TIMEOUT  = 30


def _headers() -> dict:
    return {
        "Authorization":  f"Bearer {config.AIRTABLE_TOKEN}",
        "Content-Type":   "application/json",
    }


# ─── API pública ──────────────────────────────────────────────────────────────

async def search_records(
    table_id: str,
    formula: str,
    fields: list[str] = None,
    max_records: int = 1,
    view: str = None,
) -> list[dict]:
    """Busca registros con una fórmula Airtable. Devuelve lista de records."""
    params: dict = {
        "filterByFormula": formula,
        "maxRecords":      max_records,
    }
    if view:
        params["view"] = view

    # httpx envía listas como params repetidos (fields[]=…)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(
            f"{_BASE_URL}/{table_id}",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        records = r.json().get("records", [])

    # Filtrar campos si se especificaron (la API acepta fields[] pero es verboso)
    if fields and records:
        for rec in records:
            rec["fields"] = {k: v for k, v in rec["fields"].items() if k in fields}

    return records


async def get_record(table_id: str, record_id: str) -> dict:
    """Obtiene un registro por su ID."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(
            f"{_BASE_URL}/{table_id}/{record_id}",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


async def create_record(table_id: str, fields: dict) -> dict:
    """Crea un nuevo registro. Devuelve el record creado."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(
            f"{_BASE_URL}/{table_id}",
            headers=_headers(),
            json={"fields": fields},
        )
        r.raise_for_status()
        return r.json()


async def update_record(table_id: str, record_id: str, fields: dict) -> dict:
    """Actualiza campos de un registro existente (PATCH — solo toca los campos indicados)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.patch(
            f"{_BASE_URL}/{table_id}/{record_id}",
            headers=_headers(),
            json={"fields": fields},
        )
        r.raise_for_status()
        return r.json()


async def upsert_record(table_id: str, record_id: str | None, fields: dict) -> dict:
    """
    Actualiza si record_id está disponible, crea si no.
    Solo escribe los campos que tienen valor (ignora None para no borrar datos existentes).
    """
    clean_fields = {k: v for k, v in fields.items() if v is not None and v != ""}
    if not clean_fields:
        return {}
    if record_id:
        return await update_record(table_id, record_id, clean_fields)
    return await create_record(table_id, clean_fields)
