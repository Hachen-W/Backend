import argparse
import json
import socket

HOST = "127.0.0.1"
PORT = 8000
CHUNK = 4096

SERVICE_NAME = "survey-service"
SERVICE_VERSION = "0.1.0"

REASONS = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}

surveys: dict[int, dict] = {}
next_id = 1


class HttpError(Exception):
    """Ошибка, которая превращается в обычный HTTP-ответ, а не в падение сервера."""

    def __init__(self, status: int, message: str, headers: dict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers or {}


def parse_head(head: bytes) -> tuple[str, str, str, dict[str, str]]:
    """Стартовая строка и заголовки. Имена заголовков приводятся к нижнему регистру."""
    lines = head.decode("iso-8859-1").split("\r\n")

    parts = lines[0].split(" ")
    if len(parts) != 3:
        raise HttpError(400, "malformed request line")
    method, path, version = parts

    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if not sep:
            raise HttpError(400, "malformed header line")
        headers[name.strip().lower()] = value.strip()
    return method, path, version, headers


def json_body(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode()


def handle(method: str, path: str, body: bytes) -> tuple[int, dict[str, str], bytes]:
    """Маршрутизация. Возвращает код ответа, дополнительные заголовки и тело."""
    global next_id

    if path == "/health":
        if method != "GET":
            raise HttpError(405, "method not allowed", {"Allow": "GET"})
        payload = {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}
        return 200, {}, json_body(payload)

    if path == "/surveys":
        if method != "POST":
            raise HttpError(405, "method not allowed", {"Allow": "POST"})
        try:
            data = json.loads(body.decode())
        except (ValueError, UnicodeDecodeError) as exc:
            raise HttpError(400, "body is not valid JSON") from exc
        if not isinstance(data, dict):
            raise HttpError(400, "body must be a JSON object")
        survey = {"id": next_id, **data}
        surveys[next_id] = survey
        next_id += 1
        return 201, {"Location": f"/surveys/{survey['id']}"}, json_body(survey)

    if path.startswith("/surveys/"):
        ident = path[len("/surveys/") :]
        if not ident.isdigit():
            raise HttpError(404, "survey not found")
        if method != "DELETE":
            raise HttpError(405, "method not allowed", {"Allow": "DELETE"})
        if surveys.pop(int(ident), None) is None:
            raise HttpError(404, "survey not found")
        return 204, {}, b""

    raise HttpError(404, "unknown path")


def build_response(status: int, headers: dict[str, str], body: bytes) -> bytes:
    """Собирает ответ вручную: стартовая строка, заголовки, пустая строка, тело."""
    lines = [f"HTTP/1.1 {status} {REASONS[status]}"]
    if status != 204:
        lines.append("Content-Type: application/json; charset=utf-8")
        lines.append(f"Content-Length: {len(body)}")
    lines.extend(f"{name}: {value}" for name, value in headers.items())
    lines.append("Connection: close")
    raw = ("\r\n".join(lines) + "\r\n\r\n").encode()
    return raw if status == 204 else raw + body


def handle_connection(conn: socket.socket, addr: tuple) -> None:
    """Читает один запрос, отвечает и закрывает соединение."""
    buf = b""
    recv_calls = 0
    method, path = "-", "-"
    try:
        while b"\r\n\r\n" not in buf:
            chunk = conn.recv(CHUNK)
            recv_calls += 1
            if not chunk:
                return
            buf += chunk
        head, _, buf = buf.partition(b"\r\n\r\n")

        method, path, _version, headers = parse_head(head)

        length = int(headers.get("content-length", 0))
        while len(buf) < length:
            chunk = conn.recv(CHUNK)
            recv_calls += 1
            if not chunk:
                raise HttpError(400, "incomplete request body")
            buf += chunk
        body = buf[:length]

        status, extra, payload = handle(method, path, body)
    except HttpError as exc:
        status, extra, payload = exc.status, exc.headers, json_body({"error": exc.message})
    except OSError:
        return
    except Exception:
        status, extra, payload = 500, {}, json_body({"error": "internal server error"})

    try:
        conn.sendall(build_response(status, extra, payload))
    except OSError:
        return
    print(f"{addr[0]}:{addr[1]} {method} {path} -> {status}, recv={recv_calls}", flush=True)


def serve(host: str = HOST, port: int = PORT) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen()
        print(f"sequential server on http://{host}:{port}", flush=True)
        while True:
            conn, addr = srv.accept()
            with conn:
                handle_connection(conn, addr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="однопоточный сервер на сокетах")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    try:
        serve(args.host, args.port)
    except KeyboardInterrupt:
        print("stopped")
