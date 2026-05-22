"""
handlers/extraccion_1er.py — Escenario 1.1: Extracción Datos - 1er correo

Recibe (de clasificacion.py):
    message_id, thread_id, categoria_correo, tipo_correo, bot_humano, row, subject

Lógica:
  A) Si tipo != "accion"  → devuelve {"status": "ok"}
  B) Si categoria == "Franquicia" → GPT franquicia, crea Contact + item pipeline 169
  C) Caso normal (accion, no Franquicia):
     - GPT extrae: nombre, apellido, dni, telefono, n_contrato, n_modulo, centro
     - Si hay contacto en Bitrix → crea Lead con ese contacto
     - Si no hay contacto → crea Contact + Lead
     - Crea registro en Airtable Datos extraídos
     - Si hay adjuntos → comenta en timeline Bitrix

Devuelve:
    {ticket_id, nombre, apellido, Cliente (bool), datos_extraidos_id}
"""
import asyncio
import logging
import re
import config
from services import gmail, airtable, bitrix, openai_svc

logger = logging.getLogger("email-cgi")

_ASSIGNED_BY_ID = "6358"

_PROMPT_EXTRACCION = (
    "Actúa como experto en estructurar datos extraídos de correos con información no estructurada. "
    "A continuación se indica los rótulos de los datos que se requiere extraer:\n"
    "Los datos que se van a extraer son del emisor del correo.\n"
    "En caso, el cliente no haya indicado Nombre y/o Apellido, indicar \" \". "
    "En caso no indique DNI NIF CIF NIE Pasaporte rellenar con \"00000000\". "
    "En caso NO encuentres Teléfono Móvil colocar \"000000000\". "
    "Luego, para el resto de casos completar con \"No indica\". "
    "Para el \"Nombre de la Compañía\" en cuerpo del correo debe indicar expresamente el nombre "
    "de la compañía a la que pertenece el From Email. "
    "En caso no haya nombre de la compañía completa con \"No indica\". "
    "En el campo de la compañía no consideres a \"Tu Trastero\".\n"
    "Finalmente, verifica si el correo contiene un attachment e indica \"Si\" o \"No\"."
)

_PROMPT_FRANQUICIA = (
    "Actúa como experto en estructurar datos extraídos de correos con información no estructurada. "
    "Los datos que se van a extraer son del emisor del correo.\n"
    "Contexto: somos una empresa de trasteros y los correos que recibimos son de personas "
    "interesadas en montar trasteros en franquicia. Ejemplos:\n"
    "\"Tengo un local de 400m en Alcoy, estaba interesado en montar trasteros.\"\n"
    "\"Disponemos de una nave de 1400 m² y buscamos un operador que nos ayude a establecer "
    "este negocio de self-storage en franquicia.\""
)

_PARAMS_EXTRACCION = [
    {"name": "nombre",     "type": "string", "description": "nombre del usuario",                            "isRequired": False},
    {"name": "apellido",   "type": "string", "description": "apellido del usuario",                          "isRequired": False},
    {"name": "dni",        "type": "string", "description": "DNI / NIF / CIF / NIE / Pasaporte del usuario", "isRequired": False},
    {"name": "telefono",   "type": "string", "description": "telefono del usuario",                          "isRequired": False},
    {"name": "email",      "type": "string", "description": "email del usuario",                             "isRequired": False},
    {"name": "n_contrato", "type": "string", "description": "número de contrato del cliente",                "isRequired": False},
    {"name": "n_modulo",   "type": "string", "description": "número de módulo de trastero del cliente",      "isRequired": False},
    {"name": "centro",     "type": "string", "description": "Centro donde el cliente tiene su módulo",       "isRequired": False},
    {"name": "prioridad",  "type": "string", "description": "baja, media o alta",                            "isRequired": False},
]

_PRIORIDAD_STAGE = {
    "baja":  "DT1034_120:NEW",
    "media": "DT1034_120:PREPARATION",
    "alta":  "DT1034_120:CLIENT",
}

_PARAMS_FRANQUICIA = [
    {"name": "nombre",             "type": "string", "description": "nombre del usuario",                            "isRequired": False},
    {"name": "interes",            "type": "string", "description": "interés o requerimiento del usuario",           "isRequired": False},
    {"name": "centro_operativo",   "type": "string", "description": "ciudad donde está ubicado el centro",           "isRequired": False},
    {"name": "direccion_inmueble", "type": "string", "description": "Dirección del Inmueble",                        "isRequired": False},
    {"name": "localidad",          "type": "string", "description": "localidad donde está ubicado el inmueble",      "isRequired": False},
    {"name": "provincia",          "type": "string", "description": "provincia donde está ubicado el inmueble",      "isRequired": False},
    {"name": "codigo_postal",      "type": "string", "description": "Código Postal del inmueble",                    "isRequired": False},
    {"name": "tamano",             "type": "string", "description": "tamaño del inmueble",                           "isRequired": False},
    {"name": "numero_plantas",     "type": "string", "description": "cantidad de plantas del inmueble",              "isRequired": False},
]


