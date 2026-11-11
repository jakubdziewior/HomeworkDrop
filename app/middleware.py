import json

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings


class _BodyTooLarge(HTTPException):
    # Podklasa HTTPException: FastAPI przepuszcza ją przy parsowaniu body
    # (inne wyjątki zamienia na 400), a ExceptionMiddleware zwraca 413.
    def __init__(self) -> None:
        super().__init__(status_code=413, detail=BodySizeLimitMiddleware._too_large_msg())


class BodySizeLimitMiddleware:
    """
    Twardy limit rozmiaru treści żądania (ochrona przed DoS / wyczerpaniem dysku).

    Starlette zapisuje przesyłane pliki na dysk przed wywołaniem endpointu, bez
    żadnego limitu, dlatego rozmiar musi być kontrolowany już na poziomie strumienia ASGI:
    - żądania z nagłówkiem Content-Length ponad limit są odrzucane od razu,
    - przy braku/fałszywym nagłówku liczone są faktycznie odebrane bajty.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = settings.max_request_body_bytes

        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    await self._reject(send, 400, "Nieprawidłowy nagłówek Content-Length.")
                    return
                if declared > limit:
                    await self._reject(send, 413, self._too_large_msg())
                    return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _BodyTooLarge()
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not response_started:
                await self._reject(send, 413, self._too_large_msg())

    @staticmethod
    def _too_large_msg() -> str:
        return f"Przesyłany plik jest za duży. Maksymalny rozmiar to {settings.MAX_UPLOAD_SIZE_MB} MB."

    @staticmethod
    async def _reject(send: Send, status: int, detail: str) -> None:
        body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
                (b"connection", b"close"),
            ],
        })
        await send({"type": "http.response.body", "body": body})
