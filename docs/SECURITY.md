# Archimedes — Security

---

## Threat Model

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Prompt injection | High | High | 33-pattern detection + sanitization |
| Path traversal | Medium | High | Whitelist-based path validation |
| Credential leak | Medium | Critical | Env-only secrets, .gitignore enforced |
| Unauthorized API access | Medium | High | JWT + API key on all endpoints |
| Code execution escape | Low | Critical | Sandbox isolation (Phase 6: MicroVM) |
| Rate limit abuse | High | Medium | Per-session + per-IP limiting |
| Session hijacking | Low | High | Short-lived JWTs, secure cookies |

---

## Authentication

### JWT

```
Header: Authorization: Bearer <token>
Token TTL: 24h (configurable via JWT_EXPIRY_HOURS)
Algorithm: HS256

Payload:
{
  "sub": "user_id",
  "session_id": "uuid",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### API Key (programmatic access)

```
Header: X-API-Key: <key>
Keys stored hashed (bcrypt) in SQLite.
No plaintext key storage ever.
```

### WebSocket Auth

```
Handshake: ws://host/ws/{session_id}?token=<jwt>
Token validated before connection upgrade.
Disconnect immediately on invalid token.
```

---

## Input Sanitization

### Prompt Injection Defense (33 patterns)

```python
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"disregard all prior",
    r"you are now",
    r"act as (a|an)",
    r"forget your",
    r"system prompt",
    r"jailbreak",
    r"DAN",
    r"developer mode",
    r"override (your|all)",
    r"new instructions",
    r"pretend (you are|to be)",
    r"from now on",
    r"your (true|real) self",
    r"bypass (safety|filters)",
    # + 18 more patterns
]

def check_injection(text: str) -> None:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise SecurityError("Prompt injection attempt detected")
```

---

## Tool Security

### Filesystem Tool

```python
ALLOWED_PATHS = ["/workspace", "/tmp/archimedes"]

def validate_path(path: str) -> str:
    resolved = Path(path).resolve()
    for allowed in ALLOWED_PATHS:
        if str(resolved).startswith(str(Path(allowed).resolve())):
            return str(resolved)
    raise SecurityError(f"Path traversal blocked: {path}")
```

### Bash Tool

```python
BLOCKED_COMMANDS = [
    "rm -rf /", "dd if=", "mkfs", "> /dev/",
    "chmod 777 /", "chown -R root", ":(){ :|:& };:"
]

# Phase 1: subprocess with restricted environment
subprocess.run(
    cmd,
    timeout=30,
    env={"PATH": "/usr/local/bin:/usr/bin", "HOME": "/tmp/sandbox"},
    cwd="/tmp/sandbox",
    capture_output=True,
)

# Phase 6: replace with MicroVM (gVisor or Firecracker)
```

---

## Rate Limiting

```
Per session:  60 requests / minute
Per IP:       120 requests / minute
WebSocket:    10 messages / second per connection
Burst:        2x for 10 seconds
Response:     429 Too Many Requests with Retry-After header
```

---

## Secrets Management

Rules:
1. Never commit .env (enforced by .gitignore)
2. .env.example contains only key names, no values
3. No API keys in source code, ever
4. Rotate immediately if accidentally committed

Pre-commit hook:
```bash
#!/bin/bash
if git diff --cached | grep -E "(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{36})" ; then
    echo "ERROR: Potential secret detected. Commit blocked."
    exit 1
fi
```

---

## Security Headers

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response
```

---

## CORS Config

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # never "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)
```

---

## Incident Response

| Incident | Action |
|----------|--------|
| Credential committed | Revoke immediately in provider dashboard. Rotate. Audit logs. |
| Prompt injection success | Add pattern. Audit affected sessions. |
| Path traversal | Audit accessed files. Patch. Restrict paths further. |
| Rate limit bypass | Block IP. Audit session. Strengthen algorithm. |
