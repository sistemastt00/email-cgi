"""
handlers/correo_clasif.py — Escenario 1.0: Correo de Clasificación

Recibe:
    message_id       — ID del mensaje en Gmail
    row              — ID del registro en Airtable Clasificación (tblKSSUdMWhL1n2Sw)
    lead_id          — ID del lead en Bitrix24 (de extraccion_1er)
    categoria_correo — clasificación principal
    tipo_correo      — subtipo
    bot_humano       — "bot" | "humano"
    subject          — asunto del email original

Pasos:
    1. Obtiene email completo + adjuntos
    2. Calcula asunto-clasif y actualiza Airtable (campo fldKWZHMVfTwdxsbJ)
    3. Envía correo al equipo:
       - HTML con adjunto  / HTML sin adjunto
       - Plain con adjunto / Plain sin adjunto
"""
import logging
from services import gmail, airtable
import config

logger = logging.getLogger("email-cgi")


async def run(args: dict) -> dict:
    message_id = args["message_id"]
    categoria  = args.get("categoria_correo", "")
    tipo       = args.get("tipo_correo", "")
    bh         = args.get("bot_humano", "")
    row        = args.get("row", "")   # ID registro Clasificación

    # 1. Email completo + adjuntos
    email    = await gmail.get_email(message_id)
    adjuntos = await gmail.get_attachments(message_id)
    subject  = email.get("subject", "")
    html_body  = email.get("htmlBody", "") or ""
    plain_body = email.get("fullTextBody", "") or ""

    logger.info(f"[1.0] message_id={message_id} | subject={subject!r} | html={bool(html_body)} | adjuntos={len(adjuntos)}")

    # 2. asunto-clasif (sin espacios) → actualizar Airtable
    asunto_clasif = (
        f"ClasificaciónCGI-({categoria}-{tipo}-{bh})-{subject}"
    ).replace(" ", "")

    if row:
        await airtable.update_record(
            config.AT_TBL_CLASIFICACION,
            row,
            {"fldKWZHMVfTwdxsbJ": asunto_clasif},
        )
        logger.info(f"[1.0] Airtable actualizado | row={row} | asunto-clasif={asunto_clasif!r}")

    # 3. Enviar correo al equipo
    subject_email = f"Clasificación CGI - ({categoria} - {tipo} - {bh}) - {subject}"
    use_html      = bool(html_body)
    body_content  = html_body if use_html else plain_body
    body_type     = "html" if use_html else "plain"
    attachments   = adjuntos if adjuntos else None

    sent = await gmail.send_email(
        to          = config.CLASIFICACION_TO,
        subject     = subject_email,
        body        = body_content,
        body_type   = body_type,
        attachments = attachments,
    )

    logger.info(f"[1.0] Correo enviado | thread_id={sent['threadId']} | adjuntos={bool(attachments)}")
    return {"thread_id_clasif": sent["threadId"]}
