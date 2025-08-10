"""Google Calendar integration functions: list upcoming events and create events.

Setup Instructions:
1. Create a Google Cloud project and enable Google Calendar API.
2. Create OAuth client credentials (Desktop) and download credentials.json.
3. Place credentials.json in backend/credentials/google/credentials.json (ignored or mount as secret volume).
4. First run will perform OAuth; token.json will be stored alongside credentials.

Environment Variables (optional):
GOOGLE_CALENDAR_CREDENTIALS_PATH - override credentials path.
GOOGLE_CALENDAR_TOKEN_PATH - override token storage path.
GOOGLE_CALENDAR_PRIMARY - calendar ID (default primary).
TIMEZONE - default timezone for event creation (e.g., America/Argentina/Buenos_Aires).

Commands:
!next (alias !events) -> list next events
!addevent <description>; <when> (aliases !newevent !calendaradd) -> parse natural language and create event.

Examples:
!next 5
!events mañana
!addevent Reunión con Juan; mañana 15:00
!addevent Doctor turno; 25 agosto 10am
"""
import os
import logging
import datetime as dt
from typing import Dict, Any, List, Optional

try:  # Optional heavy imports
    import dateparser  # type: ignore
    from google.oauth2.credentials import Credentials  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore
    from googleapiclient.discovery import build  # type: ignore
    from google.auth import exceptions as google_exceptions  # type: ignore
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    import httpx  # type: ignore
    _GC_LIBS_AVAILABLE = True
    _GC_IMPORT_ERROR = None
except Exception as _ge:  # pragma: no cover - import guard
    _GC_LIBS_AVAILABLE = False
    _GC_IMPORT_ERROR = str(_ge)

from functions.base import FunctionBase, bot_function

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_CAL_ID = os.environ.get("GOOGLE_CALENDAR_PRIMARY", 'primary')
DEFAULT_TZ = os.environ.get("TIMEZONE", "UTC")
TOKEN_PATH = os.environ.get("GOOGLE_CALENDAR_TOKEN_PATH", os.path.join(os.path.dirname(__file__), "..", "credentials", "google", "token.json"))
DEVICE_FLOW_ENABLED = os.environ.get("GOOGLE_CALENDAR_ENABLE_DEVICE_FLOW", "true").lower() in ("1","true","yes","on")
_DEVICE_FLOW_STATE: dict = {}


def _env_creds() -> Optional['Credentials']:
    """Build Credentials from environment variables (requires refresh token)."""
def _file_creds() -> Optional['Credentials']:
    """Load credentials from token.json if present."""
    if not _GC_LIBS_AVAILABLE:
        return None

    if not _GC_LIBS_AVAILABLE:
        return None
    client_id = os.environ.get("GOOGLE_CALENDAR_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CALENDAR_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_CALENDAR_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        return None
    return Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )


def _run_interactive_flow() -> Optional['Credentials']:
    """Run an InstalledAppFlow (console or local_server) using client id/secret from env.

    After obtaining credentials, prints (logs) the refresh token so the user can
    copy it into GOOGLE_CALENDAR_REFRESH_TOKEN to avoid repeating the flow.
    """
    if not _GC_LIBS_AVAILABLE:
        logger.error(f"Google Calendar libs no disponibles: {_GC_IMPORT_ERROR}")
        return None
    client_id = os.environ.get("GOOGLE_CALENDAR_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CALENDAR_CLIENT_SECRET")
    if not (client_id and client_secret):
        return None
    oauth_mode = os.environ.get("GOOGLE_CALENDAR_OAUTH_MODE", "console").lower()
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    try:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        if oauth_mode == "local_server":
            creds = flow.run_local_server(port=0)
        else:
            # console (device-friendly / headless) mode
            creds = flow.run_console()
        if creds and creds.refresh_token:
            logger.warning("Google Calendar OAuth completado. Copia este refresh token en tu .env como GOOGLE_CALENDAR_REFRESH_TOKEN=\n%s", creds.refresh_token)
        return creds
    except Exception as e:  # pragma: no cover
        logger.error(f"Interactive OAuth flow failed: {e}")
        return None


