"""
services/bitrix.py — Cliente asíncrono para la REST API de Bitrix24.
Usa el webhook entrante configurado en BITRIX_URL.
Permisos necesarios en el webhook: CRM, Tareas, Usuarios.
"""
import datetime
import httpx
import pytz
import config

_TIMEOUT = 30
_CREATED_BY_ID = 6358


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
    files: list[list] = None,
) -> dict:
    """
    Añade un comentario al timeline de una entidad CRM.
    entity_type: "dynamic_1034" | "contact" | "deal"
    files: [["nombre.ext", "base64content"], ...]
    """
    fields = {
        "ENTITY_ID":   entity_id,
        "ENTITY_TYPE": entity_type,
        "COMMENT":     comment,
    }
    if files:
        fields["FILES"] = files
    return await api_call("crm.timeline.comment.add", {"fields": fields})


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


# ─── Tareas ───────────────────────────────────────────────────────────────────

def next_business_day_deadline() -> str:
    """
    Devuelve el próximo día laboral (L-V) a las 09:00 hora de Madrid,
    formateado para Bitrix24. Siempre es el día SIGUIENTE al actual,
    saltando sábados y domingos.
    """
    madrid    = pytz.timezone("Europe/Madrid")
    ahora     = datetime.datetime.now(madrid)
    siguiente = ahora.date() + datetime.timedelta(days=1)
    while siguiente.weekday() >= 5:
        siguiente += datetime.timedelta(days=1)
    deadline_dt = madrid.localize(datetime.datetime(siguiente.year, siguiente.month, siguiente.day, 9, 0, 0))
    offset      = deadline_dt.strftime("%z")
    offset_fmt  = f"{offset[:3]}:{offset[3:]}"
    return deadline_dt.strftime(f"%Y-%m-%dT%H:%M:%S{offset_fmt}")


async def create_task(
    title: str,
    responsible_id: str | int,
    entity_type_id: int,
    entity_id: str | int,
    description: str = "",
    deadline: str | None = None,
) -> dict:
    """
    Crea una tarea (tasks.task.add) vinculada a un elemento CRM (SPA/deal/lead/contact).
    entity_type_id: entityTypeId del pipeline SPA (p.ej. 1034 → binding "T40A_{id}").
    deadline: ISO 8601 con offset; por defecto, próximo día laboral 09:00 Madrid.
    """
    return await api_call("tasks.task.add", {
        "fields": {
            "TITLE":          title,
            "CREATED_BY":     _CREATED_BY_ID,
            "RESPONSIBLE_ID": responsible_id,
            "DESCRIPTION":    description,
            "DEADLINE":       deadline or next_business_day_deadline(),
            "UF_CRM_TASK":    [f"T{entity_type_id:X}_{entity_id}"],
        }
    })