def _datos_extraidos_fields(args: dict, gpt: dict, ticket_id: str,
                             from_email: str, email_to: str, subject: str) -> dict:
    return {
        "fldD5UfZHBGw8VnB9": args.get("categoria_correo", ""),
        "fldGQIcSIN49d4OzB": subject,
        "fldGQUW9FLFW7glj9": args.get("categoria_correo_api", ""),
        "fldHgTlccdFZMzHUU": gpt.get("nombre", ""),
        "fldI9gglSHnvp0ptM": args.get("thread_id", ""),
        "fldPeM5wlULywrkmD": args.get("tipo_correo", ""),
        "fldQpoEAFbHYN7TmP": gpt.get("apellido", ""),
        "fldZvZhDdcQdc0zxq": email_to,
        "flddKn7zZbx4JxG2C": from_email,
        "fldkbeuamIponQYBs": from_email,
        "fldhg38Me05r19rBb": gpt.get("n_contrato", ""),
        "fldiGEfwffi6SSteD": ticket_id,
        "fldkENBRVsvYqJX10": gpt.get("telefono", ""),
        "fldkQKHpXP7eQuD3E": gpt.get("centro", ""),
        "fldrIiOucUDZMiUXW": gpt.get("dni", ""),
        "fldv20T36rftFfXLu": gpt.get("n_modulo", ""),
    }


async def run(args: dict) -> dict:
    message_id = args["message_id"]
    categoria  = args.get("categoria_correo", "")
    tipo       = args.get("tipo_correo", "")

    # A) No es accion
    if tipo != "accion":
        logger.info(f"[1.1] tipo={tipo!r} — no es accion, se omite extracción")
        return {"status": "ok"}

    email      = await gmail.get_email(message_id)
    adjuntos   = await gmail.get_attachments(message_id)
    from_email = email.get("fromEmail", "")
    to_list    = email.get("to", [])
    email_to   = to_list[0].get("email", "") if to_list else ""
    subject    = email.get("subject", "")
    body       = email.get("fullTextBody") or email.get("htmlBody") or ""
    has_attach = bool(adjuntos)

    logger.info(f"[1.1] from={from_email} | categoria={categoria} | adjuntos={has_attach}")

    # B) Franquicia
    if categoria.lower() == "franquicia":
        return await _handle_franquicia(args, from_email, email_to, subject, body)

    # C) accion normal
    # Cargar centros para prompt
    centros_records = await airtable.search_records(config.AT_TBL_CENTROS, formula="", max_records=20)
    centros_list    = [r["fields"].get("Centro", "") for r in centros_records if r.get("fields")]
    centros_desc    = ", ".join(c for c in centros_list if c) or "No indica"

    params = [p.copy() for p in _PARAMS_EXTRACCION]
    params[-1]["description"] = f"Centro donde el cliente tiene su módulo. Uno de: {centros_desc}"

    gpt_data = await openai_svc.extract_structured_data(
        text=f"{from_email} {body}",
        prompt=_PROMPT_EXTRACCION + f"\nCentros disponibles: {centros_desc}",
        parameters=params,
    )
    logger.info(f"[1.1] GPT: nombre={gpt_data.get('nombre')} | centro={gpt_data.get('centro')} | prioridad={gpt_data.get('prioridad')}")

    stage_id = _PRIORIDAD_STAGE.get((gpt_data.get("prioridad") or "").lower(), "DT1034_120:NEW")

    # Buscar contacto Bitrix
    bitrix_contacts = await bitrix.search_contacts_by_email(from_email)
    contact_found   = len(bitrix_contacts) > 0

    if contact_found:
        return await _with_contact(args, gpt_data, from_email, email_to, subject, adjuntos, bitrix_contacts[0], stage_id, body)
    else:
        return await _without_contact(args, gpt_data, from_email, email_to, subject, adjuntos, stage_id, body)


def _attachments_to_bitrix_files(adjuntos: list) -> list[list]:
    """Convierte adjuntos de Gmail (base64url) al formato FILES de Bitrix [["nombre", "base64"]]."""
    files = []
    for att in adjuntos:
        raw = att.get("data", "")
        # base64url → base64 estándar
        std = raw.replace("-", "+").replace("_", "/")
        padding = (4 - len(std) % 4) % 4
        std += "=" * padding
        files.append([att.get("filename", "adjunto"), std])
    return files