def _load_service() -> Optional[Any]:
    if not _GC_LIBS_AVAILABLE:
        logger.warning(f"Google Calendar: dependencias no instaladas ({_GC_IMPORT_ERROR})")
        return None
    creds = _env_creds()
    if not creds:
        # Attempt interactive flow if allowed
        if os.environ.get("GOOGLE_CALENDAR_ALLOW_OAUTH", "true").lower() in ("1","true","yes","on"):
            logger.info("Attempting interactive OAuth flow for Google Calendar (no refresh token present)...")
            creds = _run_interactive_flow()
            # Persist token to file for future reuse
            if creds and creds.refresh_token:
                try:
                    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
                    with open(TOKEN_PATH, 'w') as f:
                        f.write(creds.to_json())
                    logger.info(f"Token guardado en {TOKEN_PATH}")
                except Exception as e:  # pragma: no cover
                    logger.warning(f"No se pudo guardar token: {e}")
        if not creds:
            logger.warning("Google Calendar no configurado (falta refresh token).")
            return None
    try:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except google_exceptions.RefreshError as re:  # pragma: no cover
                logger.error(f"Failed to refresh Google token: {re}. Set a valid GOOGLE_CALENDAR_REFRESH_TOKEN")
                return None
        service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
        return service
    except Exception as e:  # pragma: no cover
        logger.error(f"Failed to init Google Calendar service: {e}")
        return None


