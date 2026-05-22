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
        "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "ASSIGNED_BY_ID"],
    })
    return data.get("result", [])


async def create_contact(fields: dict) -> dict:
    """Crea un contacto CRM. Devuelve {result: id}."""
    return await api_call("crm.contact.add", {"fields": fields})


# ─── SPA Items ────────────────────────────────────────────────────────────────

async def create_crm_item(entity_type_id: int, fields: dict) -> dict:
    """Crea un elemento en un pipeline SPA (crm.item.add). Devuelve el item."""
    return await api_call("crm.item.add", {
        "entityTypeId": entity_type_id,
        "fields": fields,
    })


async def update_crm_item(entity_type_id: int, item_id: str | int, fields: dict) -> dict:
    """Actualiza un elemento SPA (crm.item.update)."""
    return await api_call("crm.item.update", {
        "entityTypeId": entity_type_id,
        "id":           item_id,
        "fields":       fields,
    })


# ─── Timeline ─────────────────────────────────────────────────────────────────

async def add_timeline_comment(
    entity_type: str,
    entity_id: str | int,
    comment: str,
) -> dict:
    """
    Añade un comentario al timeline de una entidad CRM.
    entity_type: "dynamic_1034" | "contact" | "deal"
    """
    return await api_call("crm.timeline.comment.add", {
        "fields": {
            "ENTITY_ID":   entity_id,
            "ENTITY_TYPE": entity_type,
            "COMMENT":     comment,
        }
    })


# ─── Actividades / Email binding ──────────────────────────────────────────────

async def find_email_activity(subject: str, from_email: str, contact_id: str | int | None = None) -> int | None:
    """
    Busca la actividad de email más reciente vinculada al contacto (si se conoce)
    o que coincida con el asunto y el remitente.
    Devuelve el ID entero o None si no se encuentra.
    """
    # Búsqueda por contacto + asunto (más precisa)
    if contact_id:
        data = await api_call("crm.activity.list", {
            "order":  {"ID": "DESC"},
            "filter": {
                "OWNER_TYPE_ID": 3,
                "OWNER_ID":      int(contact_id),
                "%SUBJECT":      subject,
            },
            "select": ["ID", "SUBJECT", "TYPE_ID", "COMMUNICATIONS"],
            "start":  0,
        })
        results = data.get("result", [])
        if results:
            return int(results[0]["ID"])

    # Fallback: búsqueda por asunto y remitente sin filtro de tipo
    data = await api_call("crm.activity.list", {
        "order":  {"ID": "DESC"},
        "filter": {"%SUBJECT": subject},
        "select": ["ID", "SUBJECT", "TYPE_ID", "COMMUNICATIONS"],
        "start":  0,
    })
    results = data.get("result", [])
    for act in results:
        for comm in act.get("COMMUNICATIONS", []):
            if comm.get("VALUE", "").lower() == from_email.lower():
                return int(act["ID"])
    return int(results[0]["ID"]) if results else None


async def bind_activity_to_item(activity_id: int, entity_type_id: int, entity_id: str | int) -> dict:
    """Vincula una actividad existente a un item CRM (crm.activity.binding.add)."""
    return await api_call("crm.activity.binding.add", {
        "activityId":   activity_id,
        "entityTypeId": entity_type_id,
        "entityId":     int(entity_id),
    })
