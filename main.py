"""
main.py — Email CGI Bot
FastAPI + Gmail API + Airtable + Bitrix24 + OpenAI

Arquitectura:
  · Poller en background: lee emails nuevos de cgi@tutrastero.com cada 60 s
  · Webhook POST /webhook: permite disparar cualquier handler manualmente
  · Monitor  GET  /monitor: panel de logs en tiempo real
"""
import asyncio
import collections
import datetime
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

import config
from handlers import (
    clasificacion,
    correo_clasif,
    extraccion_1er,
    extraccion_cadena,
    respuesta_general,
    bot_humano,
)

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("email-cgi")

MAX_HISTORY = 100
_history: collections.deque = collections.deque(maxlen=MAX_HISTORY)


class _MonitorHandler(logging.Handler):
    def emit(self, record):
        _history.append({
            "time":    datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
            "level":   record.levelname,
            "message": self.format(record),
        })


_mh = _MonitorHandler()
_mh.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_mh)

# ─── Poller ───────────────────────────────────────────────────────────────────

async def _poller():
    logger.info(f"📧 Poller iniciado — intervalo {config.POLL_INTERVAL}s")
    while True:
        try:
            await clasificacion.process_new_emails()
        except Exception as exc:
            logger.error(f"Poller error: {exc}", exc_info=True)
        await asyncio.sleep(config.POLL_INTERVAL)

# ─── App ──────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_poller())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Email CGI Bot", lifespan=lifespan)

# ─── Dispatcher de handlers ───────────────────────────────────────────────────

_HANDLERS = {
    "correo_clasificacion":      correo_clasif.run,
    "extraccion_1er_correo":     extraccion_1er.run,
    "extraccion_cadena":         extraccion_cadena.run,
    "respuesta_area_general":    respuesta_general.run,
    "bot_o_humano":              bot_humano.run,
}

# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "bot": "email-cgi", "handlers": list(_HANDLERS)}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "JSON inválido"})

    name = payload.get("name", "")
    args = payload.get("args", {})

    logger.info(f"Webhook recibido: {name} | args={json.dumps(args, ensure_ascii=False)[:200]}")

    fn = _HANDLERS.get(name)
    if fn is None:
        logger.warning(f"Handler desconocido: {name!r}")
        return JSONResponse(
            status_code=400,
            content={"error": f"Handler desconocido: {name}", "disponibles": list(_HANDLERS)},
        )

    try:
        result = await fn(args)
        logger.info(f"Resultado [{name}]: {json.dumps(result, ensure_ascii=False)[:300]}")
        return result
    except Exception as exc:
        logger.error(f"Error en {name}: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/monitor", response_class=HTMLResponse)
async def monitor():
    filas = ""
    for entry in reversed(list(_history)):
        bg = {"ERROR": "#ffebee", "WARNING": "#fff8e1"}.get(entry["level"], "#fafafa")
        color = {"ERROR": "#c62828", "WARNING": "#e65100", "INFO": "#1565c0"}.get(
            entry["level"], "#333"
        )
        msg = entry["message"].replace("<", "&lt;").replace(">", "&gt;")
        filas += (
            f'<tr style="background:{bg}">'
            f'<td class="ts">{entry["time"]}</td>'
            f'<td class="lv" style="color:{color}">{entry["level"]}</td>'
            f'<td class="ms">{msg}</td>'
            f'</tr>'
        )
    if not filas:
        filas = '<tr><td colspan="3" style="text-align:center;color:#aaa;padding:30px">Sin eventos aún — esperando emails…</td></tr>'

    handlers_list = "".join(f"<code>{h}</code>" for h in _HANDLERS)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="5">
<title>Monitor — Email CGI</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:system-ui,sans-serif; background:#f5f7fa; padding:20px; }}
  h1   {{ color:#1a237e; font-size:1.4em; margin-bottom:4px; }}
  .sub {{ color:#666; font-size:.85em; margin-bottom:16px; }}
  .sub code {{ background:#e8eaf6; padding:1px 6px; border-radius:3px; margin:0 2px; }}
  table {{ width:100%; border-collapse:collapse; background:#fff;
           border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,.07); }}
  th  {{ background:#1a237e; color:#fff; padding:8px 12px; text-align:left; font-size:.85em; }}
  .ts {{ white-space:nowrap; width:70px; padding:5px 10px; color:#777; font-size:.82em; }}
  .lv {{ width:70px; padding:5px 8px; font-size:.8em; font-weight:600; }}
  .ms {{ padding:5px 10px; font-family:Consolas,monospace; font-size:.83em; word-break:break-word; }}
  tr:hover td {{ filter:brightness(.97); }}
  .badge {{ background:#2ecc71; color:#fff; padding:2px 10px; border-radius:10px;
            font-size:.75em; margin-left:8px; }}
</style>
</head>
<body>
  <h1>📧 Email CGI Bot <span class="badge">live</span></h1>
  <p class="sub">
    Handlers: {handlers_list} &nbsp;·&nbsp;
    Poller: cada <strong>{config.POLL_INTERVAL}s</strong> &nbsp;·&nbsp;
    Últimas <strong>{MAX_HISTORY}</strong> entradas &nbsp;·&nbsp; refresco 5 s
  </p>
  <table>
    <thead><tr><th>Hora</th><th>Nivel</th><th>Mensaje</th></tr></thead>
    <tbody>{filas}</tbody>
  </table>
</body>
</html>"""
    return html
