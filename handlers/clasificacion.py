"""
handlers/clasificacion.py — Escenario 1: Pipeline principal

Ciclo completo por cada email nuevo:
  1. Filtro blacklist → marca como leído y sale
  2. Busca registro existente en Datos extraídos (duplicado)
  3. GPT: bot_humano  (BC_Ejemplos Bot_Humano)
  4. GPT: categoria + tipo (solo si no hay duplicado exacto)
  5. Crea registro en Clasificación
  6. Marca como leído
  7. Secuencia principal (hilo nuevo): 1.1 → 1.0 → 1.5 condicional → routing
  8. Secuencia cadena (hilo existente): 1.5 con datos existentes → 1.2 condicional
"""
import asyncio
import collections
import datetime
import json
import logging
from pathlib import Path
import config
from services import gmail, airtable, bitrix, openai_svc, telegram
from handlers import correo_clasif, extraccion_1er, extraccion_cadena, bot_humano, respuesta_general, email_templates

_lock = asyncio.Lock()
summaries: collections.deque = collections.deque(maxlen=100)

_PERSIST_DIR  = Path(__file__).parent.parent / "data"
_PERSIST_FILE = _PERSIST_DIR / "summaries.json"


def _load_summaries() -> None:
    if not _PERSIST_FILE.exists():
        return
    try:
        data = json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
        for entry in data:
            summaries.append(entry)
    except Exception as exc:
        logger.warning(f"[persist] No se pudo cargar summaries: {exc}")