def _parse_time(text: str, ref: Optional[dt.datetime] = None) -> Optional[dt.datetime]:
    if not _GC_LIBS_AVAILABLE:
        return None
    settings = {"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False}
    if ref:
        settings["RELATIVE_BASE"] = ref
    try:
        parsed = dateparser.parse(text, settings=settings, languages=['es','en'])  # type: ignore
    except Exception:
        parsed = None
    return parsed


@bot_function("next")
class CalendarListFunction(FunctionBase):
    """List upcoming Google Calendar events with optional natural language date filter."""
    def __init__(self):
        super().__init__(
            name="next",
            description="List upcoming Google Calendar events (supports filter like 'mañana', 'hoy', date)",
            parameters={
                "filter": {"type": "string", "description": "Natural language day filter (hoy, mañana, date)", "required": False},
                "limit": {"type": "integer", "description": "Max events (1-20)", "default": 5}
            },
            command_info={
                "usage": "!next [cantidad|filtro]",
                "examples": ["!next", "!next 10", "!next mañana", "!events hoy"],
                "aliases": ["events", "eventos"],
                "parameter_mapping": {"filter": "first_arg"}
            },
            intent_examples=[
                {"message": "listar próximos eventos", "parameters": {}},
                {"message": "qué eventos tengo mañana", "parameters": {"filter": "mañana"}},
                {"message": "what are my next events", "parameters": {}}
            ]
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        params = self.validate_parameters(**kwargs)
        filter_text = params.get("filter")
        limit = params.get("limit", 5)

        # Interpret first arg: if digits treat as limit; else treat as filter
        if isinstance(filter_text, str) and filter_text.isdigit():
            limit = int(filter_text)
            filter_text = None
        try:
            limit = int(limit)
        except Exception:
            limit = 5
        limit = max(1, min(limit, 20))

        service = _load_service()
        if not service:
            if not _GC_LIBS_AVAILABLE:
                return self.format_error_response("Dependencias Google Calendar no instaladas")
            return self.format_error_response("Google Calendar no configurado")
        now = dt.datetime.utcnow().isoformat() + 'Z'
        try:
            events_result = service.events().list(calendarId=DEFAULT_CAL_ID, timeMin=now, maxResults=50, singleEvents=True, orderBy='startTime').execute()
            events = events_result.get('items', [])
            if not events:
                return self.format_success_response({"events": []}, "No hay eventos próximos")

            # Apply date filter if provided
            if filter_text:
                parsed = _parse_time(filter_text)
                if parsed:
                    target_date = parsed.date()
                    def starts_on(ev):
                        start_raw = ev.get('start', {})
                        dt_val = start_raw.get('dateTime') or start_raw.get('date')
                        if not dt_val:
                            return False
                        if 'T' in dt_val:
                            try:
                                d_part = dt_val.split('T')[0]
                            except Exception:
                                d_part = dt_val[:10]
                        else:
                            d_part = dt_val
                        try:
                            return dt.date.fromisoformat(d_part) == target_date
                        except Exception:
                            return False
                    events = [e for e in events if starts_on(e)]

            events = events[:limit]
            if not events:
                return self.format_success_response({"events": []}, "No hay eventos para ese filtro" if filter_text else "No hay eventos próximos")

            lines = ["📅 Próximos eventos:" + (f" ({filter_text})" if filter_text else "")]
            out_events = []
            for ev in events:
                start = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')
                summary = ev.get('summary', '(sin título)')
                start_disp = start.replace('T', ' ') if start else '?'
                lines.append(f"• {start_disp} - {summary}")
                out_events.append({
                    "id": ev.get('id'),
                    "summary": summary,
                    "start": start,
                    "htmlLink": ev.get('htmlLink')
                })
            return self.format_success_response({"events": out_events, "filter": filter_text, "limit": limit}, "\n".join(lines))
        except Exception as e:
            logger.error(f"Calendar list error: {e}")
            return self.format_error_response(str(e))


@bot_function("addevent")
class CalendarAddEventFunction(FunctionBase):
    """Create a new Google Calendar event.
    Syntax: !addevent <description>; <when>
    """
    def __init__(self):
        super().__init__(
            name="addevent",
            description="Create a Google Calendar event using natural language",
            parameters={
                "text": {"type": "string", "description": "'<summary>; <when>'", "required": True}
            },
            command_info={
                "usage": "!addevent <descripcion>; <cuando>",
                "examples": ["!addevent Reunión; mañana 15:00", "!addevent Doctor; 25 agosto 10am"],
                "aliases": ["newevent", "calendaradd", "agendar"],
                "parameter_mapping": {"text": "join_args"}
            },
            intent_examples=[
                {"message": "agendar reunión mañana 3pm", "parameters": {}},
                {"message": "add calendar event doctor next monday 9am", "parameters": {}}
            ]
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        params = self.validate_parameters(**kwargs)
        text = (params.get("text") or '').strip()
        if ';' not in text:
            return self.format_error_response("Formato inválido. Usa: resumen; cuando")
        summary_part, when_part = [p.strip() for p in text.split(';', 1)]
        if not summary_part or not when_part:
            return self.format_error_response("Falta resumen o fecha")
        ref = dt.datetime.now()
        parsed_dt = _parse_time(when_part, ref=ref)
        if not parsed_dt:
            return self.format_error_response("No pude interpretar la fecha/hora")
        # Assume duration 1 hour
        end_dt = parsed_dt + dt.timedelta(hours=1)
        # Localize naive to timezone by formatting only (Calendar accepts RFC3339 without tz as local?). Prefer UTC.
        start_iso = parsed_dt.isoformat()
        end_iso = end_dt.isoformat()
        service = _load_service()
        if not service:
            if not _GC_LIBS_AVAILABLE:
                return self.format_error_response("Dependencias Google Calendar no instaladas")
            return self.format_error_response("Google Calendar no configurado")
        body = {
            'summary': summary_part,
            'start': {'dateTime': start_iso, 'timeZone': DEFAULT_TZ},
            'end': {'dateTime': end_iso, 'timeZone': DEFAULT_TZ},
        }
        try:
            ev = service.events().insert(calendarId=DEFAULT_CAL_ID, body=body).execute()
            link = ev.get('htmlLink')
            return self.format_success_response({"event": {"id": ev.get('id'), "summary": summary_part, "start": start_iso, "url": link}}, f"✅ Evento creado: {summary_part} ({start_iso})\n{link}")
        except Exception as e:
            logger.error(f"Calendar create error: {e}")
            return self.format_error_response(str(e))


@bot_function("calauth")
class CalendarAuthFunction(FunctionBase):
    """Initiate or complete Google Calendar device authorization flow.

    Usage:
      !calauth          -> inicia el flujo y muestra código e URL
      !calauth poll     -> intenta completar (después de autorizar en el navegador)
    """
    def __init__(self):
        super().__init__(
            name="calauth",
            description="Autenticar Google Calendar (device flow)",
            parameters={
                "action": {"type": "string", "description": "start|poll", "required": False}
            },
            command_info={
                "usage": "!calauth [poll]",
                "examples": ["!calauth", "!calauth poll"],
                "aliases": ["calendar_auth"],
                "parameter_mapping": {"action": "first_arg"}
            },
            intent_examples=[
                {"message": "autenticar calendario", "parameters": {}},
                {"message": "calendar auth", "parameters": {}}
            ]
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        if not _GC_LIBS_AVAILABLE:
            return self.format_error_response(f"Dependencias no disponibles: {_GC_IMPORT_ERROR}")
        if not DEVICE_FLOW_ENABLED:
            return self.format_error_response("Device flow deshabilitado (GOOGLE_CALENDAR_ENABLE_DEVICE_FLOW=false)")
        # If already have creds, short circuit
        existing = _env_creds() or _file_creds()
        if existing and existing.refresh_token:
            return self.format_success_response({"already_authenticated": True}, "✅ Ya está autenticado Google Calendar")

        action = (kwargs.get("action") or "start").lower()
        client_id = os.environ.get("GOOGLE_CALENDAR_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CALENDAR_CLIENT_SECRET")
        if not client_id:
            return self.format_error_response("Falta GOOGLE_CALENDAR_CLIENT_ID")

        if action not in ("start", "poll"):
            action = "start"

        if action == "start":
            try:
                async with httpx.AsyncClient(timeout=10) as client:  # type: ignore
                    data = {
                        'client_id': client_id,
                        'scope': ' '.join(SCOPES)
                    }
                    r = await client.post('https://oauth2.googleapis.com/device/code', data=data)
                    r.raise_for_status()
                    payload = r.json()
                device_code = payload['device_code']
                _DEVICE_FLOW_STATE['device_code'] = device_code
                _DEVICE_FLOW_STATE['interval'] = payload.get('interval', 5)
                _DEVICE_FLOW_STATE['expires_at'] = dt.datetime.utcnow() + dt.timedelta(seconds=payload.get('expires_in', 1800))
                _DEVICE_FLOW_STATE['client_id'] = client_id
                _DEVICE_FLOW_STATE['client_secret'] = client_secret
                msg = (
                    "🔐 Autenticación Google Calendar (Device Flow)\n\n" \
                    f"1. Abrí: {payload['verification_url']}\n" \
                    f"2. Introducí el código: {payload['user_code']}\n" \
                    "3. Luego envía *!calauth poll*\n\n" \
                    "(El código expira en ~30 min)"
                )
                return self.format_success_response({
                    "status": "pending",
                    "verification_url": payload['verification_url'],
                    "user_code": payload['user_code'],
                    "interval": _DEVICE_FLOW_STATE['interval']
                }, msg)
            except Exception as e:  # pragma: no cover
                logger.error(f"Device flow start error: {e}")
                return self.format_error_response(str(e))
        else:  # poll
            if 'device_code' not in _DEVICE_FLOW_STATE:
                return self.format_error_response("Primero ejecuta !calauth para iniciar")
            if dt.datetime.utcnow() > _DEVICE_FLOW_STATE.get('expires_at', dt.datetime.utcnow()):
                _DEVICE_FLOW_STATE.clear()
                return self.format_error_response("Código expirado. Ejecuta !calauth de nuevo")
            try:
                async with httpx.AsyncClient(timeout=10) as client:  # type: ignore
                    data = {
                        'client_id': _DEVICE_FLOW_STATE['client_id'],
                        'device_code': _DEVICE_FLOW_STATE['device_code'],
                        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
                    }
                    # client_secret optional; include if present
                    if _DEVICE_FLOW_STATE.get('client_secret'):
                        data['client_secret'] = _DEVICE_FLOW_STATE['client_secret']
                    r = await client.post('https://oauth2.googleapis.com/token', data=data)
                    if r.status_code == 400:
                        err = r.json().get('error')
                        if err in ('authorization_pending', 'slow_down'):
                            return self.format_success_response({"status": err}, "⏳ Aún pendiente, autoriza y reintenta en unos segundos")
                        if err == 'access_denied':
                            _DEVICE_FLOW_STATE.clear()
                            return self.format_error_response("Acceso denegado. Inicia de nuevo")
                        return self.format_error_response(f"Error: {err}")
                    r.raise_for_status()
                    token_payload = r.json()
                refresh_token = token_payload.get('refresh_token')
                if not refresh_token:
                    return self.format_error_response("No llegó refresh_token (reintenta flujo)")
                # Persist token
                try:
                    from google.oauth2.credentials import Credentials as _Creds  # type: ignore
                    creds = _Creds(
                        token=token_payload.get('access_token'),
                        refresh_token=refresh_token,
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id=_DEVICE_FLOW_STATE['client_id'],
                        client_secret=_DEVICE_FLOW_STATE.get('client_secret'),
                        scopes=SCOPES
                    )
                    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
                    with open(TOKEN_PATH, 'w') as f:
                        f.write(creds.to_json())
                except Exception as e:  # pragma: no cover
                    logger.warning(f"No se pudo guardar token: {e}")
                _DEVICE_FLOW_STATE.clear()
                return self.format_success_response({"authenticated": True}, "✅ Autenticado. Ya podés usar !next")
            except Exception as e:  # pragma: no cover
                logger.error(f"Device flow poll error: {e}")
                return self.format_error_response(str(e))
