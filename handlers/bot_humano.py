"""
handlers/bot_humano.py — Escenario 1.5: Bot o Humano

Recibe (de clasificacion.py):
    message_id, thread_id, ticket_id, nombre, bot_humano,
    categoria_correo, tipo_correo, subject, row

Lógica:
  - Si bot_humano != "humano" → retorna sin acción
  - Si "humano":
      1. Obtiene email completo (para fromEmail)
      2. Busca contacto en Bitrix por fromEmail
      3. Envía correo de ticket al cliente (BCC al equipo)
      4. Actualiza Lead en Bitrix: STAGE_ID=UC_BZJ6XN, título, contacto opcional
      5. Añade comentario en timeline del lead
      6. Actualiza Clasificación: acciones_1 + humano_bot
"""
import logging
import config
from services import gmail, airtable, bitrix
from handlers import email_templates

logger = logging.getLogger("email-cgi")

_TICKET_BCC = ["iacgi@tutrastero.com", "sistemas@tutrastero.com"]


async def run(args: dict) -> dict:
    bot_humano = args.get("bot_humano", "")
    thread_id  = args.get("thread_id", "")
    message_id = args.get("message_id", "")
    ticket_id  = args.get("ticket_id", "")
    nombre     = args.get("nombre", "")
    categoria  = args.get("categoria_correo", "")
    subject    = args.get("subject", "")
    row        = args.get("row", "")   # ID registro Clasificación

    if bot_humano != "humano":
        logger.info(f"[1.5] bot_humano={bot_humano!r} — sin acción")
        return {"status": "ok", "bot_humano": bot_humano}

    if categoria == "doble":
        logger.info(f"[1.5] categoria=doble — gestionado por blueprint 1.5")
        return {"status": "ok", "bot_humano": bot_humano, "categoria": "doble"}

    # 1. Email completo
    email      = await gmail.get_email(message_id)
    from_email = email.get("fromEmail", "")
    email_subj = email.get("subject", "") or subject

    logger.info(f"[1.5] humano | from={from_email} | ticket_id={ticket_id}")

    # 2. Buscar contacto Bitrix
    contacts    = await bitrix.search_contacts_by_email(from_email)
    contact_id  = contacts[0]["ID"] if contacts else None
    assigned_by = (contacts[0].get("ASSIGNED_BY_ID") or "6358") if contacts else "6358"

    # 3. Enviar correo de ticket al cliente
    ticket_subject = f"Número de Ticket #{ticket_id} - {email_subj}"
    await gmail.send_email(
        to        = [from_email],
        subject   = ticket_subject,
        body      = email_templates.ticket_email(nombre, ticket_id),
        body_type = "html",
        bcc       = _TICKET_BCC,
        thread_id = thread_id,
    )
    logger.info(f"[1.5] Ticket enviado | subject={ticket_subject!r}")

    # 4. Actualizar item SPA 1034 (solo tickets CRM 1034, no franquicias CRM 169)
    _is_franquicia = str(ticket_id).startswith("169_")
    item_fields = {
        "stageId":      "DT1034_120:CLIENT",
        "assignedById": assigned_by,
        "title":        f"CGI - Requiere HUMANO: {categoria}",
    }
    if contact_id:
        item_fields["contactId"] = contact_id

    if ticket_id and not _is_franquicia:
        await bitrix.update_crm_item(1034, ticket_id, item_fields)
        logger.info(f"[1.5] Item 1034 actualizado | ticket_id={ticket_id} | contact_id={contact_id}")

        # 5. Comentario en timeline
        await bitrix.add_timeline_comment(
            "dynamic_1034", ticket_id,
            f"Comunicarse con el cliente. No se atendió al requerimiento.\n"
            f"El emisor del correo solicita la comunicación con un HUMANO para {categoria}",
        )
    elif _is_franquicia:
        logger.info(f"[1.5] Franquicia (CRM 169) — sin actualización CRM 1034 | ticket_id={ticket_id}")

    # 6. Actualizar Clasificación
    clasif_id = row
    if not clasif_id and thread_id:
        records = await airtable.search_records(
            config.AT_TBL_CLASIFICACION,
            formula=f'{{thread_id}}="{thread_id}"',
            max_records=1,
        )
        clasif_id = records[0]["id"] if records else ""

    if clasif_id:
        await airtable.update_record(
            config.AT_TBL_CLASIFICACION,
            clasif_id,
            {
                "fldXQvHFuiY9ebvYa": "Se deriva con gestor",
                "fldquQJeU5QJmNfBa": "humano",
            },
        )
        logger.info(f"[1.5] Clasificación actualizada | clasif_id={clasif_id}")

    return {"status": "ok", "bot_humano": "humano", "ticket_subject": ticket_subject, "ticket_id": ticket_id}
