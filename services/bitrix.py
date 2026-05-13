"""
services/bitrix.py — Cliente asíncrono para la REST API de Bitrix24.
Usa el webhook entrante configurado en BITRIX_URL.
Permisos necesarios en el webhook: CRM, Tareas, Usuarios.
"""
import httpx
import config

_TIMEOUT = 30


async def api_call(method: str, params: dict = None) -> dict:
    """
    Llamada genérica a la API REST de Bitrix24.
    method: e.g. "crm.contact.list", "crm.lead.update"
    """
    url = f"{config.BITRIX_URL.rstrip('/')}/{method}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(url, json=params or {})
        r.raise_for_status()
        return r.json()


# ─── Contactos ────────────────────────────────────────────────────────────────

async def search_contacts_by_email(email: str) -> list[dict]:
    """Busca contactos cuyo campo EMAIL coincida. Devuelve lista (vacía si no hay)."""
    data = await api_call("crm.contact.list", {
        "limit":  1,
        "order":  {"DATE_CREATE": "DESC"},
        "filter": {"EMAIL": email},
        "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL"],
    })
    return data.get("result", [])


async def create_contact(fields: dict) -> dict:
    """Crea un contacto CRM. Devuelve {result: id}."""
    return await api_call("crm.contact.add", {"fields": fields})


async def create_lead(fields: dict) -> dict:
    """Crea un lead CRM. Devuelve {result: id}."""
    return await api_call("crm.lead.add", {"fields": fields})


async def create_crm_item(entity_type_id: int, fields: dict) -> dict:
    """Crea un elemento en un pipeline SPA (crm.item.add). Devuelve el item."""
    return await api_call("crm.item.add", {
        "entityTypeId": entity_type_id,
        "fields": fields,
    })


async def search_leads_by_email(email: str) -> list[dict]:
    """Busca leads cuyo EMAIL coincida."""
    data = await api_call("crm.lead.list", {
        "filter": {"EMAIL": email},
        "select": ["ID", "TITLE", "NAME", "LAST_NAME", "EMAIL", "PHONE", "ASSIGNED_BY_ID"],
    })
    return data.get("result", [])


# ─── Leads ────────────────────────────────────────────────────────────────────

async def update_lead(lead_id: str | int, fields: dict) -> dict:
    """Actualiza campos de un lead."""
    return await api_call("crm.lead.update", {
        "id":     lead_id,
        "fields": fields,
    })


# ─── Timeline ─────────────────────────────────────────────────────────────────

async def add_timeline_comment(
    entity_type: str,
    entity_id: str | int,
    comment: str,
) -> dict:
    """
    Añade un comentario al timeline de una entidad CRM.
    entity_type: "lead" | "contact" | "deal"
    """
    return await api_call("crm.timeline.comment.add", {
        "fields": {
            "ENTITY_ID":   entity_id,
            "ENTITY_TYPE": entity_type,
            "COMMENT":     comment,
        }
    })


# ─── Tareas ───────────────────────────────────────────────────────────────────

async def create_task(fields: dict) -> dict:
    """Crea una tarea en Bitrix24."""
    return await api_call("tasks.task.add", {"fields": fields})


# ─── Usuarios ─────────────────────────────────────────────────────────────────

async def get_user(user_id: str | int) -> dict:
    """Obtiene datos de un usuario por ID."""
    data = await api_call("user.get", {"ID": user_id})
    result = data.get("result", [])
    return result[0] if result else {}
