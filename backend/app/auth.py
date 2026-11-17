"""Password hashing, session tokens and a simple sign-in throttle. Standard library only."""

import base64
import hashlib
import hmac
import secrets
import threading
import time

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32

SESSION_DAYS = 30

MAX_FAILED_LOGINS = 10
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    """Return 'scrypt$n$r$p$salt$hash' so the parameters can change later without breaking old hashes."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_DKLEN
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Used when the email doesn't exist, so a wrong email takes as long as a wrong password.
DUMMY_HASH = hash_password("not-a-real-password")


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Only a hash of each session token is stored, so a leaked database can't be used to log in."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class LoginThrottle:
    """Blocks an email for a while after too many wrong passwords."""

    def __init__(self, max_failures: int = MAX_FAILED_LOGINS, window_seconds: int = FAILED_LOGIN_WINDOW_SECONDS):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        return [t for t in self._failures.get(key, []) if now - t < self.window]

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            recent = self._recent(key, time.time())
            self._failures[key] = recent
            return len(recent) >= self.max_failures

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = time.time()
            self._failures[key] = self._recent(key, now) + [now]

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)