def _save_summaries() -> None:
    try:
        _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        _PERSIST_FILE.write_text(
            json.dumps(list(summaries), ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning(f"[persist] No se pudo guardar summaries: {exc}")

logger = logging.getLogger("email-cgi")

_flow_logs: list = []  # log capture for the current email being processed

class _FlowCaptureHandler(logging.Handler):
    def emit(self, record):
        _flow_logs.append({
            "time":    datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
            "level":   record.levelname,
            "message": self.format(record),
        })

_capture_handler = _FlowCaptureHandler()
_capture_handler.setFormatter(logging.Formatter("%(message)s"))

_BCC = ["iacgi@tutrastero.com", "sistemas@tutrastero.com"]

_load_summaries()

_AREA_GENERAL_CATS = {
    "agendar_visita", "reservar", "presupuesto", "autorizar_terceros",
    "incidencia", "actualizar_datos", "inventario", "valoración",
    "cambio_titular_modulo",
}

_AREA_CLIENTE_CATS = {
    "mis_documentos", "documentos_generales", "claves_acceso",
    "pagar_facturas", "ver_facturas", "renueve_promocion", "aviso_salida",
}

_OTROS_SERVICIOS_CATS = {
    "mudanza", "materiales_embalaje", "otros", "resena_google",
    "moroso", "desestima_oferta", "foto_salida",
    "modificar_visita", "cancelar_visita",
}


def _is_blacklisted(from_email: str) -> bool:
    addr = from_email.lower()
    return any(pattern in addr for pattern in config.EMAIL_BLACKLIST_CONTAINS)


async def _process_email(msg_stub: dict):
    _flow_logs.clear()
    logger.addHandler(_capture_handler)
    try:
        await _process_email_inner(msg_stub)
    finally:
        logger.removeHandler(_capture_handler)


async def _process_email_inner(msg_stub: dict):
    message_id = msg_stub["id"]
    thread_id  = msg_stub["threadId"]

    email      = await gmail.get_email(message_id)
    from_email = email.get("fromEmail", "")
    subject    = email.get("subject", "")
    body       = email.get("fullTextBody") or email.get("htmlBody") or subject

    # 1. Blacklist
    if _is_blacklisted(from_email):
        logger.info(f"[1] Ignorado (blacklist) | from={from_email}")
        await gmail.mark_processed(message_id)
        summaries.appendleft({
            "time":       datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
            "from_email": from_email,
            "from_name":  email.get("fromName", ""),
            "subject":    subject,
            "hilo":       "nuevo",
            "categoria":  "—",
            "tipo":       "—",
            "bot_humano": "—",
            "ticket_id":  "—",
            "nombre":     "—",
            "resultado":  "Ignorado (blacklist)",
            "error":      False,
            "logs":       list(_flow_logs),
        })
        _save_summaries()
        return

    # 1b. Reenvío especial: soporte@trasterone.com → Jaison (sale del pipeline)
    if from_email.lower() == "soporte@trasterone.com":
        fwd_body      = email.get("htmlBody") or email.get("fullTextBody") or subject
        fwd_body_type = "html" if email.get("htmlBody") else "plain"
        header = (
            f"<p style='font-family:arial;font-size:13px;color:#555'>"
            f"<b>De:</b> {email.get('fromName','')} &lt;{from_email}&gt;<br>"
            f"<b>Asunto:</b> {subject}"
            f"</p><hr>"
        ) if fwd_body_type == "html" else f"De: {from_email}\nAsunto: {subject}\n\n"
        await gmail.send_email(
            to=["jaison.veliz@tutrastero.com"],
            subject=f"Fwd: [{from_email}] {subject}",
            body=header + fwd_body,
            body_type=fwd_body_type,
        )
        await gmail.mark_processed(message_id)
        logger.info(f"[1] Reenviado a Jaison (trasterone) | from={from_email}")
        summaries.appendleft({
            "time":       datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
            "from_email": from_email,
            "from_name":  email.get("fromName", ""),
            "subject":    subject,
            "hilo":       "nuevo",
            "categoria":  "—",
            "tipo":       "—",
            "bot_humano": "—",
            "ticket_id":  "—",
            "nombre":     "—",
            "resultado":  "Reenviado a Jaison (trasterone)",
            "error":      False,
            "logs":       list(_flow_logs),
        })
        _save_summaries()
        return

    # 1c. Reenvío especial: @idealista.com con mensaje de nuevos mensajes → Jaison + Fanny
    _is_idealista = "@idealista.com" in from_email.lower()
    if _is_idealista:
        fwd_body = email.get("htmlBody") or email.get("fullTextBody") or subject
        fwd_body_type = "html" if email.get("htmlBody") else "plain"
        header = (
            f"<p style='font-family:arial;font-size:13px;color:#555'>"
            f"<b>De:</b> {email.get('fromName','')} &lt;{from_email}&gt;<br>"
            f"<b>Asunto:</b> {subject}"
            f"</p><hr>"
        ) if fwd_body_type == "html" else f"De: {from_email}\nAsunto: {subject}\n\n"
        _IDEALISTA_MSG = "tienes nuevos mensajes que esperan tu respuesta"
        if _IDEALISTA_MSG in (subject + " " + body).lower():
            await gmail.send_email(
                to=["jaison.veliz@tutrastero.com", "fanny.trejo@tutrastero.com"],
                subject=f"Fwd: [{from_email}] {subject}",
                body=header + fwd_body,
                body_type=fwd_body_type,
            )
            logger.info(f"[1] Reenviado a Jaison+Fanny (idealista nuevos mensajes) | from={from_email}")
        else:
            await gmail.send_email(
                to=["carlos.gutierrez@tutrastero.com"],
                subject=f"Fwd: [{from_email}] {subject}",
                body=header + fwd_body,
                body_type=fwd_body_type,
            )
            logger.info(f"[1] Reenviado a Carlos (idealista) | from={from_email}")

    logger.info(f"[1] Procesando | from={from_email} | subject={subject!r}")

    # 2. Buscar registro existente en Datos extraídos
    existing        = await airtable.search_records(
        config.AT_TBL_DATOS_EXTRAIDOS,
        formula=f'{{thread_id}}="{thread_id}"',
        max_records=2,
        fields=["thread_id", "nombre", "lead_id", "categoria_api", "tipo"],
    )
    is_new_thread   = len(existing) == 0
    existing_fields = existing[0]["fields"] if existing else {}

    # 3 & 4. Clasificación: fija para @idealista.com, GPT para el resto
    if _is_idealista:
        examples_bh     = []
        examples_clasif = []
        examples_tipo   = []
        definitions     = []
        bot_humano_result = "humano"
        categoria         = "Otros"
        categoria_api     = "otros"
        tipo              = "informacion"
        logger.info(f"[1] Idealista → clasificación fija: otros / informacion / humano")
    else:
        # GPT: bot_humano
        examples_bh = [
            r["fields"] for r in await airtable.search_records(
                config.AT_TBL_EJEMPLOS_BOT_HUMANO, formula="", max_records=50,
                fields=["Fragmento de Correo", "Bot o Humano"],
            )
        ]
        bot_humano_result = await openai_svc.classify_bot_humano(
            email_body=body,
            examples=examples_bh,
        )
        logger.info(f"[1] bot_humano={bot_humano_result}")

        # GPT: categoria + tipo
        definitions = [
            r["fields"] for r in await airtable.search_records(
                config.AT_TBL_DEFINICIONES, formula="", max_records=50,
                fields=["Categoria", "Descripcion", "Enlace", "categoria_api"],
            )
        ]
        examples_clasif = [
            r["fields"] for r in await airtable.search_records(
                config.AT_TBL_EJEMPLOS_CLASIF, formula="", max_records=50,
                fields=["Ejemplos", "Categoria Asignada"],
            )
        ]
        cat_result = await openai_svc.classify_categoria(
            subject=subject, email_body=body,
            definitions=definitions, examples_clasif=examples_clasif,
        )
        categoria     = cat_result.get("categoria", "")
        categoria_api = cat_result.get("categoria_api", "")
        logger.info(f"[1] categoria={categoria} | categoria_api={categoria_api}")

        examples_tipo = [
            r["fields"] for r in await airtable.search_records(
                config.AT_TBL_EJEMPLOS_TIPO, formula="", max_records=50,
                fields=["Fragmento de Correo", "Tipo de correo"],
            )
        ]
        tipo = await openai_svc.classify_tipo(
            subject=subject, email_body=body, from_email=from_email,
            categoria=categoria, examples_clasif=examples_clasif, examples_tipo=examples_tipo,
        )
        logger.info(f"[1] tipo={tipo}")

    # 5. Crear registro en Clasificación
    clasif_record = await airtable.create_record(
        config.AT_TBL_CLASIFICACION,
        fields={
            "fldX2vzDBKwrXmiGQ": categoria,
            "fldjXk8GniT6hO6oa": tipo,
            "fldpuawV9XMHjYpSp": thread_id,
            "fldquQJeU5QJmNfBa": bot_humano_result,
            "flduN9b2wr5cVZrhj": subject,
        },
    )
    clasif_record_id = clasif_record.get("id", "")
    logger.info(f"[1] Clasificación creada | record={clasif_record_id}")

    # 6. Marcar como leído
    await gmail.mark_processed(message_id)

    args_base = {
        "message_id":           message_id,
        "thread_id":            thread_id,
        "categoria_correo":     categoria,
        "categoria_correo_api": categoria_api,
        "tipo_correo":          tipo,
        "bot_humano":           bot_humano_result,
        "row":                  clasif_record_id,
        "subject":              subject,
    }

    # 7. Secuencia principal: solo si es hilo nuevo
    extrac_result = {}
    is_req = False
    cliente = False
    if is_new_thread:
        # 1.1 primero (devuelve ticket_id, nombre, Cliente)
        try:
            extrac_result = await extraccion_1er.run(args_base)
            logger.info(f"[1] 1.1 ok | {extrac_result}")
        except Exception as exc:
            logger.error(f"[1] Error en 1.1: {exc}", exc_info=True)
            await telegram.send_alert(
                f"⚠️ *Email CGI* — error en `extraccion_1er`\n"
                f"📧 `{from_email}`\n"
                f"❌ `{type(exc).__name__}: {str(exc)[:200]}`"
            )

        ticket_id = extrac_result.get("ticket_id", "")
        nombre    = extrac_result.get("nombre", "")
        cliente   = extrac_result.get("Cliente", False)

        # 1.0 con ticket_id de 1.1
        try:
            r10 = await correo_clasif.run({**args_base, "ticket_id": ticket_id})
            logger.info(f"[1] 1.0 ok | {r10}")
        except Exception as exc:
            logger.error(f"[1] Error en 1.0: {exc}", exc_info=True)

        # 1.5 si (tipo==accion AND categoria!=Franquicia) OR cliente==True
        is_req = tipo == "accion" and "franquicia" not in (categoria_api or categoria).lower()
        if is_req or cliente:
            try:
                r15 = await bot_humano.run({
                    **args_base,
                    "ticket_id": ticket_id,
                    "nombre":    nombre,
                })
                logger.info(f"[1] 1.5 ok | {r15}")
            except Exception as exc:
                logger.error(f"[1] Error en 1.5: {exc}", exc_info=True)

        # Routing de área: solo si bot y pasa el mismo gate que 1.5
        if bot_humano_result == "bot" and (is_req or cliente):
            if categoria in _AREA_GENERAL_CATS or categoria_api in _AREA_GENERAL_CATS:
                try:
                    r14 = await respuesta_general.run({
                        **args_base,
                        "ticket_id": ticket_id,
                        "nombre":    nombre,
                        "apellido":  extrac_result.get("apellido", ""),
                        "telefono":  extrac_result.get("telefono", ""),
                    })
                    logger.info(f"[1] 1.4 ok | {r14}")
                except Exception as exc:
                    logger.error(f"[1] Error en 1.4: {exc}", exc_info=True)

            elif categoria in _AREA_CLIENTE_CATS or categoria_api in _AREA_CLIENTE_CATS:
                try:
                    await _send_area_cliente_email(
                        message_id=message_id, nombre=nombre, ticket_id=ticket_id,
                        clasif_id=clasif_record_id, categoria=categoria,
                        thread_id=thread_id,
                    )
                    logger.info(f"[1] area_cliente email enviado | categoria={categoria}")
                except Exception as exc:
                    logger.error(f"[1] Error en area_cliente email: {exc}", exc_info=True)

        # otros_servicios: mismo gate que area_general/area_cliente
        if bot_humano_result == "bot" and (is_req or cliente) and (
            categoria in _OTROS_SERVICIOS_CATS or categoria_api in _OTROS_SERVICIOS_CATS
        ):
            try:
                await _send_otros_servicios_email(
                    categoria=categoria, categoria_api=categoria_api,
                    from_email=from_email, subject=subject,
                    nombre=nombre, ticket_id=ticket_id,
                    clasif_id=clasif_record_id,
                    apellido=extrac_result.get("apellido", ""),
                    telefono=extrac_result.get("telefono", ""),
                    thread_id=thread_id,
                )
                logger.info(f"[1] otros_servicios ok | categoria={categoria}")
            except Exception as exc:
                logger.error(f"[1] Error en otros_servicios: {exc}", exc_info=True)

    # 8. Secuencia cadena: si hay registro existente en Datos extraídos
    if existing:
        ex_nombre     = existing_fields.get("nombre", "")
        ex_ticket_id  = existing_fields.get("lead_id", "")  # Airtable field still named lead_id
        ex_categoria  = existing_fields.get("categoria_api", "")
        ex_tipo       = existing_fields.get("tipo", "")

        # 1.5 con datos del registro existente (módulo 89)
        try:
            r89 = await bot_humano.run({
                "message_id":       message_id,
                "thread_id":        thread_id,
                "nombre":           ex_nombre,
                "ticket_id":        ex_ticket_id,
                "categoria_correo": ex_categoria,
                "bot_humano":       bot_humano_result,
                "subject":          subject,
                "row":              clasif_record_id,
            })
            logger.info(f"[1] 1.5 (cadena) ok | {r89}")
        except Exception as exc:
            logger.error(f"[1] Error en 1.5 (cadena): {exc}", exc_info=True)

        # 1.2 si bot_humano != "bot" AND tipo_existente == "accion" (módulo 90)
        if bot_humano_result != "bot" and ex_tipo == "accion":
            try:
                r90 = await extraccion_cadena.run({
                    "message_id":           message_id,
                    "thread_id":            thread_id,
                    "categoria_correo":     ex_categoria,
                    "categoria_correo_api": ex_categoria,
                    "tipo_correo":          ex_tipo,
                    "bot_humano":           bot_humano_result,
                })
                logger.info(f"[1] 1.2 ok | {r90}")
            except Exception as exc:
                logger.error(f"[1] Error en 1.2: {exc}", exc_info=True)

    # ── Summary ──────────────────────────────────────────────────────────────
    _nombre     = extrac_result.get("nombre", "") if is_new_thread else existing_fields.get("nombre", "")
    _ticket_id  = extrac_result.get("ticket_id", "") if is_new_thread else existing_fields.get("lead_id", "")

    _sent_to_client = bot_humano_result == "bot" and (is_req or cliente)
    if bot_humano_result == "humano":
        resultado = "Ticket enviado al cliente + lead → HUMANO"
    elif is_new_thread and _sent_to_client:
        resultado = "Respuesta automática CTA enviada"
    elif not is_new_thread:
        resultado = "Cadena: clasificado + 1.5/1.2"
    else:
        resultado = "Clasificado + correo clasificación enviado"

    summary_entry = {
        "time":            datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
        "from_email":      from_email,
        "from_name":       email.get("fromName", ""),
        "subject":         subject,
        "hilo":            "nuevo" if is_new_thread else "cadena",
        "categoria":       categoria,
        "tipo":            tipo,
        "bot_humano":      bot_humano_result,
        "ticket_id":       _ticket_id,
        "nombre":          _nombre,
        "resultado":       resultado,
        "error":           False,
        "logs":            list(_flow_logs),
        "eval_clasif":           "—",
        "razon_eval_clasif":     "—",
        "eval_tipo":             "—",
        "razon_eval_tipo":       "—",
        "eval_bot_humano":       "—",
        "razon_eval_bot_humano": "—",
        "efectividad":           "—",
    }
    summaries.appendleft(summary_entry)
    _save_summaries()

    # ── Evaluación pipeline (background) ─────────────────────────────────────
    plantilla_enviada = _get_plantilla_enviada(categoria, bot_humano_result, is_req, cliente)
    asyncio.create_task(_evaluar_pipeline(
        clasif_id        = clasif_record_id,
        email_body       = body,
        subject          = subject,
        tipo             = tipo,
        bot_humano       = bot_humano_result,
        categoria        = categoria,
        plantilla_enviada= plantilla_enviada,
        is_req           = is_req,
        examples_tipo    = examples_tipo,
        examples_bh      = examples_bh,
        definitions      = definitions,
        examples_clasif  = examples_clasif,
        summary_entry    = summary_entry,
    ))


async def _send_area_cliente_email(
    message_id: str, nombre: str, ticket_id: str, clasif_id: str, categoria: str,
    thread_id: str = "",
):
    email      = await gmail.get_email(message_id)
    from_email = email.get("fromEmail", "")
    subj       = email.get("subject", "")

    if categoria == "aviso_salida":
        body         = email_templates.aviso_salida_sofia_email(nombre, from_email)
        timeline_msg = (
            f"Respuesta automática EXITOSA.\n"
            f"A la solicitud de {categoria} se derivó al cliente al chat Sofía."
        )
    else:
        body         = email_templates.area_cliente_email(nombre)
        timeline_msg = (
            f"Respuesta automática EXITOSA.\n"
            f"A la solicitud de {categoria} se generó la siguiente RESPUESTA AUTOMÁTICA: "
            f"Enlace a {categoria} de la web Tu Trastero."
        )

    await gmail.send_email(
        to=[from_email],
        subject=subj,
        body=body,
        body_type="html",
        bcc=_BCC,
        thread_id=thread_id,
    )

    if ticket_id:
        await bitrix.update_crm_item(1034, ticket_id, {
            "assignedById": "6358",
            "title":        f"CGI - Respuesta EXITOSA: {categoria}",
            "stageId":      "DT1034_120:SUCCESS",
        })
        await bitrix.add_timeline_comment("dynamic_1034", ticket_id, timeline_msg)

    if clasif_id:
        await airtable.update_record(
            config.AT_TBL_CLASIFICACION,
            clasif_id,
            {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            },
        )


async def _send_otros_servicios_email(
    categoria: str, categoria_api: str, from_email: str, subject: str,
    nombre: str, ticket_id: str, clasif_id: str,
    apellido: str = "", telefono: str = "", thread_id: str = "",
):
    cat  = categoria.lower()
    capi = categoria_api.lower()

    if "mudanza" in cat or capi == "mudanza":
        await gmail.send_email(
            to=[from_email], subject=subject,
            body=email_templates.mudanza_sofia_email(nombre, from_email),
            body_type="html", bcc=_BCC, thread_id=thread_id,
        )
        if ticket_id:
            await bitrix.update_crm_item(1034, ticket_id, {
                "assignedById": "6358",
                "title":        "CGI - Respuesta EXITOSA: Mudanza",
                "stageId":      "DT1034_120:SUCCESS",
            })
            await bitrix.add_timeline_comment(
                "dynamic_1034", ticket_id,
                f"Respuesta automática EXITOSA.\n"
                f"A la solicitud de {categoria} se derivó al cliente al chat Sofía.",
            )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            })

    elif "materiales" in cat or capi == "tu_caja":
        await gmail.send_email(
            to=[from_email], subject=subject,
            body=email_templates.materiales_sofia_email(nombre, from_email),
            body_type="html", bcc=_BCC, thread_id=thread_id,
        )
        if ticket_id:
            await bitrix.update_crm_item(1034, ticket_id, {
                "assignedById": "6358",
                "title":        "CGI - Respuesta EXITOSA: Tu Caja",
                "stageId":      "DT1034_120:SUCCESS",
            })
            await bitrix.add_timeline_comment(
                "dynamic_1034", ticket_id,
                f"CGI - Respuesta EXITOSA: Tu Caja.\n"
                f"A la solicitud de {categoria} se derivó al cliente al chat Sofía.",
            )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            })

    elif cat == "otros" or capi == "otros":
        await gmail.send_email(
            to=[from_email], subject=subject,
            body=email_templates.otros_sofia_email(nombre, from_email),
            body_type="html", bcc=_BCC, thread_id=thread_id,
        )
        if ticket_id:
            await bitrix.update_crm_item(1034, ticket_id, {
                "assignedById": "6358",
                "title":        "CGI - Respuesta EXITOSA: Otros",
                "stageId":      "DT1034_120:SUCCESS",
            })
            await bitrix.add_timeline_comment(
                "dynamic_1034", ticket_id,
                f"Respuesta automática EXITOSA.\n"
                f"A la solicitud de {categoria} se derivó al cliente al chat Sofía.",
            )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            })

    elif "reseña" in cat or "resena" in capi or "google" in cat:
        ticket_subj = f"Reseña recibida - Número de Ticket #{ticket_id}"
        contacts = await bitrix.search_contacts_by_email(from_email)
        contact_found = len(contacts) > 0
        await gmail.send_email(
            to=[from_email], subject=ticket_subj,
            body=email_templates.resena_ticket_email(nombre, ticket_id),
            body_type="html", bcc=_BCC, thread_id=thread_id,
        )
        if ticket_id:
            if contact_found:
                await bitrix.add_timeline_comment(
                    "dynamic_1034", ticket_id,
                    "Comunicarse con cliente.\n\nDejó una reseña en google.",
                )
            else:
                await bitrix.add_timeline_comment(
                    "dynamic_1034", ticket_id,
                    f"Comunicarse con cliente.\n\nDejó una reseña en google.\n"
                    f"El email del usuario no está en bitrix.\n"
                    f"Nombre: {nombre}\n Apellido: {apellido}\n Teléfono: {telefono}\n Email: {from_email}",
                )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldXQvHFuiY9ebvYa": "Se deriva con gestor",
                "fldquQJeU5QJmNfBa": "humano",
            })

    elif "moroso" in cat or capi == "moroso":
        await gmail.send_email(
            to=[from_email],
            subject="Aviso importante sobre el estado de su servicio",
            body=email_templates.moroso_email(nombre),
            body_type="html", bcc=_BCC, thread_id=thread_id,
        )
        if ticket_id:
            await bitrix.update_crm_item(1034, ticket_id, {
                "stageId":      "DT1034_120:CLIENT",
                "assignedById": "43712",
            })
            await bitrix.add_timeline_comment(
                "dynamic_1034", ticket_id,
                f"Se indicó al CLIENTE que el acceso a su trastero será inhabilitado en caso de impago.\n"
                f"Nombre: {nombre}\n Apellido: {apellido}\n Teléfono: {telefono}\n Email: {from_email}",
            )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            })

    elif "desestima" in cat or "desestima" in capi:
        await gmail.send_email(
            to=[from_email],
            subject="Agradecemos su interés y estaremos cuando nos necesite",
            body=email_templates.desestima_email(nombre),
            body_type="html", bcc=_BCC, thread_id=thread_id,
        )
        if ticket_id:
            await bitrix.update_crm_item(1034, ticket_id, {
                "stageId": "DT1034_120:PREPARATION",
            })
            await bitrix.add_timeline_comment(
                "dynamic_1034", ticket_id,
                f"El usuario DESESTIMA la oferta por la contratación de su módulo.\n"
                f"Nombre: {nombre}\n Apellido: {apellido}\n Teléfono: {telefono}\n Email: {from_email}",
            )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            })

    elif "foto" in cat or "foto" in capi:
        foto_contacts = await bitrix.search_contacts_by_email(from_email)
        foto_contact_found = len(foto_contacts) > 0
        await gmail.send_email(
            to=[from_email],
            subject=f"Número de Ticket #{ticket_id}",
            body=email_templates.foto_salida_ticket_email(nombre, ticket_id),
            body_type="html", bcc=_BCC, thread_id=thread_id,
        )
        if ticket_id:
            if foto_contact_found:
                await bitrix.update_crm_item(1034, ticket_id, {
                    "stageId": "DT1034_120:SUCCESS",
                })
                await bitrix.add_timeline_comment(
                    "dynamic_1034", ticket_id,
                    "Se reenvió al cliente URL para que suba las fotos de estado del trastero.",
                )
            else:
                await bitrix.update_crm_item(1034, ticket_id, {
                    "stageId":      "DT1034_120:CLIENT",
                    "assignedById": "20",
                })
                await bitrix.add_timeline_comment(
                    "dynamic_1034", ticket_id,
                    f"El usuario quiere subir las fotos del estado del trastero para proceder con la salida "
                    f"del trastero, pero su correo no está registrado.\n"
                    f"Nombre: {nombre}\n Apellido: {apellido}\n Teléfono: {telefono}\n Email: {from_email}",
                )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldXQvHFuiY9ebvYa": "Se deriva con gestor",
                "fldquQJeU5QJmNfBa": "humano",
            })

    elif "modificar_visita" in cat or "cancelar_visita" in cat or capi in ("modificar_visita", "cancelar_visita"):
        await gmail.send_email(
            to=[from_email], subject=subject,
            body=email_templates.visita_sofia_email(nombre, from_email, categoria),
            body_type="html", bcc=_BCC, thread_id=thread_id,
        )
        if ticket_id:
            await bitrix.update_crm_item(1034, ticket_id, {
                "assignedById": "6358",
                "title":        f"CGI - Respuesta EXITOSA: {categoria}",
                "stageId":      "DT1034_120:SUCCESS",
            })
            await bitrix.add_timeline_comment(
                "dynamic_1034", ticket_id,
                f"Respuesta automática EXITOSA.\n"
                f"A la solicitud de {categoria} se derivó al cliente al chat Sofía.",
            )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            })

    logger.info(f"[otros] done | categoria={categoria!r} | from={from_email}")


