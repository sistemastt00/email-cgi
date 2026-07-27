"""
services/openai_svc.py — Wrapper asíncrono sobre el SDK de OpenAI.

extract_structured_data() replica el módulo "transformTextToStructuredData" de Make.
Las 3 funciones de clasificación usan los prompts exactos del blueprint.
"""
import json
from openai import AsyncOpenAI
import config

_client = AsyncOpenAI(api_key=config.OPENAI_KEY)


# ─── Primitiva: extracción de datos estructurados ─────────────────────────────

async def extract_structured_data(
    text: str,
    prompt: str,
    parameters: list[dict],
    model: str = None,
) -> dict:
    """
    Extrae campos estructurados de un texto usando function calling.

    parameters: lista de dicts con claves:
        name        (str)  — nombre del campo
        type        (str)  — "string" | "number" | "boolean"
        description (str)  — descripción para el modelo
        isRequired  (bool) — si el campo es obligatorio
    """
    model = model or config.OPENAI_MODEL

    props = {}
    required = []
    for p in parameters:
        props[p["name"]] = {
            "type":        p.get("type", "string"),
            "description": p.get("description", ""),
        }
        if p.get("isRequired", False):
            required.append(p["name"])

    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required

    response = await _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user",   "content": text},
        ],
        tools=[{
            "type": "function",
            "function": {
                "name":        "extract_data",
                "description": "Extrae datos estructurados del texto",
                "parameters":  schema,
            },
        }],
        tool_choice={"type": "function", "function": {"name": "extract_data"}},
    )

    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments)


# ─── Nodo 1: bot_humano ───────────────────────────────────────────────────────

async def classify_bot_humano(
    email_body: str,
    examples: list[dict],
    model: str = None,
) -> str:
    """
    Clasifica si el correo debe ser atendido por bot o humano.
    examples: registros de BC_Ejemplos Bot_Humano
    Devuelve: "bot" | "humano"
    """
    examples_text = json.dumps(examples, ensure_ascii=False)

    prompt = (
        "Actuarás como un Analista Experto de Intención de Correo Electrónico. "
        "Tu objetivo principal es analizar el contenido de un correo electrónico y clasificarlo "
        "en una de dos categorías: bot o humano. La clasificación debe basarse estrictamente en "
        "la necesidad explícita o implícita de que la solicitud sea manejada por una persona.\n\n"
        "# CONTEXTO\n"
        "Recibirás el contenido de un correo electrónico. Este puede ser el primer mensaje de un "
        "usuario o parte de una cadena de correos. Debes prestar especial atención al tono, las "
        "palabras clave y el historial de la conversación si se proporciona.\n\n"
        "# CATEGORÍAS DE CLASIFICACIÓN\n"
        "- bot: El correo contiene una solicitud que puede ser gestionada, al menos inicialmente, "
        "por un sistema automatizado o bot. (Clasificación por defecto)\n"
        "- humano: El correo debe ser manejado por un agente humano. La intervención de un bot ya "
        "no es suficiente o deseada por el emisor.\n\n"
        "# REGLAS DE DECISIÓN (CRITERIOS)\n"
        "- Clasificarás como \"bot\" si cumple con lo siguiente:\n"
        "Preguntas Informativas Estándar: Consultas sobre el estado de un pedido, solicitudes de "
        "factura, preguntas frecuentes (FAQs), restablecimiento de contraseñas, etc.\n"
        "Primer Contacto: Es el primer correo sobre un tema rutinario, aunque se dirija a una "
        "persona (ej. \"Hola equipo, ¿podéis decirme...\").\n"
        "Navegación o Búsqueda de Información: El usuario busca información que probablemente se "
        "encuentre en una base de conocimientos o página web.\n"
        "Respuestas a notificaciones automáticas que no expresan un problema, como un simple "
        "\"Gracias\".\n\n"
        "- Clasificarás como\" humano\" si detectas CUALQUIERA de los siguientes criterios:\n"
        "Petición Explícita: El emisor usa frases directas como \"quiero hablar con una persona\", "
        "\"necesito un agente\", \"pásame con un humano\", \"ayuda de un operador\".\n"
        "Cuando solicita alguna confirmación (ejemplo: ¿Me lo podrían confirmar?)\n"
        "Frustración con Automatización: El emisor muestra frustración con respuestas anteriores, "
        "usando frases como \"no me entiendes\", \"tu respuesta no sirve\", \"esto no es lo que "
        "pregunté\", \"deja de enviarme respuestas automáticas\".\n"
        "Insistencia o Escalada: Es parte de una cadena de correos y el emisor insiste en su punto, "
        "reitera una pregunta no resuelta o pide escalar el caso (\"quiero poner una queja\", "
        "\"necesito hablar con un supervisor\").\n"
        "Respuesta a un correo automático: El emisor del correo puede estar respondiendo a un correo "
        "automático (ej. Necesito que me informen de los plazos de devoluciones, si whatapp no es un "
        "canal oficial de comunicación, no se comuniquen por ahí, email si es un canal oficial. No "
        "puedo hablar por teléfono me encuentro en el trabajo).\n"
        "Complejidad o Sensibilidad: El tema es intrínsecamente complejo, contiene múltiples preguntas "
        "no relacionadas o trata sobre un asunto sensible (ej. una queja formal, un problema de "
        "seguridad, una situación emocional) que un bot no podría gestionar con el matiz adecuado.\n\n"
        "Referencia a un fallo previo del bot: \"El bot no pudo ayudarme\", \"ya he intentado la "
        "solución automática\".\n\n"
        f"#EJEMPLOS DE CLASIFICACIÓN\n{examples_text}\n\n"
        "#FORMATO DE RESPUESTA\n"
        "Elige solo:\n"
        "-bot\n"
        "-humano"
    )

    result = await extract_structured_data(
        text=email_body,
        prompt=prompt,
        parameters=[{
            "name": "bot_humano",
            "type": "string",
            "description": "La respuesta es uno de los valores: \"bot\" o \"humano\"",
            "isRequired": False,
        }],
        model=model,
    )
    return result.get("bot_humano", "humano")