def _clean_body(text: str) -> str:
    """Limpia HTML y normaliza espacios/saltos de línea del cuerpo del correo."""
    # Quitar etiquetas HTML
    text = re.sub(r"<[^>]+>", " ", text)
    # Decodificar entidades comunes
    text = text.replace("&nbsp;", " ").replace("&amp;", "&") \
               .replace("&lt;", "<").replace("&gt;", ">") \
               .replace("&quot;", '"').replace("&#39;", "'")
    # Colapsar espacios múltiples en cada línea
    lines = [re.sub(r" {2,}", " ", line).strip() for line in text.splitlines()]
    # Eliminar líneas vacías consecutivas (máx 1 en blanco seguida)
    cleaned = []
    prev_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue
        cleaned.append(line)
        prev_blank = is_blank
    return "\n".join(cleaned).strip()


def _build_timeline_comment(from_email, subject, adjuntos, gpt_data, nombre, apellido, body):
    n_adj     = len(adjuntos) if adjuntos else 0
    adj_str   = f"{n_adj} archivo(s)" if n_adj else "No"
    telefono  = gpt_data.get("telefono", "")
    centro    = gpt_data.get("centro", "")
    prioridad = gpt_data.get("prioridad", "")
    body_text = _clean_body(body or "")[:3000]
    return (
        f"📧 Correo recibido\n"
        f"De: {from_email}\n"
        f"Asunto: {subject}\n"
        f"Adjuntos: {adj_str}\n"
        f"\n"
        f"Nombre: {nombre} {apellido}\n"
        f"Teléfono: {telefono}\n"
        f"Centro: {centro}\n"
        f"Prioridad: {prioridad}\n"
        f"\n"
        f"--- Mensaje ---\n"
        f"{body_text}"
    )


async def _with_contact(args, gpt_data, from_email, email_to, subject, adjuntos, contact, stage_id="DT1034_120:NEW", body=""):
    contact_id  = contact["ID"]
    nombre_bx   = contact.get("NAME", gpt_data.get("nombre", ""))
    apellido_bx = contact.get("LAST_NAME", gpt_data.get("apellido", ""))
    assigned_by = contact.get("ASSIGNED_BY_ID") or _ASSIGNED_BY_ID

    item_resp = await bitrix.create_crm_item(1034, {
        "title":        f"CGI - Respuesta automática: {args.get('categoria_correo', '')}",
        "stageId":      stage_id,
        "contactId":    contact_id,
        "sourceId":     "EMAIL",
        "assignedById": assigned_by,
    })
    ticket_id = str(item_resp.get("result", {}).get("item", {}).get("id", ""))

    at_record = await airtable.create_record(
        config.AT_TBL_DATOS_EXTRAIDOS,
        _datos_extraidos_fields(args, gpt_data, ticket_id, from_email, email_to, subject),
    )
    at_id = at_record.get("id", "")

    if ticket_id:
        await bitrix.add_timeline_comment(
            "dynamic_1034", ticket_id,
            _build_timeline_comment(from_email, subject, adjuntos, gpt_data, nombre_bx, apellido_bx, body),
            files=_attachments_to_bitrix_files(adjuntos) if adjuntos else None,
        )
        try:
            await asyncio.sleep(60)
            activity_id = await bitrix.find_email_activity(subject, from_email, contact_id)
            if activity_id:
                await bitrix.bind_activity_to_item(activity_id, 1034, ticket_id)
                logger.info(f"[1.1] Email activity {activity_id} vinculado al ticket {ticket_id}")
            else:
                logger.info(f"[1.1] No se encontró actividad email para vincular | subject={subject!r}")
        except Exception as exc:
            logger.warning(f"[1.1] No se pudo vincular actividad email: {type(exc).__name__}: {exc!r}")

    logger.info(f"[1.1] Item 1034 (contacto existente) | ticket_id={ticket_id} | at={at_id}")
    return {
        "nombre": nombre_bx, "apellido": apellido_bx, "email": from_email,
        "dni": gpt_data.get("dni", ""), "n_modulo": gpt_data.get("n_modulo", ""),
        "n_contrato": gpt_data.get("n_contrato", ""), "telefono": gpt_data.get("telefono", ""),
        "ticket_id": ticket_id, "centro": gpt_data.get("centro", ""),
        "datos_extraidos_id": at_id, "Cliente": True,
    }


