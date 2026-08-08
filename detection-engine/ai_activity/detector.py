"""Classify processes into AI apps, roles, and tool classes."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from ai_activity.catalog import (
    AI_APP_ROOTS,
    AI_CMDLINE_MARKERS,
    AI_CLOUD_DOMAIN_MARKERS,
    AI_HELPER_NAME_MARKERS,
    ROLE_EXTENSION_HOST,
    ROLE_HELPER,
    ROLE_PTY_HOST,
    ROLE_RENDERER,
    ROLE_ROOT,
    ROLE_SHELL,
    ROLE_TERMINAL,
    ROLE_TOOL,
    ROLE_UNKNOWN,
    SECRET_PATH_MARKERS,
    SHELL_BASENAMES,
    TOOL_BASENAMES,
    TOOL_OTHER,
    TOOL_SHELL,
)

_IP_RE = re.compile(
    r"^(?:\d{1,3}\.){3}\d{1,3}$|^\[?[0-9a-fA-F:]+\]?$"
)


@dataclass(frozen=True)
class ProcessClassification:
    is_ai_root: bool
    app_name: str | None
    role: str
    tool_class: str | None
    basename: str


def basename_of(name: str, executable: str = "") -> str:
    raw = (name or "").strip() or (executable or "").strip()
    if not raw:
        return ""
    base = os.path.basename(raw.replace("\\", "/"))
    # Strip .exe on Windows-style names
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return base


def normalize_comm(name: str) -> str:
    return basename_of(name).lower()


def _payload_fields(payload: dict[str, Any]) -> tuple[str, str, str]:
    comm = str(payload.get("comm") or payload.get("process_name") or "").strip()
    executable = str(
        payload.get("executable") or payload.get("image") or payload.get("path") or ""
    ).strip()
    cmdline = str(payload.get("cmdline") or payload.get("command_line") or "").strip()
    return comm, executable, cmdline


def classify_process(
    *,
    name: str = "",
    executable: str = "",
    cmdline: str = "",
    parent_is_ai: bool = False,
) -> ProcessClassification:
    """Classify a process for AI session membership and role."""
    base = normalize_comm(name) or normalize_comm(executable)
    cmdline_l = (cmdline or "").lower()
    name_l = (name or "").lower()

    # Explicit AI root by basename
    app = AI_APP_ROOTS.get(base)
    if app:
        return ProcessClassification(
            is_ai_root=True,
            app_name=app,
            role=ROLE_ROOT,
            tool_class=None,
            basename=base,
        )

    # Helper / Electron role detection (not roots)
    role = _role_from_name_cmdline(name_l, cmdline_l, base)
    if role in (ROLE_RENDERER, ROLE_EXTENSION_HOST, ROLE_PTY_HOST, ROLE_HELPER, ROLE_TERMINAL):
        # Helpers alone don't open sessions; they attach when parent is AI.
        return ProcessClassification(
            is_ai_root=False,
            app_name=_app_from_helper(name_l, cmdline_l),
            role=role,
            tool_class=None,
            basename=base,
        )

    # Cmdline suggests AI extension host under VS Code / Cursor
    if any(m in cmdline_l for m in AI_CMDLINE_MARKERS) and (
        "helper" in name_l or "extension" in cmdline_l or parent_is_ai
    ):
        return ProcessClassification(
            is_ai_root=False,
            app_name=_app_from_helper(name_l, cmdline_l),
            role=ROLE_EXTENSION_HOST if "extension" in cmdline_l else ROLE_HELPER,
            tool_class=None,
            basename=base,
        )

    tool = TOOL_BASENAMES.get(base)
    if tool == TOOL_SHELL or base in SHELL_BASENAMES:
        return ProcessClassification(
            is_ai_root=False,
            app_name=None,
            role=ROLE_SHELL,
            tool_class=TOOL_SHELL,
            basename=base,
        )
    if tool:
        return ProcessClassification(
            is_ai_root=False,
            app_name=None,
            role=ROLE_TOOL,
            tool_class=tool,
            basename=base,
        )

    if parent_is_ai:
        return ProcessClassification(
            is_ai_root=False,
            app_name=None,
            role=ROLE_UNKNOWN,
            tool_class=TOOL_OTHER,
            basename=base,
        )

    return ProcessClassification(
        is_ai_root=False,
        app_name=None,
        role=ROLE_UNKNOWN,
        tool_class=None,
        basename=base,
    )


def classify_from_payload(
    payload: dict[str, Any], *, parent_is_ai: bool = False
) -> ProcessClassification:
    comm, executable, cmdline = _payload_fields(payload)
    return classify_process(
        name=comm,
        executable=executable,
        cmdline=cmdline,
        parent_is_ai=parent_is_ai,
    )


def _role_from_name_cmdline(name_l: str, cmdline_l: str, base: str) -> str:
    if "renderer" in name_l or "--type=renderer" in cmdline_l:
        return ROLE_RENDERER
    if "ptyhost" in name_l.replace(" ", "") or "pty host" in name_l or "ptyhost" in cmdline_l.replace(" ", ""):
        return ROLE_PTY_HOST
    if "extension-host" in cmdline_l or "extensionhost" in cmdline_l.replace(" ", ""):
        return ROLE_EXTENSION_HOST
    if "plugin" in name_l and "helper" in name_l:
        return ROLE_EXTENSION_HOST
    if "terminal" in name_l and "helper" not in name_l:
        return ROLE_TERMINAL
    if any(name_l.startswith(m) or name_l == m for m in AI_HELPER_NAME_MARKERS):
        if "gpu" in name_l:
            return ROLE_HELPER
        return ROLE_HELPER
    if "helper" in name_l and any(x in name_l for x in ("cursor", "code", "windsurf", "claude")):
        return ROLE_HELPER
    return ROLE_UNKNOWN


def _app_from_helper(name_l: str, cmdline_l: str) -> str | None:
    blob = f"{name_l} {cmdline_l}"
    if "cursor" in blob:
        return "cursor"
    if "windsurf" in blob:
        return "windsurf"
    if "claude" in blob or "anthropic" in blob:
        return "claude"
    if "code" in blob or "copilot" in blob or "vscode" in blob:
        return "vscode"
    if "continue" in blob:
        return "continue"
    if "cline" in blob:
        return "cline"
    return None


def extract_secret_paths(cmdline: str) -> list[str]:
    """Return cmdline tokens/substrings that look like secret paths."""
    if not cmdline:
        return []
    found: list[str] = []
    lower = cmdline.lower()
    for marker in SECRET_PATH_MARKERS:
        if marker.lower() in lower:
            # Prefer the concrete token containing the marker
            for tok in cmdline.split():
                if marker.lower() in tok.lower() and tok not in found:
                    found.append(tok)
            if not any(marker.lower() in f.lower() for f in found):
                found.append(marker)
    return found


def extract_git_repo(cmdline: str) -> str | None:
    parts = cmdline.split()
    for i, p in enumerate(parts):
        if p in ("clone", "remote") and i + 1 < len(parts):
            cand = parts[i + 1]
            if "://" in cand or cand.endswith(".git") or "github.com" in cand or "gitlab.com" in cand:
                return cand
        if p.startswith("git@") or ".git" in p:
            return p
    return None


def extract_docker_activity(cmdline: str) -> str | None:
    lower = cmdline.lower()
    if not lower:
        return None
    for action in ("build", "run", "push", "pull", "compose", "exec"):
        if f" {action}" in f" {lower}" or lower.startswith(action):
            return f"docker {action}"
    return "docker"


def extract_k8s_activity(cmdline: str) -> str | None:
    lower = cmdline.lower()
    if not lower:
        return None
    for action in ("apply", "delete", "create", "get", "exec", "logs", "port-forward"):
        if f" {action}" in f" {lower}" or lower.startswith(action):
            return f"kubectl {action}"
    return "kubectl"


def extract_cloud_activity(cmdline: str, tool_class: str | None) -> str | None:
    if tool_class == "aws":
        parts = cmdline.split()
        # aws <service> <verb>
        if len(parts) >= 3:
            return f"aws {' '.join(parts[1:3])}"
        return "aws"
    if tool_class == "ssh":
        return "ssh"
    return None


def domain_from_addr(addr: str) -> str:
    """Best-effort domain/host from remote_addr (IP or hostname)."""
    raw = (addr or "").strip().lower()
    if not raw:
        return ""
    # Strip brackets for IPv6
    if raw.startswith("[") and "]" in raw:
        raw = raw[1 : raw.index("]")]
    # Drop port if host:port and not IPv6
    if raw.count(":") == 1 and not raw.startswith("["):
        host, _, maybe_port = raw.partition(":")
        if maybe_port.isdigit():
            raw = host
    return raw


def is_notable_domain(domain: str) -> bool:
    d = (domain or "").lower()
    if not d or _IP_RE.match(d):
        return False
    return any(m in d for m in AI_CLOUD_DOMAIN_MARKERS) or "." in d


def is_private_ip(addr: str) -> bool:
    host = domain_from_addr(addr)
    if not host:
        return True
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    if host.startswith("10.") or host.startswith("192.168.") or host.startswith("172."):
        # coarse private check for 172.16–31
        if host.startswith("172."):
            try:
                second = int(host.split(".")[1])
                return 16 <= second <= 31
            except (IndexError, ValueError):
                return False
        return True
    return False