# ─── Nodo 2: clasificacion (categoria) ───────────────────────────────────────

async def classify_categoria(
    subject: str,
    email_body: str,
    definitions: list[dict],
    examples_clasif: list[dict],
    model: str = None,
) -> dict:
    """
    Clasifica la categoría del correo.
    definitions:     registros de BC_Definiciones (campos: Categoria, Descripcion, Enlace, categoria_api)
    examples_clasif: registros de BC_Ejemplos Clasificación (campos: Ejemplos, Categoria Asignada)
    Devuelve: {"categoria": str, "categoria_api": str}
    """
    defs_text    = json.dumps(definitions,     ensure_ascii=False)
    examples_text = json.dumps(examples_clasif, ensure_ascii=False)

    prompt = (
        "Eres un asistente experto en la clasificación de correos para un negocio de self-storage. "
        "Tu única tarea es clasificar el correo electrónico proporcionado en una de las siguientes categorias.\n\n"
        "Utiliza las definiciones como guía general y los ejemplos como casos prácticos de alta prioridad.\n\n"
        f"--- DEFINICIONES DE CATEGORÍAS ---{defs_text}\n\n"
        f"--- EJEMPLOS DE CLASIFICACIÓN ---{examples_text}\n\n"
        "--- INSTRUCCIÓN ---\n"
        "Basado en las definiciones, los ejemplos y el contenido del correo, ¿a qué categoría pertenece? "
        "Responde únicamente con la palabra exacta de la \"categoria\" y su correspondiente \"categoria_api\"."
    )

    result = await extract_structured_data(
        text=subject + email_body,
        prompt=prompt,
        parameters=[
            {
                "name": "categoria",
                "type": "string",
                "description": f"La respuesta es uno de los valores de Categoria en: {defs_text}",
                "isRequired": False,
            },
            {
                "name": "categoria_api",
                "type": "string",
                "description": f"La respuesta es uno de los valores de categoria_api en: {defs_text}",
                "isRequired": False,
            },
        ],
        model=model,
    )
    return result


# ─── Nodo 3: tipo ─────────────────────────────────────────────────────────────

