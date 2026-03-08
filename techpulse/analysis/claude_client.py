from __future__ import annotations
"""Anthropic SDK wrapper with retry logic and token tracking."""
import time
import uuid
from datetime import datetime, timezone

import anthropic
from sqlalchemy import text

from techpulse.config.settings import settings
from techpulse.database.connection import get_db
from techpulse.utils.logger import get_logger

logger = get_logger("analysis.claude")

MODEL = "claude-sonnet-4-6"
MAX_RETRIES = 3
RETRY_DELAY = 5


class ClaudeClient:
    def __init__(self):
        if not settings.has_anthropic():
            logger.warning("Anthropic API key not configured")
            self._client = None
            return
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def is_available(self) -> bool:
        return self._client is not None

    def complete(
        self,
        prompt: str,
        system: str = "",
        job_type: str = "general",
        max_tokens: int = 4096,
    ) -> str | None:
        if not self._client:
            return None

        batch_id = str(uuid.uuid4())
        self._start_batch(batch_id, job_type)

        for attempt in range(MAX_RETRIES):
            try:
                messages = [{"role": "user", "content": prompt}]
                kwargs = {
                    "model": MODEL,
                    "max_tokens": max_tokens,
                    "messages": messages,
                }
                if system:
                    kwargs["system"] = system

                response = self._client.messages.create(**kwargs)
                content = response.content[0].text

                self._complete_batch(
                    batch_id,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )
                return content

            except anthropic.RateLimitError:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Rate limited, waiting {RETRY_DELAY * (attempt + 1)}s...")
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    self._fail_batch(batch_id, "Rate limit exceeded")
                    return None
            except anthropic.APIError as e:
                self._fail_batch(batch_id, str(e))
                logger.error(f"Claude API error: {e}")
                return None

        return None

    def _start_batch(self, batch_id: str, job_type: str):
        with get_db() as conn:
            conn.execute(text("""
                INSERT INTO analysis_batches (id, job_type, status, started_at)
                VALUES (:id, :job_type, 'running', :started_at)
            """), {
                "id": batch_id,
                "job_type": job_type,
                "started_at": datetime.now(timezone.utc).isoformat(),
            })
            conn.commit()

    def _complete_batch(self, batch_id: str, input_tokens: int, output_tokens: int):
        with get_db() as conn:
            conn.execute(text("""
                UPDATE analysis_batches
                SET status='complete', input_tokens=:inp, output_tokens=:out,
                    completed_at=:now
                WHERE id=:id
            """), {
                "id": batch_id,
                "inp": input_tokens,
                "out": output_tokens,
                "now": datetime.now(timezone.utc).isoformat(),
            })
            conn.commit()

    def _fail_batch(self, batch_id: str, error: str):
        with get_db() as conn:
            conn.execute(text("""
                UPDATE analysis_batches
                SET status='failed', error_message=:err, completed_at=:now
                WHERE id=:id
            """), {
                "id": batch_id,
                "err": error,
                "now": datetime.now(timezone.utc).isoformat(),
            })
            conn.commit()


# Singleton
_client: ClaudeClient | None = None


def get_claude() -> ClaudeClient:
    global _client
    if _client is None:
        _client = ClaudeClient()
    return _client