def _get_plantilla_enviada(
    categoria: str, bot_humano: str, is_req: bool, cliente: bool,
) -> str:
    """Devuelve el nombre de la plantilla enviada según el routing real."""
    if not (bot_humano == "bot" and (is_req or cliente)):
        return ""
    cat = categoria.lower()
    if cat == "aviso_salida":
        return "aviso_salida_sofia"
    if "mudanza" in cat:
        return "mudanza_sofia"
    if "materiales" in cat:
        return "materiales_sofia"
    if cat == "otros":
        return "otros_sofia"
    if categoria in _AREA_GENERAL_CATS:
        return "area_general_cta"
    if categoria in _AREA_CLIENTE_CATS:
        return "area_cliente"
    if "reseña" in cat or "resena" in cat:
        return "ticket_resena"
    if "moroso" in cat:
        return "moroso"
    if "desestima" in cat:
        return "desestima"
    if "foto" in cat:
        return "ticket_foto_salida"
    if "modificar_visita" in cat or "cancelar_visita" in cat:
        return "visita_sofia"
    return ""


async def _evaluar_pipeline(
    clasif_id: str,
    email_body: str,
    subject: str,
    tipo: str,
    bot_humano: str,
    categoria: str,
    plantilla_enviada: str,
    is_req: bool,
    examples_tipo: list,
    examples_bh: list,
    definitions: list,
    examples_clasif: list,
    summary_entry: dict = None,
) -> None:
    """Evaluación en cascada (background). Escribe en Airtable y actualiza el monitor."""
    eval_clasif_val        = "—"
    razon_eval_clasif      = "—"
    eval_tipo_val          = "—"
    razon_eval_tipo        = "—"
    eval_bh_val            = "—"
    razon_eval_bot_humano  = "—"
    efectividad_val        = "—"
    try:
        # Nivel 1: eval_clasif + eval_tipo + eval_bot_humano en paralelo
        # eval_clasif y eval_bot_humano evalúan las decisiones de nivel 1 (categoria y bot_humano)
        # eval_tipo evalúa la decisión de nivel 2 (tipo), pero no depende de las anteriores en eval
        if tipo == "accion":
            (eval_clasif_val, razon_eval_clasif), \
            (eval_bh_val, razon_eval_bot_humano), \
            (eval_tipo_val, razon_eval_tipo) = await asyncio.gather(
                openai_svc.eval_clasif(email_body, subject, categoria, definitions, examples_clasif),
                openai_svc.eval_bot_humano(email_body, categoria, bot_humano, examples_bh),
                openai_svc.eval_tipo(email_body, tipo, examples_tipo),
            )
            logger.info(f"[eval] eval_bot_humano={eval_bh_val} | razon={razon_eval_bot_humano}")
        else:
            (eval_clasif_val, razon_eval_clasif), \
            (eval_tipo_val, razon_eval_tipo) = await asyncio.gather(
                openai_svc.eval_clasif(email_body, subject, categoria, definitions, examples_clasif),
                openai_svc.eval_tipo(email_body, tipo, examples_tipo),
            )
        logger.info(f"[eval] eval_clasif={eval_clasif_val} | eval_tipo={eval_tipo_val}")

        # Nivel 2: efectividad (solo si tipo==accion, depende de bot_humano y is_req)
        if tipo == "accion":
            if bot_humano == "humano":
                efectividad_val = "escalado"
            elif not is_req:
                efectividad_val = "sin_accion"
            elif plantilla_enviada:
                efectividad_val = await openai_svc.eval_efectividad(
                    email_body, categoria, plantilla_enviada,
                )
                logger.info(f"[eval] efectividad={efectividad_val}")
            else:
                efectividad_val = "no_resuelto"

        if clasif_id:
            await airtable.update_record(
                config.AT_TBL_CLASIFICACION,
                clasif_id,
                {
                    "eval_clasif":           eval_clasif_val,
                    "razon_eval_clasif":     razon_eval_clasif,
                    "eval_tipo":             eval_tipo_val,
                    "razon_eval_tipo":       razon_eval_tipo,
                    "eval_bot_humano":       eval_bh_val,
                    "razon_eval_bot_humano": razon_eval_bot_humano,
                    "efectividad":           efectividad_val,
                },
            )
            logger.info(f"[eval] Airtable actualizado | {eval_clasif_val} / {eval_tipo_val} / {eval_bh_val} / {efectividad_val}")

        if summary_entry is not None:
            summary_entry["eval_clasif"]           = eval_clasif_val
            summary_entry["razon_eval_clasif"]     = razon_eval_clasif
            summary_entry["eval_tipo"]             = eval_tipo_val
            summary_entry["razon_eval_tipo"]       = razon_eval_tipo
            summary_entry["eval_bot_humano"]       = eval_bh_val
            summary_entry["razon_eval_bot_humano"] = razon_eval_bot_humano
            summary_entry["efectividad"]           = efectividad_val
            _save_summaries()

    except Exception as exc:
        logger.warning(f"[eval] Error en evaluación pipeline: {exc}")


