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
import logging
import config
from services import gmail, airtable, bitrix, openai_svc
from handlers import correo_clasif, extraccion_1er, extraccion_cadena, bot_humano, respuesta_general, email_templates

_lock = asyncio.Lock()
summaries: collections.deque = collections.deque(maxlen=100)

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

_AREA_GENERAL_CATS = {
    "Agendar Visita", "Reservar Tu Trastero", "Notificar Incidencia",
    "Hacer Valoración", "Hacer Inventario", "Autorizar a Terceros",
    "Actualizar Tus Datos", "Cambio de Titular/Modulo", "Presupuesto",
    "Cambio de trastero",
    "agendar_visita", "reservar_trastero", "notificar_incidencia",
    "hacer_valoracion", "hacer_inventario", "autorizar_terceros",
    "actualizar_datos", "cambio_titular", "presupuesto", "cambio_trastero",
}

_AREA_CLIENTE_CATS = {
    "Mis Documentos", "Documentos Generales", "Claves de Acceso",
    "Pagar Facturas", "Ver Facturas", "Renueve Promocion", "Cancelar Tu Trastero",
    "mis_documentos", "documentos_generales", "claves_acceso",
    "pagar_facturas", "ver_facturas", "renueve_promocion", "cancelar_trastero",
}

_OTROS_SERVICIOS_CATS = {
    "Mudanza", "mudanza",
    "Materiales de embalaje", "tu_caja",
    "Otros", "otros",
    "Reseña google", "resena_google",
    "Moroso", "moroso",
    "Desestima Oferta", "desestima_oferta",
    "Foto Salida", "foto_salida",
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
            "lead_id":    "—",
            "nombre":     "—",
            "resultado":  "Ignorado (blacklist)",
            "error":      False,
            "logs":       list(_flow_logs),
        })
        return

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

    # 3. GPT: bot_humano
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

    # 4. GPT: categoria + tipo
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
    if is_new_thread:
        # 1.1 primero (devuelve lead_id, nombre, Cliente)
        try:
            extrac_result = await extraccion_1er.run(args_base)
            logger.info(f"[1] 1.1 ok | {extrac_result}")
        except Exception as exc:
            logger.error(f"[1] Error en 1.1: {exc}", exc_info=True)

        lead_id = extrac_result.get("lead_id", "")
        nombre  = extrac_result.get("nombre", "")
        cliente = extrac_result.get("Cliente", False)

        # 1.0 con lead_id de 1.1
        try:
            r10 = await correo_clasif.run({**args_base, "lead_id": lead_id})
            logger.info(f"[1] 1.0 ok | {r10}")
        except Exception as exc:
            logger.error(f"[1] Error en 1.0: {exc}", exc_info=True)

        # 1.5 si (tipo==Requerimiento AND categoria!=Franquicia) OR cliente==True
        is_req = tipo == "Requerimiento" and "franquicia" not in (categoria_api or categoria).lower()
        if is_req or cliente:
            try:
                r15 = await bot_humano.run({
                    **args_base,
                    "lead_id": lead_id,
                    "nombre":  nombre,
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
                        "lead_id":  lead_id,
                        "nombre":   nombre,
                        "apellido": extrac_result.get("apellido", ""),
                    })
                    logger.info(f"[1] 1.4 ok | {r14}")
                except Exception as exc:
                    logger.error(f"[1] Error en 1.4: {exc}", exc_info=True)

            elif categoria in _AREA_CLIENTE_CATS or categoria_api in _AREA_CLIENTE_CATS:
                try:
                    await _send_area_cliente_email(
                        message_id=message_id, nombre=nombre, lead_id=lead_id,
                        clasif_id=clasif_record_id, categoria=categoria,
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
                    nombre=nombre, lead_id=lead_id,
                    clasif_id=clasif_record_id, message_id=message_id,
                )
                logger.info(f"[1] otros_servicios ok | categoria={categoria}")
            except Exception as exc:
                logger.error(f"[1] Error en otros_servicios: {exc}", exc_info=True)

    # 8. Secuencia cadena: si hay registro existente en Datos extraídos
    if existing:
        ex_nombre    = existing_fields.get("nombre", "")
        ex_lead_id   = existing_fields.get("lead_id", "")
        ex_categoria = existing_fields.get("categoria_api", "")
        ex_tipo      = existing_fields.get("tipo", "")

        # 1.5 con datos del registro existente (módulo 89)
        try:
            r89 = await bot_humano.run({
                "message_id":       message_id,
                "thread_id":        thread_id,
                "nombre":           ex_nombre,
                "lead_id":          ex_lead_id,
                "categoria_correo": ex_categoria,
                "bot_humano":       bot_humano_result,
                "subject":          subject,
                "row":              clasif_record_id,
            })
            logger.info(f"[1] 1.5 (cadena) ok | {r89}")
        except Exception as exc:
            logger.error(f"[1] Error en 1.5 (cadena): {exc}", exc_info=True)

        # 1.2 si bot_humano != "bot" AND tipo_existente == "Requerimiento" (módulo 90)
        if bot_humano_result != "bot" and ex_tipo == "Requerimiento":
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
    _nombre  = extrac_result.get("nombre", "") if is_new_thread else existing_fields.get("nombre", "")
    _lead_id = extrac_result.get("lead_id", "") if is_new_thread else existing_fields.get("lead_id", "")

    _sent_to_client = bot_humano_result == "bot" and (is_req or cliente)
    if bot_humano_result == "humano":
        resultado = "Ticket enviado al cliente + lead → HUMANO"
    elif is_new_thread and _sent_to_client:
        resultado = "Respuesta automática CTA enviada"
    elif not is_new_thread:
        resultado = "Cadena: clasificado + 1.5/1.2"
    else:
        resultado = "Clasificado + correo clasificación enviado"

    summaries.appendleft({
        "time":       datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
        "from_email": from_email,
        "from_name":  email.get("fromName", ""),
        "subject":    subject,
        "hilo":       "nuevo" if is_new_thread else "cadena",
        "categoria":  categoria,
        "tipo":       tipo,
        "bot_humano": bot_humano_result,
        "lead_id":    _lead_id,
        "nombre":     _nombre,
        "resultado":  resultado,
        "error":      False,
        "logs":       list(_flow_logs),
    })