async def classify_tipo(
    subject: str,
    email_body: str,
    from_email: str,
    categoria: str,
    examples_clasif: list[dict],
    examples_tipo: list[dict],
    model: str = None,
) -> str:
    """
    Clasifica el tipo del correo: accion o informacion.
    examples_clasif: registros de BC_Ejemplos Clasificación
    examples_tipo:   registros de BC_Ejemplos Tipo (campos: Fragmento de Correo, Tipo de correo)
    Devuelve: "accion" | "informacion"
    """
    examples_clasif_text = json.dumps(examples_clasif, ensure_ascii=False)
    examples_tipo_text   = json.dumps(examples_tipo,   ensure_ascii=False)

    prompt = (
        "Eres un asistente experto en la clasificación de correos para un negocio de self-storage. "
        "Tu principal tarea es analizar e identificar el \"tipo\" de correo electrónico. "
        "Los tipos pueden ser \"accion\" o \"informacion\"\n\n"
        f"- accion: en base, primero, al cuerpo y, luego, al asunto del correo electrónico "
        f"de categoría {categoria}, analiza si el emisor solicita o requiere cierta información "
        f"relacionada a la categoría identificada. Además, en base a la categoría {categoria} y a "
        f"los ejemplos de la base de conocimiento {examples_clasif_text}, identifica si brinda "
        "información con el objetivo de solicitar algo referente a la categoría "
        f"{categoria}. Además, analiza si la intención del mensaje es para reclamar algo y espera "
        "una respuesta.  En caso la categoría "
        f"{categoria} sea \"mis_documentos\", \"documentos_generales\", \"claves_acceso\", "
        "\"pagar_facturas\", \"ver_facturas\", \"renueve_promocion\", \"aviso_salida\", "
        "\"incidencia\" has un análisis más profundo, y determina si el emisor hace una "
        "solicitud, y clasificalo como \"accion\".\n\n"
        "- informacion: en base, primero, al cuerpo y, luego, al asunto del correo electrónico de "
        f"categoría {categoria}, analiza si el cuerpo del correo electrónico solo muestra información "
        "y no solicita nada respecto a la categoría. Además, esta categoría debe clasificar los correos "
        "que tengan intensión de vender, ofrecer o mostrar algún producto o servicio.\n\n"
        f"--- EJEMPLOS DE TIPOS---\n{examples_tipo_text}\n\n"
        "La salida debe ser una de las siguiente: \"accion\" o \"informacion\""
    )

    result = await extract_structured_data(
        text=subject + email_body,
        prompt=prompt,
        parameters=[{
            "name": "tipo",
            "type": "string",
            "description": "accion o informacion",
            "isRequired": False,
        }],
        model=model,
    )
    return result.get("tipo", "informacion")


# ─── Evaluación de clasificaciones ───────────────────────────────────────────

async def eval_tipo(
    email_body: str,
    tipo: str,
    examples_tipo: list[dict],
) -> tuple[str, str]:
    """Evalúa si tipo (accion/informacion) fue clasificado correctamente.
    El evaluador primero clasifica independientemente y luego compara con el original.
    Devuelve: ('correcto'|'incorrecto', razon)
    """
    examples_text = json.dumps(examples_tipo, ensure_ascii=False)
    prompt = (
        "Eres un evaluador experto de clasificaciones de correo para Tu Trastero "
        "(empresa de self-storage).\n\n"
        "PASO 1 — Clasifica TÚ MISMO este correo:\n"
        "- 'accion': el cliente solicita o requiere una gestión concreta de la empresa\n"
        "- 'informacion': el cliente solo aporta información o el correo no requiere gestión\n\n"
        f"--- EJEMPLOS DE REFERENCIA ---\n{examples_text}\n\n"
        f"PASO 2 — Compara tu clasificación con la clasificación original: \"{tipo}\"\n"
        "- Si coinciden → evaluacion: correcto\n"
        "- Si difieren  → evaluacion: incorrecto + razón breve de la discrepancia (máx 1 frase)"
    )
    result = await extract_structured_data(
        text=email_body, prompt=prompt,
        parameters=[
            {
                "name": "tipo_evaluado", "type": "string",
                "description": "Tu propia clasificación del correo: accion o informacion", "isRequired": True,
            },
            {
                "name": "evaluacion", "type": "string",
                "description": "correcto o incorrecto (comparando tipo_evaluado con la clasificación original)", "isRequired": True,
            },
            {
                "name": "razon", "type": "string",
                "description": "Razón breve de la discrepancia (solo si incorrecto, máx 1 frase)", "isRequired": False,
            },
        ],
        model="gpt-4o-mini",
    )
    tipo_eval = result.get("tipo_evaluado", "").lower().strip()
    razon     = result.get("razon", "").strip()
    # Forzar consistencia: si el evaluador clasificó igual que el original → siempre correcto
    if tipo_eval in ("accion", "informacion"):
        val = "correcto" if tipo_eval == tipo else "incorrecto"
    else:
        val = result.get("evaluacion", "").lower().strip()
        val = val if val in ("correcto", "incorrecto") else "correcto"
    return (val, razon)


