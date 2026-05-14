"""
handlers/extraccion_1er.py — Escenario 1.1: Extracción Datos - 1er correo

Recibe (de clasificacion.py):
    message_id, thread_id, categoria_correo, tipo_correo, bot_humano, row, subject

Lógica:
  A) Si tipo != "Requerimiento"  → devuelve {"status": "ok"}
  B) Si categoria == "Franquicia" → GPT franquicia, crea Contact + item pipeline 169
  C) Caso normal (Requerimiento, no Franquicia):
     - GPT extrae: nombre, apellido, dni, telefono, n_contrato, n_modulo, centro
     - Si hay contacto en Bitrix → crea Lead con ese contacto
     - Si no hay contacto → crea Contact + Lead
     - Crea registro en Airtable Datos extraídos
     - Si hay adjuntos → comenta en timeline Bitrix

Devuelve:
    {lead_id, nombre, apellido, Cliente (bool), datos_extraidos_id}
"""
import logging
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
]

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


def _datos_extraidos_fields(args: dict, gpt: dict, lead_id: str,
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
        "fldiGEfwffi6SSteD": lead_id,
        "fldkENBRVsvYqJX10": gpt.get("telefono", ""),
        "fldkQKHpXP7eQuD3E": gpt.get("centro", ""),
        "fldrIiOucUDZMiUXW": gpt.get("dni", ""),
        "fldv20T36rftFfXLu": gpt.get("n_modulo", ""),
    }


async def run(args: dict) -> dict:
    message_id = args["message_id"]
    categoria  = args.get("categoria_correo", "")
    tipo       = args.get("tipo_correo", "")

    # A) No es Requerimiento
    if tipo != "Requerimiento":
        logger.info(f"[1.1] tipo={tipo!r} — no es Requerimiento, se omite extracción")
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
    if categoria == "Franquicia":
        return await _handle_franquicia(args, from_email, email_to, subject, body)

    # C) Requerimiento normal
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
    logger.info(f"[1.1] GPT: nombre={gpt_data.get('nombre')} | centro={gpt_data.get('centro')}")

    # Buscar contacto Bitrix
    bitrix_contacts = await bitrix.search_contacts_by_email(from_email)
    contact_found   = len(bitrix_contacts) > 0

    if contact_found:
        return await _with_contact(args, gpt_data, from_email, email_to, subject, has_attach, bitrix_contacts[0])
    else:
        return await _without_contact(args, gpt_data, from_email, email_to, subject, has_attach)


async def _with_contact(args, gpt_data, from_email, email_to, subject, has_attach, contact):
    contact_id  = contact["ID"]
    nombre_bx   = contact.get("NAME", gpt_data.get("nombre", ""))
    apellido_bx = contact.get("LAST_NAME", gpt_data.get("apellido", ""))

    lead_resp = await bitrix.create_lead({
        "TITLE":          f"CGI - Respuesta automática: {args.get('categoria_correo', '')}",
        "STATUS_ID":      "NEW",
        "CONTACT_IDS":    [contact_id],
        "ASSIGNED_BY_ID": _ASSIGNED_BY_ID,
    })
    lead_id = str(lead_resp.get("result", ""))

    at_record = await airtable.create_record(
        config.AT_TBL_DATOS_EXTRAIDOS,
        _datos_extraidos_fields(args, gpt_data, lead_id, from_email, email_to, subject),
    )
    at_id = at_record.get("id", "")

    if has_attach:
        await bitrix.add_timeline_comment(
            "LEAD", lead_id,
            f"📧 CORREO RECIBIDO de {from_email}:\nAsunto: {subject}"
        )

    logger.info(f"[1.1] Lead (contacto existente) | lead_id={lead_id} | at={at_id}")
    return {
        "nombre": nombre_bx, "apellido": apellido_bx, "email": from_email,
        "dni": gpt_data.get("dni", ""), "n_modulo": gpt_data.get("n_modulo", ""),
        "n_contrato": gpt_data.get("n_contrato", ""), "telefono": gpt_data.get("telefono", ""),
        "lead_id": lead_id, "centro": gpt_data.get("centro", ""),
        "datos_extraidos_id": at_id, "Cliente": True,
    }


async def _without_contact(args, gpt_data, from_email, email_to, subject, has_attach):
    contact_resp = await bitrix.create_contact({
        "NAME":        gpt_data.get("nombre", ""),
        "LAST_NAME":   gpt_data.get("apellido", ""),
        "EMAIL":       [{"VALUE": from_email, "TYPE_ID": "EMAIL", "VALUE_TYPE": "WORK"}],
        "PHONE":       [{"VALUE": gpt_data.get("telefono", ""), "TYPE_ID": "PHONE", "VALUE_TYPE": "WORK"}],
        "TYPE_ID":     "CLIENT",
        "SOURCE_ID":   "EMAIL",
        "SECOND_NAME": " ",
        "UF_CRM_6FB0A682":   "122",
        "UF_CRM_FD1274F7":   "168",
        "UF_CRM_1593078333": "31516",
    })
    contact_id = str(contact_resp.get("result", ""))

    lead_resp = await bitrix.create_lead({
        "TITLE":          f"CGI - Respuesta automática: {args.get('categoria_correo', '')}",
        "STATUS_ID":      "NEW",
        "CONTACT_IDS":    [contact_id],
        "ASSIGNED_BY_ID": _ASSIGNED_BY_ID,
    })
    lead_id = str(lead_resp.get("result", ""))

    at_record = await airtable.create_record(
        config.AT_TBL_DATOS_EXTRAIDOS,
        _datos_extraidos_fields(args, gpt_data, lead_id, from_email, email_to, subject),
    )
    at_id = at_record.get("id", "")

    if has_attach:
        await bitrix.add_timeline_comment("lead", lead_id, "Archivos adjuntos: ")

    logger.info(f"[1.1] Lead (contacto nuevo) | lead_id={lead_id} | at={at_id}")
    return {
        "nombre": gpt_data.get("nombre", ""), "apellido": gpt_data.get("apellido", ""),
        "email": from_email, "dni": gpt_data.get("dni", ""),
        "n_modulo": gpt_data.get("n_modulo", ""), "n_contrato": gpt_data.get("n_contrato", ""),
        "telefono": gpt_data.get("telefono", ""), "lead_id": lead_id,
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
        "SOURCE_ID":  "EMAIL",
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
    item_id = item_resp.get("result", {}).get("item", {}).get("id", "")
    lead_id = f"169_{item_id}"

    at_record = await airtable.create_record(
        config.AT_TBL_DATOS_EXTRAIDOS,
        _datos_extraidos_fields(args, gpt_data, lead_id, from_email, email_to, subject),
    )
    at_id = at_record.get("id", "")

    logger.info(f"[1.1] Franquicia creada | item={item_id} | at={at_id}")
    return {
        "nombre": gpt_data.get("nombre", ""), "apellido": "",
        "email": from_email, "lead_id": lead_id,
        "centro": gpt_data.get("centro_operativo", ""),
        "datos_extraidos_id": at_id, "Cliente": True,
    }
