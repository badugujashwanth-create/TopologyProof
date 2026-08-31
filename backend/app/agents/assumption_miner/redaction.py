"""Secret redaction."""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactedText:
    """Sanitized text result."""
    text: str
    redacted: bool
class Redactor:
    """Redact credential-like assignments."""
    _pattern = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s]+")
    def redact(self, text: str) -> RedactedText:
        """Replace secret values."""
        value = self._pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
        return RedactedText(value, value != text)