async def eval_clasif(
    email_body: str,
    subject: str,
    categoria: str,
    definitions: list[dict],
    examples_clasif: list[dict],
) -> tuple[str, str]:
    """Evalúa si la categoría fue clasificada correctamente.
    El evaluador primero clasifica independientemente y luego compara con el original.
    Devuelve: ('correcto'|'incorrecto', razon)
    """
    defs_text     = json.dumps(definitions,    ensure_ascii=False)
    examples_text = json.dumps(examples_clasif, ensure_ascii=False)
    prompt = (
        "Eres un evaluador experto de clasificaciones de correo para Tu Trastero "
        "(empresa de self-storage).\n\n"
        "PASO 1 — Clasifica TÚ MISMO la categoría de este correo usando las definiciones y ejemplos:\n\n"
        f"--- DEFINICIONES ---\n{defs_text}\n\n"
        f"--- EJEMPLOS ---\n{examples_text}\n\n"
        f"PASO 2 — Compara tu categoría con la clasificación original: \"{categoria}\"\n"
        "- Si coinciden → evaluacion: correcto\n"
        "- Si difieren  → evaluacion: incorrecto + razón breve de la discrepancia (máx 1 frase)"
    )
    result = await extract_structured_data(
        text=subject + "\n" + email_body, prompt=prompt,
        parameters=[
            {
                "name": "categoria_evaluada", "type": "string",
                "description": "Tu propia clasificación de la categoría del correo", "isRequired": True,
            },
            {
                "name": "evaluacion", "type": "string",
                "description": "correcto o incorrecto (comparando categoria_evaluada con la clasificación original)", "isRequired": True,
            },
            {
                "name": "razon", "type": "string",
                "description": "Razón breve de la discrepancia (solo si incorrecto, máx 1 frase)", "isRequired": False,
            },
        ],
        model="gpt-4o-mini",
    )
    cat_eval = result.get("categoria_evaluada", "").strip()
    razon    = result.get("razon", "").strip()
    # Forzar consistencia: si el evaluador clasificó igual que el original → siempre correcto
    if cat_eval:
        val = "correcto" if cat_eval.lower() == categoria.lower() else "incorrecto"
    else:
        val = result.get("evaluacion", "").lower().strip()
        val = val if val in ("correcto", "incorrecto") else "correcto"
    return (val, razon)


