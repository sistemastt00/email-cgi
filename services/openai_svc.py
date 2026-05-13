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
        f"#EJEMPLOS DE CLASIFICACIÓN\n{examples_text}"
    )

    result = await extract_structured_data(
        text=email_body,
        prompt=prompt,
        parameters=[{
            "name": "bot_humano",
            "type": "string",
            "description": "Tu respuesta debe ser únicamente una palabra \"bot\" o \"humano\"",
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
    Clasifica el tipo del correo: Requerimiento, Informativo, Interno o Malicioso.
    examples_clasif: registros de BC_Ejemplos Clasificación
    examples_tipo:   registros de BC_Ejemplos Tipo (campos: Fragmento de Correo, Tipo de correo)
    Devuelve: "Requerimiento" | "Informativo" | "Interno" | "Malicioso"
    """
    examples_clasif_text = json.dumps(examples_clasif, ensure_ascii=False)
    examples_tipo_text   = json.dumps(examples_tipo,   ensure_ascii=False)

    prompt = (
        "Eres un asistente experto en la clasificación de correos para un negocio de self-storage. "
        "Tu principal tarea es analizar e identificar el \"tipo\" de correo electrónico. "
        "Los tipos pueden ser \"Requerimiento\", \"Informativo\",  \"Interno\" o \"Malicioso\"\n\n"
        f"- Requerimiento: en base, primero, al cuerpo y, luego, al asunto del correo electrónico "
        f"de categoría {categoria}, analiza si el emisor solicita o requiere cierta información "
        f"relacionada a la categoría identificada. Además, en base a la categoría {categoria} y a "
        f"los ejemplos de la base de conocimiento {examples_clasif_text}, identifica si brinda "
        "información con el objetivo de solicitar algo referente a la categoría "
        f"{categoria}. Además, analiza si la intención del mensaje es para reclamar algo y espera "
        "una respuesta.  En caso la categoría "
        f"{categoria} sea \"Mis Documentos\", \"Documentos Generales\", \"Claves de Acceso\", "
        "\"Pagar Facturas\", \"Ver Facturas\", \"Renueve Promocion\", \"Cancelar Tu Trastero\",  "
        "\"Notificar Incidencia\" has un análisis más profundo, y determina si el emisor hace una "
        "solicitud, y clasificalo como \"Requerimiento\".\n\n"
        "- Informativo: en base, primero, al cuerpo y, luego, al asunto del correo electrónico de "
        f"categoría {categoria}, analiza si el cuerpo del correo electrónico solo muestra información "
        "y no solicita nada respecto a la categoría. Además, esta categoría debe clasificar los correos "
        "que tengan intensión de vender, ofrecer o mostrar algún producto o servicio.\n\n"
        f"- Interno:  si {from_email} contiene un dominio como @tutrastero.com, @mail-tutrastero.com, "
        "soporte@trasterone.com o emails que incluyan \"tutrastero\" deben ser clasificados como "
        "\"Interno\". Adicional a ello, en esta categoría entran emails de Jotform (por ejemplo, "
        "encuestas de satisfacción), soporte@trasterone.com y similares. \n\n"
        f"--- EJEMPLOS DE TIPOS---\n{examples_tipo_text}\n\n"
        "La salida debe ser una de las siguiente: \"Requerimiento\", \"Informativo\" o  \"Interno\""
    )

    result = await extract_structured_data(
        text=subject + email_body,
        prompt=prompt,
        parameters=[{
            "name": "tipo",
            "type": "string",
            "description": "Requerimiento, Informativo o Interno",
            "isRequired": False,
        }],
        model=model,
    )
    return result.get("tipo", "Informativo")
