"""Shared immutable primitives and enumerations for analysis contracts."""

from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import StrEnum
from re import compile as compile_pattern
from types import MappingProxyType
from typing import Annotated, cast

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    PlainSerializer,
)

SAFE_STORAGE_NAME_PATTERN = compile_pattern(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
WINDOWS_RESERVED_STORAGE_STEMS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)


def _strip_non_blank(value: object) -> str:
    """Return stripped text or reject values without visible characters."""
    if not isinstance(value, str):
        # Pydantic converts ValueError, while TypeError escapes model validation.
        raise ValueError("must be a string")  # noqa: TRY004
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


def _preserve_non_blank(value: object) -> str:
    """Return source text unchanged after rejecting blank or non-string values."""
    if not isinstance(value, str):
        # Pydantic converts ValueError, while TypeError escapes model validation.
        raise ValueError("must be a string")  # noqa: TRY004
    if not value.strip():
        raise ValueError("must not be blank")
    return value


def _safe_storage_name(value: object) -> str:
    """Return a storage-safe identifier with no path or control characters."""
    normalized = _strip_non_blank(value)
    if normalized != value or normalized in {".", ".."}:
        raise ValueError("must not contain surrounding whitespace or traversal segments")
    if SAFE_STORAGE_NAME_PATTERN.fullmatch(normalized) is None:
        raise ValueError("must contain only ASCII letters, digits, dots, hyphens, or underscores")
    if normalized.endswith("."):
        raise ValueError("must not end with a dot")
    if normalized.partition(".")[0].upper() in WINDOWS_RESERVED_STORAGE_STEMS:
        raise ValueError("must not use a reserved Windows device name")
    return normalized


def _require_utc(value: datetime) -> datetime:
    """Require timezone-aware timestamps with a zero UTC offset."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value


def _freeze_json_value(value: JsonValue) -> JsonValue:
    """Recursively freeze a Pydantic-validated JSON value."""
    if isinstance(value, dict):
        frozen = MappingProxyType({key: _freeze_json_value(item) for key, item in value.items()})
        return cast(JsonValue, frozen)
    if isinstance(value, list):
        return cast(JsonValue, tuple(_freeze_json_value(item) for item in value))
    return value


def _thaw_json_value(value: object) -> JsonValue:
    """Convert frozen JSON containers back to serializer-native containers."""
    if isinstance(value, Mapping):
        return {str(key): _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return cast(JsonValue, value)


def _serialize_json_object(value: object) -> dict[str, JsonValue]:
    """Serialize a frozen top-level JSON object as a plain dictionary."""
    thawed = _thaw_json_value(value)
    if not isinstance(thawed, dict):
        raise TypeError("JSON object serializer received a non-object value")
    return thawed


NonBlankText = Annotated[str, BeforeValidator(_strip_non_blank)]
PreservedNonBlankText = Annotated[str, BeforeValidator(_preserve_non_blank)]
SafeStorageName = Annotated[str, BeforeValidator(_safe_storage_name)]
UtcDatetime = Annotated[datetime, AfterValidator(_require_utc)]
FrozenJsonObject = Annotated[
    dict[str, JsonValue],
    AfterValidator(_freeze_json_value),
    PlainSerializer(_serialize_json_object, return_type=dict[str, JsonValue]),
]
Confidence = Annotated[float, Field(ge=0, le=1)]


class ContractModel(BaseModel):
    """Provide strict ownership boundaries for immutable wire contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TopologyDimension(StrEnum):
    """Name a supported deployment-topology axis."""

    REPLICA_COUNT = "replica_count"
    REQUEST_ROUTING = "request_routing"
    RESTART_RECOVERY = "restart_recovery"
    CONCURRENCY = "concurrency"
    STATE_LOCALITY = "state_locality"


class Severity(StrEnum):
    """Classify the potential impact of a supported finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingVerdict(StrEnum):
    """State the finding-level evidence outcome."""

    HIGH_RISK = "high-risk"
    REVIEW_REQUIRED = "review-required"
    NO_TESTED_FAILURE = "no-tested-failure"


class OverallVerdict(StrEnum):
    """State the aggregate result rendered for an analysis."""

    TOPOLOGY_SENSITIVE_CORRECTNESS_RISK = "topology-sensitive-correctness-risk"
    REPRODUCIBLE_TOPOLOGY_SENSITIVE_FAILURE = "reproducible-topology-sensitive-failure"
    REVIEW_REQUIRED = "review-required"
    NO_TESTED_TOPOLOGY_FAILURE = "no-tested-topology-failure"


class RunStatus(StrEnum):
    """Represent the lifecycle state of an analysis run."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisStage(StrEnum):
    """Name one externally observable analysis pipeline stage."""

    REPOSITORY_LOADED = "repository_loaded"
    DIFF_PARSED = "diff_parsed"
    CONTEXT_EXPANDED = "context_expanded"
    STATIC_ANALYSIS_COMPLETED = "static_analysis_completed"
    ASSUMPTION_MINING_COMPLETED = "assumption_mining_completed"
    FINDING_SYNTHESIS_COMPLETED = "finding_synthesis_completed"
    VERIFICATION_RECOMMENDATION_COMPLETED = "verification_recommendation_completed"
    REPORT_GENERATED = "report_generated"


class TrajectoryAction(StrEnum):
    """Name a display-safe action recorded in an analysis trajectory."""

    REPOSITORY_LOADED = "repository_loaded"
    DIFF_PARSED = "diff_parsed"
    CHANGED_SYMBOL_DETECTED = "changed_symbol_detected"
    CONTEXT_EXPANDED = "context_expanded"
    STATIC_SIGNAL_CREATED = "static_signal_created"
    HYPOTHESIS_CREATED = "hypothesis_created"
    TOPOLOGY_DIMENSION_ASSIGNED = "topology_dimension_assigned"
    VERIFICATION_PROPOSED = "verification_proposed"
    TOOL_RESULT_OBSERVED = "tool_result_observed"
    HYPOTHESIS_UPDATED = "hypothesis_updated"
    FINDING_CREATED = "finding_created"
    REPORT_GENERATED = "report_generated"


class ErrorResponse(ContractModel):
    """Describe a safe structured error returned across API boundaries."""

    code: NonBlankText
    message: NonBlankText
    field: NonBlankText | None = None
    detail: FrozenJsonObject | None = None