async def _without_contact(args, gpt_data, from_email, email_to, subject, adjuntos, stage_id="DT1034_120:NEW", body=""):
    contact_resp = await bitrix.create_contact({
        "NAME":        gpt_data.get("nombre", ""),
        "LAST_NAME":   gpt_data.get("apellido", ""),
        "EMAIL":       [{"VALUE": from_email, "TYPE_ID": "EMAIL", "VALUE_TYPE": "WORK"}],
        "PHONE":       [{"VALUE": gpt_data.get("telefono", ""), "TYPE_ID": "PHONE", "VALUE_TYPE": "WORK"}],
        "TYPE_ID":     "CLIENT",
        "SECOND_NAME": " ",
        "UF_CRM_6FB0A682":   "122",
        "UF_CRM_FD1274F7":   "168",
        "UF_CRM_1593078333": "31516",
    })
    contact_id = str(contact_resp.get("result", ""))

    item_resp = await bitrix.create_crm_item(1034, {
        "title":        f"CGI - Respuesta automática: {args.get('categoria_correo', '')}",
        "stageId":      stage_id,
        "contactId":    contact_id,
        "sourceId":     "EMAIL",
        "assignedById": _ASSIGNED_BY_ID,
    })
    ticket_id = str(item_resp.get("result", {}).get("item", {}).get("id", ""))

    at_record = await airtable.create_record(
        config.AT_TBL_DATOS_EXTRAIDOS,
        _datos_extraidos_fields(args, gpt_data, ticket_id, from_email, email_to, subject),
    )
    at_id = at_record.get("id", "")

    if ticket_id:
        await bitrix.add_timeline_comment(
            "dynamic_1034", ticket_id,
            _build_timeline_comment(
                from_email, subject, adjuntos, gpt_data,
                gpt_data.get("nombre", ""), gpt_data.get("apellido", ""), body,
            ),
        )
        try:
            await asyncio.sleep(60)
            # contact_id recién creado — Bitrix no lo tenía al llegar el email
            activity_id = await bitrix.find_email_activity(subject, from_email, None)
            if activity_id:
                await bitrix.bind_activity_to_item(activity_id, 1034, ticket_id)
                logger.info(f"[1.1] Email activity {activity_id} vinculado al ticket {ticket_id}")
            else:
                logger.info(f"[1.1] No se encontró actividad email para vincular | subject={subject!r}")
        except Exception as exc:
            logger.warning(f"[1.1] No se pudo vincular actividad email: {type(exc).__name__}: {exc!r}")

    logger.info(f"[1.1] Item 1034 (contacto nuevo) | ticket_id={ticket_id} | at={at_id}")
    return {
        "nombre": gpt_data.get("nombre", ""), "apellido": gpt_data.get("apellido", ""),
        "email": from_email, "dni": gpt_data.get("dni", ""),
        "n_modulo": gpt_data.get("n_modulo", ""), "n_contrato": gpt_data.get("n_contrato", ""),
        "telefono": gpt_data.get("telefono", ""), "ticket_id": ticket_id,
        "centro": gpt_data.get("centro", ""), "datos_extraidos_id": at_id, "Cliente": False,
    }


async def _handle_franquicia(args, from_email, email_to, subject, body):
    gpt_data = await openai_svc.extract_structured_data(
        text=f"{from_email} {body}",
        prompt=_PROMPT_FRANQUICIA,
        parameters=_PARAMS_FRANQUICIA,
    )
    logger.info(f"[1.1] Franquicia GPT: nombre={gpt_data.get('nombre')} | localidad={gpt_data.get('localidad')}")

    contact_resp = await bitrix.create_contact({
        "NAME":       gpt_data.get("nombre", ""),
        "EMAIL":      [{"VALUE": from_email, "TYPE_ID": "EMAIL", "VALUE_TYPE": "WORK"}],
        "TYPE_ID":    "OTHER",
        "SECOND_NAME": " ",
        "UF_CRM_6FB0A682":   "122",
        "UF_CRM_FD1274F7":   "168",
        "UF_CRM_1593078333": "31516",
    })
    contact_id = str(contact_resp.get("result", ""))

    item_resp = await bitrix.create_crm_item(169, {
        "title":                 "E-mail de Franquicia Gestionada",
        "stageId":               "DT169_102:NEW",
        "contactId":             contact_id,
        "ufCrm48_1705404278211": gpt_data.get("codigo_postal", ""),
        "ufCrm48_1705404430929": gpt_data.get("interes", ""),
        "ufCrm48_1705404216437": gpt_data.get("direccion_inmueble", ""),
        "ufCrm48_1705404240183": gpt_data.get("localidad", ""),
        "ufCrm48_1705404499208": gpt_data.get("numero_plantas", ""),
    })
    item_id   = item_resp.get("result", {}).get("item", {}).get("id", "")
    ticket_id = f"169_{item_id}"

    at_record = await airtable.create_record(
        config.AT_TBL_DATOS_EXTRAIDOS,
        _datos_extraidos_fields(args, gpt_data, ticket_id, from_email, email_to, subject),
    )
    at_id = at_record.get("id", "")

    logger.info(f"[1.1] Franquicia creada | item={item_id} | at={at_id}")
    return {
        "nombre": gpt_data.get("nombre", ""), "apellido": "",
        "email": from_email, "ticket_id": ticket_id,
        "centro": gpt_data.get("centro_operativo", ""),
        "datos_extraidos_id": at_id, "Cliente": True,
    }
