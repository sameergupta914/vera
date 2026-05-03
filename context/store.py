"""Thread-safe context storage with versioning."""

import threading
from datetime import datetime
from typing import Optional


class ContextStore:
    """In-memory context storage with version tracking.

    All operations are thread-safe via a single lock.
    Context is stored as: {(scope, context_id): {"version": int, "payload": dict}}
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._contexts: dict[tuple[str, str], dict] = {}
        self._started_at = datetime.utcnow()

    def push_context(self, scope: str, context_id: str, version: int, payload: dict) -> tuple[bool, str, Optional[int]]:
        """Push context atomically. Returns (accepted, reason, current_version).

        - Idempotent: same (scope, context_id, version) is a no-op
        - Higher version replaces lower atomically
        - Lower/equal version (when different exists) returns 409
        """
        key = (scope, context_id)

        with self._lock:
            existing = self._contexts.get(key)

            if existing is None:
                # First time seeing this context
                self._contexts[key] = {"version": version, "payload": payload}
                return True, "accepted", version

            if existing["version"] == version:
                # Idempotent: same version, accept silently
                return True, "accepted", version

            if existing["version"] > version:
                # Stale: we have a newer version
                return False, "stale_version", existing["version"]

            # existing["version"] < version: replace with newer
            self._contexts[key] = {"version": version, "payload": payload}
            return True, "accepted", version

    def get_context(self, scope: str, context_id: str) -> Optional[dict]:
        """Get context payload by scope and ID. Returns None if not found."""
        key = (scope, context_id)
        with self._lock:
            entry = self._contexts.get(key)
            return entry["payload"] if entry else None

    def get_version(self, scope: str, context_id: str) -> Optional[int]:
        """Get current version for a context. Returns None if not found."""
        key = (scope, context_id)
        with self._lock:
            entry = self._contexts.get(key)
            return entry["version"] if entry else None

    def get_all_counts(self) -> dict[str, int]:
        """Get counts of loaded contexts by scope."""
        with self._lock:
            counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
            for (scope, _) in self._contexts.keys():
                if scope in counts:
                    counts[scope] += 1
            return counts

    def get_uptime_seconds(self) -> int:
        """Get bot uptime in seconds."""
        return int((datetime.utcnow() - self._started_at).total_seconds())

    def list_active_triggers(self, now: datetime) -> list[str]:
        """List trigger IDs that are not expired."""
        with self._lock:
            active = []
            for (scope, context_id), entry in self._contexts.items():
                if scope != "trigger":
                    continue
                payload = entry["payload"]
                expires_at = payload.get("expires_at")
                if expires_at:
                    try:
                        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                        if exp > now:
                            active.append(context_id)
                    except ValueError:
                        # Invalid date format, include it anyway
                        active.append(context_id)
                else:
                    active.append(context_id)
            return active

    def get_merchant_by_trigger(self, trigger_id: str) -> Optional[str]:
        """Get merchant_id associated with a trigger."""
        trigger = self.get_context("trigger", trigger_id)
        if trigger:
            return trigger.get("merchant_id")
        return None

    def get_category_by_merchant(self, merchant_id: str) -> Optional[str]:
        """Get category_slug for a merchant."""
        merchant = self.get_context("merchant", merchant_id)
        if merchant:
            return merchant.get("category_slug")
        return None

    def clear(self):
        """Clear all contexts. Used for testing."""
        with self._lock:
            self._contexts.clear()
            self._started_at = datetime.utcnow()
