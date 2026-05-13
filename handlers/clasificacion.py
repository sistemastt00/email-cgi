"""
handlers/clasificacion.py — Escenario 1: Pipeline principal

Ciclo completo por cada email nuevo:
  1. Filtro blacklist → marca como leído y sale
  2. Busca registro existente en Datos extraídos (duplicado)
  3. GPT: bot_humano  (BC_Ejemplos Bot_Humano)
  4. GPT: categoria + tipo (solo si no hay duplicado exacto)
  5. Crea registro en Clasificación
  6. Marca como leído
  7. Secuencia principal (hilo nuevo): 1.1 → 1.0 → 1.5 condicional
  8. Secuencia cadena (hilo existente): 1.5 con datos existentes → 1.2 condicional
"""
import logging
import config
from services import gmail, airtable, openai_svc
from handlers import correo_clasif, extraccion_1er, extraccion_cadena, bot_humano, respuesta_general

logger = logging.getLogger("email-cgi")

_RESPUESTA_GENERAL_CATS = {
    "Agendar Visita", "Reservar Tu Trastero", "Autorizar a Terceros",
    "Notificar Incidencia", "Actualizar Tus Datos", "Hacer Inventario",
    "Hacer Valoración", "Presupuesto", "Cambio de Titular/Modulo",
}


def _is_blacklisted(from_email: str) -> bool:
    addr = from_email.lower()
    return any(pattern in addr for pattern in config.EMAIL_BLACKLIST_CONTAINS)


async def _process_email(msg_stub: dict):
    message_id = msg_stub["id"]
    thread_id  = msg_stub["threadId"]

    email      = await gmail.get_email(message_id)
    from_email = email.get("fromEmail", "")
    subject    = email.get("subject", "")
    body       = email.get("fullTextBody") or email.get("htmlBody") or subject

    # 1. Blacklist
    if _is_blacklisted(from_email):
        logger.info(f"[1] Ignorado (blacklist) | from={from_email}")
        await gmail.mark_as_read(message_id)
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
            config.AT_TBL_EJEMPLOS_BOT_HUMANO, formula="", max_records=100,
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
    await gmail.mark_as_read(message_id)

    args_base = {
        "message_id":       message_id,
        "thread_id":        thread_id,
        "categoria_correo": categoria_api or categoria,
        "tipo_correo":      tipo,
        "bot_humano":       bot_humano_result,
        "row":              clasif_record_id,
        "subject":          subject,
    }

    # 7. Secuencia principal: solo si es hilo nuevo
    if is_new_thread:
        # 1.1 primero (devuelve lead_id, nombre, Cliente)
        extrac_result = {}
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

        # 1.4 respuesta_general: si bot_humano=="bot" y categoria tiene respuesta automática
        if (bot_humano_result == "bot"
                and (categoria in _RESPUESTA_GENERAL_CATS
                     or categoria_api in _RESPUESTA_GENERAL_CATS)):
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

    # 8. Secuencia cadena: si hay registro existente en Datos extraídos
    if existing:
        ex_nombre   = existing_fields.get("nombre", "")
        ex_lead_id  = existing_fields.get("lead_id", "")
        ex_categoria = existing_fields.get("categoria_api", "")
        ex_tipo     = existing_fields.get("tipo", "")

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
                    "message_id":        message_id,
                    "thread_id":         thread_id,
                    "categoria_correo":  ex_categoria,
                    "categoria_correo_api": ex_categoria,
                    "tipo_correo":       ex_tipo,
                    "bot_humano":        bot_humano_result,
                })
                logger.info(f"[1] 1.2 ok | {r90}")
            except Exception as exc:
                logger.error(f"[1] Error en 1.2: {exc}", exc_info=True)


async def process_new_emails():
    """Lee emails nuevos no leídos y los procesa uno a uno."""
    messages = await gmail.list_unread_emails()
    if not messages:
        return

    logger.info(f"[1] {len(messages)} email(s) nuevos encontrados")
    for msg in messages:
        try:
            await _process_email(msg)
        except Exception as exc:
            logger.error(f"[1] Error procesando {msg.get('id')}: {exc}", exc_info=True)
