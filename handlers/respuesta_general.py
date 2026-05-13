"""
handlers/respuesta_general.py — Escenario 1.4: Respuestas Área General

Recibe (de clasificacion.py):
    message_id, thread_id, lead_id, nombre, apellido,
    categoria_correo, tipo_correo, bot_humano, row

Lógica:
  1. Obtiene email completo (fromEmail, subject)
  2. Si la categoría tiene CTA conocido → envía email al cliente (BCC al equipo)
  3. Actualiza Lead en Bitrix: TITLE="CGI - Respuesta EXITOSA: {categoria}"
  4. Añade comentario en timeline del lead
  5. Actualiza Clasificación: acciones_2="Enlace a web", humano_bot="bot"
     (solo si categoria no contiene "Cancelar")
"""
import logging
import config
from services import gmail, airtable, bitrix

logger = logging.getLogger("email-cgi")

_BCC = ["iacgi@tutrastero.com", "sistemas@tutrastero.com"]

# Categorías con CTA y URL de destino
_CTA_MAP = {
    "Agendar Visita":         ("Agendar mi visita ahora",        "https://tutrastero.com/es/agendar-visita/"),
    "Reservar Tu Trastero":   ("Reservar y asegurar mi trastero", "https://administracion.tutrastero.com/form/contratacion-online"),
    "Notificar Incidencia":   ("Reportar incidencia",             "https://tutrastero.com/es/servicios-online/gestion-incidencias/"),
    "Hacer Valoración":       ("Indicar el valor de mis bienes",  "https://tutrastero.com/es/servicios-online/declaracion-de-valor/"),
    "Hacer Inventario":       ("Gestionar mi inventario",         "https://tutrastero.com/es/servicios-online/"),
    "Autorizar a Terceros":   ("Autorizar acceso",                "https://tutrastero.com/es/servicios-online/"),
    "Actualizar Tus Datos":   ("Actualizar mis datos",            "https://tutrastero.com/es/servicios-online/"),
}


def _cta_html(nombre: str, categoria: str, cta_text: str, cta_url: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;font-size:14px;color:#333;max-width:600px;margin:auto">
  <p>Estimado/a {nombre or "cliente"},</p>
  <p>Hemos recibido tu solicitud relacionada con <strong>{categoria}</strong>.</p>
  <p>Para gestionarlo de forma rápida y sencilla, puedes acceder directamente
     desde el siguiente enlace:</p>
  <p style="text-align:center;margin:24px 0">
    <a href="{cta_url}"
       style="background:#1a73e8;color:#fff;padding:12px 24px;border-radius:4px;
              text-decoration:none;font-weight:bold">
      {cta_text}
    </a>
  </p>
  <p>Si tienes alguna duda adicional, no dudes en contactarnos.</p>
  <p>Un saludo,<br>Tu Trastero</p>
  <p style="color:#999;font-size:11px">cgi@tutrastero.com</p>
</body>
</html>"""


async def run(args: dict) -> dict:
    thread_id  = args.get("thread_id", "")
    message_id = args.get("message_id", "")
    lead_id    = args.get("lead_id", "")
    nombre     = args.get("nombre", "")
    categoria  = args.get("categoria_correo", "")
    row        = args.get("row", "")   # ID registro Clasificación

    # 1. Email completo
    email      = await gmail.get_email(message_id)
    from_email = email.get("fromEmail", "")
    subj       = email.get("subject", "")

    logger.info(f"[1.4] from={from_email} | categoria={categoria!r} | lead_id={lead_id}")

    # 2. Enviar email con CTA si la categoría lo tiene
    cta = _CTA_MAP.get(categoria)
    if cta:
        cta_text, cta_url = cta
        await gmail.send_email(
            to        = [from_email],
            subject   = subj,
            body      = _cta_html(nombre, categoria, cta_text, cta_url),
            body_type = "html",
            bcc       = _BCC,
        )
        logger.info(f"[1.4] Email CTA enviado | to={from_email} | cta={cta_text!r}")

    # 3. Actualizar Lead en Bitrix
    if lead_id:
        await bitrix.update_lead(lead_id, {
            "ASSIGNED_BY_ID": "6358",
            "TITLE":          f"CGI - Respuesta EXITOSA: {categoria}",
        })

        # 4. Comentario en timeline
        await bitrix.add_timeline_comment(
            "lead", lead_id,
            f"Respuesta automática EXITOSA. A la solicitud de {categoria} se generó "
            f"la siguiente RESPUESTA AUTOMÁTICA: Enlace directo {categoria} de la web Tu Trastero.",
        )
        logger.info(f"[1.4] Bitrix actualizado | lead_id={lead_id}")

    # 5. Actualizar Clasificación (solo si no es categoría "Cancelar")
    if "cancelar" not in categoria.lower():
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
                    "fldgj898WCeUM3QqV": "Enlace a web",
                    "fldquQJeU5QJmNfBa": "bot",
                },
            )
            logger.info(f"[1.4] Clasificación actualizada | clasif_id={clasif_id}")

    return {"status": "ok", "categoria": categoria}
