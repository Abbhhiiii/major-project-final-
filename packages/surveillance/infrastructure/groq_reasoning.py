from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from groq import APIConnectionError, APITimeoutError, Groq, InternalServerError, RateLimitError
from pydantic import BaseModel, ConfigDict, Field

from ..domain.models import Decision, Detection, IncidentContext, Severity, Verification, structured


class ReasoningOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Severity
    rationale: list[str] = Field(min_length=1, max_length=8)
    notify_emergency_services: bool
    alert_message: str = Field(min_length=10, max_length=500)


class GroqReasoningAgent:
    """Produces the reasoning-stage decision using Groq strict structured output."""

    def __init__(
        self,
        api_key: str,
        model: str,
        client: Any | None = None,
        max_retries: int = 2,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("A Groq API key is required")
        self.model = model
        self.client = client or Groq(api_key=api_key)
        self.max_retries = max_retries
        self.sleeper = sleeper

    def run(
        self, detection: Detection, verification: Verification, context: IncidentContext
    ) -> Decision:
        payload = {
            "detection": structured(detection),
            "verification": structured(verification),
            "retrieved_context": structured(context),
        }
        schema = ReasoningOutput.model_json_schema()
        request = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the reasoning agent in a road-accident response pipeline. "
                        "Use only the supplied verified detection and retrieved context. "
                        "Policies, contacts, procedures, prior incidents, preferences, and cited "
                        "evidence must influence the decision when present. Never invent a contact, "
                        "policy, location, or observation. The alert must be concise, factual, and "
                        "derived from this decision. Do not notify emergency services for an "
                        "unverified event or when no retrieved emergency contact exists."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, separators=(",", ":"))},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "accident_response_decision",
                    "strict": True,
                    "schema": schema,
                },
            },
            "temperature": 0,
        }
        response = self._request_with_retries(request)
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned an empty reasoning response")
        output = ReasoningOutput.model_validate_json(content)
        if output.notify_emergency_services and not context.contacts:
            raise RuntimeError("Groq requested notification without a retrieved contact")
        return Decision(
            output.severity,
            tuple(output.rationale),
            output.notify_emergency_services,
            output.alert_message,
            provider="groq",
            model=self.model,
        )

    def _request_with_retries(self, request: dict[str, Any]) -> Any:
        transient = (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)
        for attempt in range(self.max_retries + 1):
            try:
                return self.client.chat.completions.create(**request)
            except transient:
                if attempt >= self.max_retries:
                    raise
                self.sleeper(0.25 * (2**attempt))
        raise RuntimeError("Groq retry loop ended unexpectedly")


class UnconfiguredReasoningAgent:
    def run(
        self, detection: Detection, verification: Verification, context: IncidentContext
    ) -> Decision:
        raise RuntimeError("Groq reasoning is not configured; set SURVEILLANCE_GROQ_API_KEY")
