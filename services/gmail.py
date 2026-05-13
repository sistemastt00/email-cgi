"""
services/gmail.py — Wrapper asíncrono sobre la Gmail API (google-api-python-client).

Las llamadas al SDK de Google son síncronas; las exponemos como async
ejecutándolas en un hilo con asyncio.to_thread() para no bloquear el event loop.
"""
import asyncio
import base64
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders as email_encoders

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import config

_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


# ─── Autenticación ────────────────────────────────────────────────────────────

def _build_service():
    """Crea y devuelve un servicio Gmail autenticado (refresca el token si hace falta)."""
    creds = Credentials(
        token=None,
        refresh_token=config.GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.GMAIL_CLIENT_ID,
        client_secret=config.GMAIL_CLIENT_SECRET,
        scopes=_SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _parse_from(from_header: str) -> tuple[str, str]:
    """Devuelve (nombre, email) a partir de 'Nombre <email>' o 'email'."""
    m = re.match(r'^"?([^"<]*)"?\s*<([^>]+)>', from_header.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", from_header.strip()


def _extract_body(payload: dict, mime_type: str) -> str:
    """Extrae recursivamente el cuerpo con el mime_type indicado."""
    if payload.get("mimeType") == mime_type:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = _extract_body(part, mime_type)
        if result:
            return result
    return ""


def _parse_message(msg: dict) -> dict:
    """Convierte un mensaje raw de Gmail en un dict limpio."""
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    from_name, from_email = _parse_from(headers.get("From", ""))
    payload = msg.get("payload", {})
    return {
        "id":           msg["id"],
        "threadId":     msg["threadId"],
        "subject":      headers.get("Subject", ""),
        "fromName":     from_name,
        "fromEmail":    from_email,
        "headers":      headers,
        "fullTextBody": _extract_body(payload, "text/plain"),
        "htmlBody":     _extract_body(payload, "text/html"),
        "snippet":      msg.get("snippet", ""),
    }


# ─── Funciones síncronas (se ejecutan en hilo) ────────────────────────────────

def _list_unread_sync() -> list[dict]:
    svc = _build_service()
    res = svc.users().messages().list(
        userId="me", q="is:unread in:inbox", maxResults=10
    ).execute()
    return res.get("messages", [])   # [{id, threadId}, ...]


def _get_email_sync(message_id: str) -> dict:
    svc = _build_service()
    msg = svc.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    return _parse_message(msg)


def _get_attachments_sync(message_id: str) -> list[dict]:
    svc = _build_service()
    msg = svc.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    attachments = []

    def _walk(payload):
        filename = payload.get("filename", "")
        att_id   = payload.get("body", {}).get("attachmentId")
        if filename and att_id:
            att = svc.users().messages().attachments().get(
                userId="me", messageId=message_id, id=att_id
            ).execute()
            attachments.append({
                "filename": filename,
                "mimeType": payload.get("mimeType", "application/octet-stream"),
                "data":     att.get("data", ""),   # base64url
            })
        for part in payload.get("parts", []):
            _walk(part)

    _walk(msg.get("payload", {}))
    return attachments


def _send_email_sync(
    to: list[str],
    subject: str,
    body: str,
    body_type: str = "html",        # "html" | "plain"
    attachments: list[dict] = None,
    bcc: list[str] = None,
) -> dict:
    """Envía un email y devuelve {threadId, messageId}."""
    svc = _build_service()

    if attachments:
        msg = MIMEMultipart("mixed")
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(body, body_type, "utf-8"))
        msg.attach(alt)
        for att in attachments:
            data = base64.urlsafe_b64decode(att["data"] + "==")
            part = MIMEBase("application", "octet-stream")
            part.set_payload(data)
            email_encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition", f'attachment; filename="{att["filename"]}"'
            )
            msg.attach(part)
    else:
        msg = MIMEText(body, body_type, "utf-8")

    msg["To"]      = ", ".join(to)
    msg["Subject"] = subject
    if bcc:
        msg["Bcc"] = ", ".join(bcc)

    raw    = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = svc.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    return {"threadId": result.get("threadId", ""), "messageId": result.get("id", "")}


def _mark_as_read_sync(message_id: str):
    svc = _build_service()
    svc.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


# ─── API pública asíncrona ────────────────────────────────────────────────────

async def list_unread_emails() -> list[dict]:
    """Devuelve lista de {id, threadId} de emails no leídos en Bandeja de entrada."""
    return await asyncio.to_thread(_list_unread_sync)


async def get_email(message_id: str) -> dict:
    """Devuelve el email completo parseado."""
    return await asyncio.to_thread(_get_email_sync, message_id)


async def get_attachments(message_id: str) -> list[dict]:
    """Devuelve lista de adjuntos [{filename, mimeType, data (base64url)}]."""
    return await asyncio.to_thread(_get_attachments_sync, message_id)


async def send_email(
    to: list[str],
    subject: str,
    body: str,
    body_type: str = "html",
    attachments: list[dict] = None,
    bcc: list[str] = None,
) -> dict:
    """Envía un email. Devuelve {threadId, messageId}."""
    return await asyncio.to_thread(_send_email_sync, to, subject, body, body_type, attachments, bcc)


async def mark_as_read(message_id: str):
    """Marca un email como leído."""
    await asyncio.to_thread(_mark_as_read_sync, message_id)
