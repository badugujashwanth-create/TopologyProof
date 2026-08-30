"""Run-state, trajectory, and generated-report contracts."""

from itertools import pairwise
from types import MappingProxyType
from typing import cast

from pydantic import Field, field_serializer, field_validator, model_validator

from backend.app.config import ProviderName
from backend.app.schemas.common import (
    AnalysisStage,
    ContractModel,
    ErrorResponse,
    FrozenJsonObject,
    NonBlankText,
    OverallVerdict,
    PreservedNonBlankText,
    RunStatus,
    SafeStorageName,
    TrajectoryAction,
    UtcDatetime,
)

PIPELINE_STAGES = tuple(AnalysisStage)


class AnalysisRun(ContractModel):
    """Describe immutable observable state for one submitted analysis."""

    run_id: SafeStorageName
    status: RunStatus
    provider: ProviderName
    created_at: UtcDatetime
    updated_at: UtcDatetime
    current_stage: AnalysisStage | None = None
    completed_stages: tuple[AnalysisStage, ...] = ()
    stage_timestamps: dict[AnalysisStage, UtcDatetime] = Field(default_factory=dict)
    artifact_refs: tuple[SafeStorageName, ...] = ()
    overall_verdict: OverallVerdict | None = None
    limitations: tuple[NonBlankText, ...] = ()
    error: ErrorResponse | None = None

    @field_validator("stage_timestamps")
    @classmethod
    def freeze_stage_timestamps(
        cls, value: dict[AnalysisStage, UtcDatetime]
    ) -> dict[AnalysisStage, UtcDatetime]:
        """Freeze stage timestamps after their values have been validated."""
        return cast(dict[AnalysisStage, UtcDatetime], MappingProxyType(dict(value)))

    @field_serializer("stage_timestamps")
    def serialize_stage_timestamps(
        self, value: dict[AnalysisStage, UtcDatetime]
    ) -> dict[str, UtcDatetime]:
        """Serialize enum-keyed timestamps with stable wire keys."""
        return {stage.value: timestamp for stage, timestamp in value.items()}

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "AnalysisRun":
        """Require timestamps, stages, status, verdict, and errors to agree."""
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        expected_prefix = PIPELINE_STAGES[: len(self.completed_stages)]
        if self.completed_stages != expected_prefix:
            raise ValueError("completed_stages must be an ordered unique pipeline prefix")
        if set(self.stage_timestamps) != set(self.completed_stages):
            raise ValueError("stage_timestamps must match completed_stages")
        timestamps = tuple(self.stage_timestamps[stage] for stage in self.completed_stages)
        if any(timestamp < self.created_at or timestamp > self.updated_at for timestamp in timestamps):
            raise ValueError("stage timestamps must fall within the run lifetime")
        if any(later < earlier for earlier, later in pairwise(timestamps)):
            raise ValueError("stage timestamps must be monotonic")
        if self.status is RunStatus.QUEUED:
            if self.current_stage is not None or self.completed_stages:
                raise ValueError("queued runs cannot expose stage progress")
        elif self.status is RunStatus.RUNNING:
            if len(self.completed_stages) == len(PIPELINE_STAGES):
                raise ValueError("running runs cannot have every stage completed")
            if self.current_stage is not PIPELINE_STAGES[len(self.completed_stages)]:
                raise ValueError("current_stage must be the next incomplete stage")
        elif self.status is RunStatus.COMPLETED:
            if self.completed_stages != PIPELINE_STAGES:
                raise ValueError("completed runs require every pipeline stage")
            if self.current_stage is not None or self.overall_verdict is None:
                raise ValueError("completed runs require a verdict and no current stage")
            if self.overall_verdict is OverallVerdict.REPRODUCIBLE_TOPOLOGY_SENSITIVE_FAILURE:
                raise ValueError("M1 runs cannot claim a reproducible topology-sensitive failure")
        else:
            if self.error is None:
                raise ValueError("failed runs require an error")
            if len(self.completed_stages) == len(PIPELINE_STAGES):
                raise ValueError("failed runs cannot complete every pipeline stage")
            next_stage = PIPELINE_STAGES[len(self.completed_stages)]
            if self.current_stage is not None and self.current_stage is not next_stage:
                raise ValueError("failed run current_stage must be the next incomplete stage")
        if self.status is not RunStatus.COMPLETED and self.overall_verdict is not None:
            raise ValueError("only completed runs may expose an overall verdict")
        if self.status is not RunStatus.FAILED and self.error is not None:
            raise ValueError("only failed runs may expose an error")
        if len(self.artifact_refs) != len(set(self.artifact_refs)):
            raise ValueError("artifact_refs must be unique")
        return self


class TrajectoryEvent(ContractModel):
    """Describe one append-only, display-safe analysis action."""

    run_id: SafeStorageName
    step: int = Field(gt=0)
    occurred_at: UtcDatetime
    component: NonBlankText
    action: TrajectoryAction
    input_references: tuple[NonBlankText, ...] = ()
    output_reference: NonBlankText | None = None
    summary: NonBlankText
    duration_ms: int | None = Field(default=None, ge=0)
    metadata: FrozenJsonObject = Field(default_factory=dict)


class ReportArtifact(ContractModel):
    """Describe a generated deterministic Markdown report for one run."""

    run_id: SafeStorageName
    filename: SafeStorageName
    content: PreservedNonBlankText
