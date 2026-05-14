"""
handlers/respuesta_general.py — Escenario 1.4: Respuestas Área General

Categorías area_general: Airtable update → Bitrix update → email CTA al cliente
Rutas especiales: Presupuesto (título distinto en Bitrix), Cambio de trastero (ticket + STAGE_ID)
"""
import logging
import config
from services import gmail, airtable, bitrix
from handlers import email_templates

logger = logging.getLogger("email-cgi")

_BCC = ["iacgi@tutrastero.com", "sistemas@tutrastero.com"]

_EMAIL_BUILDERS = {
    "Agendar Visita":       email_templates.agendar_visita_email,
    "Reservar Tu Trastero": email_templates.reservar_trastero_email,
    "Notificar Incidencia": email_templates.notificar_incidencia_email,
    "Hacer Valoración":     email_templates.hacer_valoracion_email,
    "Hacer Inventario":     email_templates.hacer_inventario_email,
    "Autorizar a Terceros": email_templates.autorizar_terceros_email,
    "Actualizar Tus Datos": email_templates.actualizar_datos_email,
    "Presupuesto":          email_templates.presupuesto_email,
}


async def run(args: dict) -> dict:
    thread_id  = args.get("thread_id", "")
    message_id = args.get("message_id", "")
    lead_id    = args.get("lead_id", "")
    nombre     = args.get("nombre", "")
    categoria  = args.get("categoria_correo", "")
    row        = args.get("row", "")

    email      = await gmail.get_email(message_id)
    from_email = email.get("fromEmail", "")
    subj       = email.get("subject", "")

    logger.info(f"[1.4] from={from_email} | categoria={categoria!r} | lead_id={lead_id}")

    clasif_id = row or await _get_clasif_id(thread_id)

    # ── Cambio de trastero ────────────────────────────────────────────────────
    if categoria in {"Cambio de trastero", "cambio_trastero"}:
        contacts   = await bitrix.search_contacts_by_email(from_email)
        contact_id = contacts[0]["ID"] if contacts else None

        ticket_subj = f"Solicitud Cambio de Trastero - Número de Ticket #{lead_id}"
        await gmail.send_email(
            to=[from_email], subject=ticket_subj,
            body=email_templates.cambio_trastero_email(nombre, lead_id),
            body_type="html", bcc=_BCC,
        )

        if lead_id:
            lead_fields = {
                "STAGE_ID":       "UC_M25V3A",
                "ASSIGNED_BY_ID": "6358",
                "TITLE":          "CGI - Cambio de trastero",
            }
            if contact_id:
                lead_fields["CONTACT_ID"] = contact_id
            await bitrix.update_lead(lead_id, lead_fields)

        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldXQvHFuiY9ebvYa": "Se deriva con gestor",
                "fldquQJeU5QJmNfBa": "humano",
            })

        logger.info(f"[1.4] Cambio de trastero ticket enviado | lead_id={lead_id}")
        return {"status": "ok", "categoria": categoria, "flujo": "cambio_trastero"}

    # ── Flujo área general (CTA) ──────────────────────────────────────────────

    # 1. Airtable: acciones_2 = "Enlace a web", humano_bot = "bot"
    if clasif_id:
        await airtable.update_record(
            config.AT_TBL_CLASIFICACION,
            clasif_id,
            {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            },
        )
        logger.info(f"[1.4] Airtable actualizado | clasif_id={clasif_id}")

    # 2. Email builder para esta categoría
    builder = _EMAIL_BUILDERS.get(categoria)
    if not builder:
        logger.info(f"[1.4] Sin template definido para categoria={categoria!r}")
        return {"status": "ok", "categoria": categoria, "flujo": "sin_cta"}

    # 3. Bitrix: TITLE y timeline (Presupuesto tiene texto propio)
    if lead_id:
        if categoria == "Presupuesto":
            bitrix_title = "CGI - Solicitud de Presupuesto"
            timeline_msg = "Se envió enlace a web al CLIENTE para que solicite presupuesto."
        else:
            bitrix_title = f"CGI - Respuesta EXITOSA: {categoria}"
            timeline_msg = (
                f"Respuesta automática EXITOSA. A la solicitud de {categoria} se generó "
                f"la siguiente RESPUESTA AUTOMÁTICA: Enlace directo {categoria} de la web Tu Trastero."
            )
        await bitrix.update_lead(lead_id, {
            "ASSIGNED_BY_ID": "6358",
            "TITLE":          bitrix_title,
        })
        await bitrix.add_timeline_comment("lead", lead_id, timeline_msg)
        logger.info(f"[1.4] Bitrix actualizado | lead_id={lead_id}")

    # 4. Email CTA al cliente
    await gmail.send_email(
        to=[from_email],
        subject=subj,
        body=builder(nombre),
        body_type="html",
        bcc=_BCC,
    )
    logger.info(f"[1.4] Email CTA enviado | to={from_email} | categoria={categoria!r}")

    return {"status": "ok", "categoria": categoria, "flujo": "cta"}


async def _get_clasif_id(thread_id: str) -> str:
    if not thread_id:
        return ""
    records = await airtable.search_records(
        config.AT_TBL_CLASIFICACION,
        formula=f'{{thread_id}}="{thread_id}"',
        max_records=1,
    )
    return records[0]["id"] if records else ""