async def run_retroactive_eval(limit: int = 50) -> dict:
    """Evalúa registros de Clasificación que no tienen eval_clasif."""
    # 1. Cargar ejemplos una sola vez
    definitions = [r["fields"] for r in await airtable.search_records(
        config.AT_TBL_DEFINICIONES, formula="", max_records=50,
        fields=["Categoria", "Descripcion", "Enlace", "categoria_api"],
    )]
    examples_clasif = [r["fields"] for r in await airtable.search_records(
        config.AT_TBL_EJEMPLOS_CLASIF, formula="", max_records=50,
        fields=["Ejemplos", "Categoria Asignada"],
    )]
    examples_tipo = [r["fields"] for r in await airtable.search_records(
        config.AT_TBL_EJEMPLOS_TIPO, formula="", max_records=50,
        fields=["Fragmento de Correo", "Tipo de correo"],
    )]
    examples_bh = [r["fields"] for r in await airtable.search_records(
        config.AT_TBL_EJEMPLOS_BOT_HUMANO, formula="", max_records=50,
        fields=["Fragmento de Correo", "Bot o Humano"],
    )]

    # 2. Buscar registros sin eval_clasif
    records = await airtable.search_records(
        config.AT_TBL_CLASIFICACION,
        formula='AND({eval_clasif}="", {thread_id}!="")',
        max_records=limit,
    )

    processed = 0
    skipped   = 0
    for rec in records:
        rec_id = rec["id"]
        fields = rec.get("fields", {})
        thread_id  = fields.get("thread_id", "") or fields.get("fldpuawV9XMHjYpSp", "")
        tipo       = fields.get("tipo", "")        or fields.get("fldjXk8GniT6hO6oa", "")
        categoria  = fields.get("categoria_api", "") or fields.get("fldX2vzDBKwrXmiGQ", "")
        bot_humano_v = fields.get("bot_humano", "") or "bot"

        if not thread_id or not tipo:
            skipped += 1
            continue

        # 3. Cuerpo del email desde Gmail
        try:
            subject_r, email_body = await gmail.get_thread_body(thread_id)
        except Exception as exc:
            logger.warning(f"[retro-eval] No se pudo obtener thread {thread_id}: {exc}")
            skipped += 1
            continue

        if not email_body:
            skipped += 1
            continue

        # 4. Evaluar
        try:
            eval_clasif_val, razon_eval_clasif     = "—", "—"
            eval_tipo_val,   razon_eval_tipo        = "—", "—"
            eval_bh_val,     razon_eval_bot_humano  = "—", "—"

            if tipo == "accion":
                (eval_clasif_val, razon_eval_clasif), \
                (eval_bh_val, razon_eval_bot_humano), \
                (eval_tipo_val, razon_eval_tipo) = await asyncio.gather(
                    openai_svc.eval_clasif(email_body, subject_r, categoria, definitions, examples_clasif),
                    openai_svc.eval_bot_humano(email_body, categoria, bot_humano_v, examples_bh),
                    openai_svc.eval_tipo(email_body, tipo, examples_tipo),
                )
                if bot_humano_v == "humano":
                    efectividad_val = "escalado"
                else:
                    efectividad_val = "no_resuelto"
            else:
                (eval_clasif_val, razon_eval_clasif), \
                (eval_tipo_val, razon_eval_tipo) = await asyncio.gather(
                    openai_svc.eval_clasif(email_body, subject_r, categoria, definitions, examples_clasif),
                    openai_svc.eval_tipo(email_body, tipo, examples_tipo),
                )
                efectividad_val = "sin_accion"

            await airtable.update_record(config.AT_TBL_CLASIFICACION, rec_id, {
                "eval_clasif":           eval_clasif_val,
                "razon_eval_clasif":     razon_eval_clasif,
                "eval_tipo":             eval_tipo_val,
                "razon_eval_tipo":       razon_eval_tipo,
                "eval_bot_humano":       eval_bh_val,
                "razon_eval_bot_humano": razon_eval_bot_humano,
                "efectividad":           efectividad_val,
            })
            logger.info(f"[retro-eval] {rec_id} | {eval_clasif_val}/{eval_tipo_val}/{eval_bh_val}/{efectividad_val}")
            processed += 1
        except Exception as exc:
            logger.warning(f"[retro-eval] Error evaluando {rec_id}: {exc}")
            skipped += 1

    return {"processed": processed, "skipped": skipped, "total": len(records)}


async def process_new_emails():
    """Lee emails nuevos no leídos y los procesa uno a uno."""
    if _lock.locked():
        return
    async with _lock:
        messages = await gmail.list_unread_emails()
        if not messages:
            return

        logger.info(f"[1] {len(messages)} email(s) nuevos encontrados")
        for msg in messages:
            try:
                await _process_email(msg)
            except Exception as exc:
                logger.error(f"[1] Error procesando {msg.get('id')}: {exc}", exc_info=True)
                await telegram.send_alert(
                    f"⚠️ *Email CGI* — error procesando email\n"
                    f"🆔 `{msg.get('id')}`\n"
                    f"❌ `{type(exc).__name__}: {str(exc)[:200]}`"
                )