async def eval_bot_humano(
    email_body: str,
    categoria: str,
    bot_humano: str,
    examples_bh: list[dict],
) -> tuple[str, str]:
    """Evalúa si la decisión bot/humano fue correcta.
    El evaluador primero decide independientemente y luego compara con el original.
    Devuelve: ('correcto'|'incorrecto', razon)
    """
    examples_text = json.dumps(examples_bh, ensure_ascii=False)
    prompt = (
        "Eres un evaluador experto de clasificaciones de correo para Tu Trastero "
        "(empresa de self-storage).\n\n"
        "PASO 1 — Decide TÚ MISMO si este correo (categoría: \"{categoria}\") debe ir a 'bot' o 'humano':\n"
        "- 'bot': puede gestionarse automáticamente\n"
        "- 'humano': requiere intervención de un agente humano\n\n"
        f"--- EJEMPLOS DE REFERENCIA ---\n{{examples_text}}\n\n"
        f"PASO 2 — Compara tu decisión con la decisión original: \"{bot_humano}\"\n"
        "- Si coinciden → evaluacion: correcto\n"
        "- Si difieren  → evaluacion: incorrecto + razón breve de la discrepancia (máx 1 frase)"
    ).format(categoria=categoria, examples_text=examples_text, bot_humano=bot_humano)
    result = await extract_structured_data(
        text=email_body, prompt=prompt,
        parameters=[
            {
                "name": "bh_evaluado", "type": "string",
                "description": "Tu propia decisión: bot o humano", "isRequired": True,
            },
            {
                "name": "evaluacion", "type": "string",
                "description": "correcto o incorrecto (comparando bh_evaluado con la decisión original)", "isRequired": True,
            },
            {
                "name": "razon", "type": "string",
                "description": "Razón breve de la discrepancia (solo si incorrecto, máx 1 frase)", "isRequired": False,
            },
        ],
        model="gpt-4o-mini",
    )
    bh_eval = result.get("bh_evaluado", "").lower().strip()
    razon   = result.get("razon", "").strip()
    # Forzar consistencia: si el evaluador decidió igual que el original → siempre correcto
    if bh_eval in ("bot", "humano"):
        val = "correcto" if bh_eval == bot_humano else "incorrecto"
    else:
        val = result.get("evaluacion", "").lower().strip()
        val = val if val in ("correcto", "incorrecto") else "correcto"
    return (val, razon)


async def eval_efectividad(
    email_body: str,
    categoria: str,
    plantilla_enviada: str,
    template_content: str = "",
) -> str:
    """Evalúa si la respuesta automática fue adecuada para resolver la consulta.
    Devuelve: 'resuelto' | 'no_resuelto'
    """
    content_desc = template_content or f"Plantilla: {plantilla_enviada}"
    prompt = (
        "Eres un evaluador experto de respuestas automáticas para Tu Trastero "
        "(empresa de self-storage).\n\n"
        "Determina si la respuesta automática enviada fue adecuada para resolver "
        "la consulta del cliente.\n\n"
        f"Categoría identificada: \"{categoria}\"\n"
        f"Respuesta enviada al cliente:\n---\n{content_desc}\n---\n\n"
        "Responde ÚNICAMENTE:\n"
        "- resuelto: la respuesta era adecuada para la consulta\n"
        "- no_resuelto: la respuesta no era adecuada o el cliente no obtendría lo que necesita"
    )
    result = await extract_structured_data(
        text=email_body, prompt=prompt,
        parameters=[{
            "name": "efectividad", "type": "string",
            "description": "resuelto o no_resuelto", "isRequired": True,
        }],
        model="gpt-4o-mini",
    )
    val = result.get("efectividad", "").lower().strip()
    return val if val in ("resuelto", "no_resuelto") else "resuelto"


async def eval_follow_up(
    follow_up_body: str,
    template_content: str,
    categoria: str,
) -> str:
    """Evalúa si el cliente quedó satisfecho a partir de su respuesta al email automático.
    Devuelve: 'resuelto' | 'no_resuelto' | 'escalado'
    """
    prompt = (
        "Eres un evaluador de satisfacción de clientes para Tu Trastero (self-storage).\n\n"
        f"El sistema envió esta respuesta automática al cliente (categoría: {categoria}):\n"
        f"---\n{template_content}\n---\n\n"
        "El cliente ha respondido con el mensaje que recibirás. "
        "Determina si su consulta quedó resuelta o si sigue necesitando ayuda.\n\n"
        "Responde ÚNICAMENTE:\n"
        "- resuelto: el cliente confirma, agradece o no tiene más preguntas sobre el tema\n"
        "- no_resuelto: el cliente insiste, tiene más dudas o no logró lo que necesitaba\n"
        "- escalado: el cliente pide hablar con una persona o muestra frustración clara"
    )
    result = await extract_structured_data(
        text=follow_up_body, prompt=prompt,
        parameters=[{
            "name": "efectividad", "type": "string",
            "description": "resuelto, no_resuelto o escalado", "isRequired": True,
        }],
        model="gpt-4o-mini",
    )
    val = result.get("efectividad", "").lower().strip()
    return val if val in ("resuelto", "no_resuelto", "escalado") else "no_resuelto"
