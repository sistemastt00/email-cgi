"""
handlers/bot_humano.py — Escenario 1.5: Bot o Humano

Recibe (de clasificacion.py):
    message_id, thread_id, lead_id, nombre, bot_humano,
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

logger = logging.getLogger("email-cgi")

_TICKET_BCC = ["iacgi@tutrastero.com", "sistemas@tutrastero.com"]


def _ticket_html(nombre: str, lead_id: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;font-size:14px;color:#333">
  <p>Estimado/a {nombre or "cliente"},</p>
  <p>Hemos recibido su correo y hemos generado un ticket de seguimiento con el número
     <strong>#{lead_id}</strong>.</p>
  <p>Un miembro de nuestro equipo revisará su solicitud y se pondrá en contacto con
     usted a la brevedad posible.</p>
  <p>Gracias por ponerse en contacto con Tu Trastero.</p>
  <br>
  <p style="color:#666;font-size:12px">
    Tu Trastero &mdash; cgi@tutrastero.com
  </p>
</body>
</html>"""


async def run(args: dict) -> dict:
    bot_humano = args.get("bot_humano", "")
    thread_id  = args.get("thread_id", "")
    message_id = args.get("message_id", "")
    lead_id    = args.get("lead_id", "")
    nombre     = args.get("nombre", "")
    categoria  = args.get("categoria_correo", "")
    subject    = args.get("subject", "")
    row        = args.get("row", "")   # ID registro Clasificación

    if bot_humano != "humano":
        logger.info(f"[1.5] bot_humano={bot_humano!r} — sin acción")
        return {"status": "ok", "bot_humano": bot_humano}

    # 1. Email completo
    email      = await gmail.get_email(message_id)
    from_email = email.get("fromEmail", "")
    email_subj = email.get("subject", "") or subject

    logger.info(f"[1.5] humano | from={from_email} | lead_id={lead_id}")

    # 2. Buscar contacto Bitrix
    contacts   = await bitrix.search_contacts_by_email(from_email)
    contact_id = contacts[0]["ID"] if contacts else None

    # 3. Enviar correo de ticket al cliente
    ticket_subject = f"Número de Ticket #{lead_id} - {email_subj}"
    await gmail.send_email(
        to        = [from_email],
        subject   = ticket_subject,
        body      = _ticket_html(nombre, lead_id),
        body_type = "html",
        bcc       = _TICKET_BCC,
    )
    logger.info(f"[1.5] Ticket enviado | subject={ticket_subject!r}")

    # 4. Actualizar Lead en Bitrix
    lead_fields = {
        "STAGE_ID":       "UC_BZJ6XN",
        "ASSIGNED_BY_ID": "6358",
        "TITLE":          f"CGI - Requiere HUMANO: {categoria}",
    }
    if contact_id:
        lead_fields["CONTACT_ID"] = contact_id

    if lead_id:
        await bitrix.update_lead(lead_id, lead_fields)
        logger.info(f"[1.5] Lead actualizado | lead_id={lead_id} | contact_id={contact_id}")

        # 5. Comentario en timeline
        await bitrix.add_timeline_comment(
            "lead", lead_id,
            f"Comunicarse con el cliente. No se atendió al requerimiento. "
            f"El emisor del correo solicita la comunicación con un HUMANO para {categoria}",
        )

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

    return {"status": "ok", "bot_humano": "humano", "ticket_subject": ticket_subject}