async def _send_area_cliente_email(
    message_id: str, nombre: str, lead_id: str, clasif_id: str, categoria: str,
):
    email      = await gmail.get_email(message_id)
    from_email = email.get("fromEmail", "")
    subj       = email.get("subject", "")

    await gmail.send_email(
        to=[from_email],
        subject=subj,
        body=email_templates.area_cliente_email(nombre),
        body_type="html",
        bcc=_BCC,
    )

    if lead_id:
        await bitrix.update_lead(lead_id, {
            "ASSIGNED_BY_ID": "6358",
            "TITLE":          f"CGI - Respuesta EXITOSA: {categoria}",
        })
        await bitrix.add_timeline_comment(
            "lead", lead_id,
            f"Respuesta automática EXITOSA.\n"
            f"A la solicitud de {categoria} se generó la siguiente RESPUESTA AUTOMÁTICA: "
            f"Enlace a {categoria} de la web Tu Trastero.",
        )

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
    nombre: str, lead_id: str, clasif_id: str, message_id: str,
):
    cat  = categoria.lower()
    capi = categoria_api.lower()

    if "mudanza" in cat or capi == "mudanza":
        await gmail.send_email(
            to=[from_email], subject=subject,
            body=email_templates.mudanza_email(nombre),
            body_type="html", bcc=_BCC,
        )
        if lead_id:
            await bitrix.update_lead(lead_id, {
                "ASSIGNED_BY_ID": "6358",
                "TITLE":          "CGI - Respuesta EXITOSA: Mudanza",
            })
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldXQvHFuiY9ebvYa": "Se deriva con gestor",
                "fldquQJeU5QJmNfBa": "humano",
            })

    elif "materiales" in cat or capi == "tu_caja":
        await gmail.send_email(
            to=[from_email], subject=subject,
            body=email_templates.materiales_email(nombre),
            body_type="html", bcc=_BCC,
        )
        if lead_id:
            await bitrix.update_lead(lead_id, {
                "ASSIGNED_BY_ID": "6358",
                "TITLE":          "CGI - Respuesta EXITOSA: Tu Caja",
            })
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            })

    elif cat == "otros" or capi == "otros":
        ticket_subj = f"Número de Ticket # {lead_id} - {subject}"
        await gmail.send_email(
            to=[from_email], subject=ticket_subj,
            body=email_templates.otros_ticket_email(nombre, lead_id),
            body_type="html", bcc=_BCC,
        )
        if lead_id:
            await bitrix.update_lead(lead_id, {
                "STAGE_ID":       "UC_M25V3A",
                "ASSIGNED_BY_ID": "6358",
                "TITLE":          "CGI - Respuesta EXITOSA: (Sin clasificar)",
            })
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldXQvHFuiY9ebvYa": "Se deriva con gestor",
                "fldquQJeU5QJmNfBa": "humano",
            })

    elif "reseña" in cat or "resena" in capi or "google" in cat:
        ticket_subj = f"Reseña recibida - Número de Ticket #{lead_id}"
        await gmail.send_email(
            to=[from_email], subject=ticket_subj,
            body=email_templates.resena_ticket_email(nombre, lead_id),
            body_type="html", bcc=_BCC,
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
            body_type="html", bcc=_BCC,
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
            body_type="html", bcc=_BCC,
        )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldgj898WCeUM3QqV": "Enlace a web",
                "fldquQJeU5QJmNfBa": "bot",
            })

    elif "foto" in cat or "foto" in capi:
        await gmail.send_email(
            to=[from_email],
            subject=f"Número de Ticket #{lead_id}",
            body=email_templates.foto_salida_ticket_email(nombre, lead_id),
            body_type="html", bcc=_BCC,
        )
        if clasif_id:
            await airtable.update_record(config.AT_TBL_CLASIFICACION, clasif_id, {
                "fldXQvHFuiY9ebvYa": "Se deriva con gestor",
                "fldquQJeU5QJmNfBa": "humano",
            })

    logger.info(f"[otros] done | categoria={categoria!r} | from={from_email}")


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
