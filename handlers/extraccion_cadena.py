"""
handlers/extraccion_cadena.py — Escenario 1.2: Extracción Datos - Cadena de correos

Se ejecuta cuando llega un correo de seguimiento en un hilo ya conocido.
Extrae el DNI actualizado y lo sincroniza con Airtable y Bitrix24.

Recibe:
    message_id — ID del mensaje en Gmail
    thread_id  — ID del hilo de Gmail

Pasos:
    1. Obtiene email completo
    2. GPT-4.1 extrae el DNI del cuerpo del correo
    3. Busca el registro existente en Airtable "Datos extraídos" por thread_id
    4. Upsert del campo dni
    5. Añade comentario en timeline de Bitrix24 si hay lead_id

Retorna:
    nombre, apellido, dni, n_modulo, n_contrato, tipo_contacto,
    telefono, datos_extraidos_id, centro
"""
import logging
from services import gmail, airtable, bitrix, openai_svc
import config

logger = logging.getLogger("email-cgi")


async def run(args: dict) -> dict:
    message_id = args["message_id"]
    thread_id  = args["thread_id"]

    # 1. Email completo
    email    = await gmail.get_email(message_id)
    body_txt = email.get("fullTextBody") or email.get("htmlBody") or ""

    logger.info(f"[1.2] message_id={message_id} | thread_id={thread_id}")

    # 2. Extraer DNI con GPT-4.1
    extracted = await openai_svc.extract_structured_data(
        text=body_txt,
        prompt=(
            "Actúa como experto en estructurar datos extraídos de correos con información "
            "no estructurada. Identifica el documento de identidad "
            "(DNI / NIF / CIF / NIE / Pasaporte) indicado en el correo. "
            "Estamos en España. Si el cliente no lo ha indicado, devuelve \"null\"."
        ),
        parameters=[{
            "name":        "dni",
            "type":        "string",
            "description": "Documento de identidad: DNI / NIF / CIF / NIE / Pasaporte",
            "isRequired":  False,
        }],
    )
    dni = extracted.get("dni") or "null"
    logger.info(f"[1.2] DNI extraído: {dni!r}")

    # 3. Buscar registro en Airtable "Datos extraídos" por thread_id
    records = await airtable.search_records(
        config.AT_TBL_DATOS_EXTRAIDOS,
        formula=f'{{thread_id}}="{thread_id}"',
        max_records=1,
    )
    record    = records[0] if records else None
    record_id = record["id"] if record else None
    existing  = record.get("fields", {}) if record else {}

    # 4. Upsert del campo dni
    updated = await airtable.upsert_record(
        config.AT_TBL_DATOS_EXTRAIDOS,
        record_id,
        {"dni": dni},
    )
    logger.info(f"[1.2] Airtable upsert | record_id={record_id or 'nuevo'}")

    # 5. Comentario en Bitrix24 si existe lead_id
    lead_id = existing.get("lead_id")
    if lead_id and dni and dni != "null":
        await bitrix.add_timeline_comment(
            entity_type="lead",
            entity_id=lead_id,
            comment=f"DNI CORREGIDO {dni}",
        )
        logger.info(f"[1.2] Timeline comment añadido | lead_id={lead_id}")

    fields = updated.get("fields", {})
    return {
        "nombre":             fields.get("nombre", ""),
        "apellido":           fields.get("apellido", ""),
        "dni":                fields.get("dni", ""),
        "n_modulo":           fields.get("n_modulo", ""),
        "n_contrato":         fields.get("n_contrato", ""),
        "tipo_contacto":      fields.get("tipo", ""),
        "telefono":           fields.get("telefono", ""),
        "datos_extraidos_id": updated.get("id", ""),
        "centro":             fields.get("centro", ""),
    }
