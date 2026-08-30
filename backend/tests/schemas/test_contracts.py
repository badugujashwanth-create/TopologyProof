"""Contract tests for strict TopologyProof analysis schemas."""

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import cast

import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.schemas import (
    AnalysisRequest,
    AnalysisRun,
    AnalysisStage,
    AssumptionHypothesis,
    ChangedPath,
    ChangedSymbol,
    ContextItem,
    DiffArtifact,
    DiffSummary,
    ErrorResponse,
    EvidenceLocation,
    Finding,
    FindingList,
    FindingVerdict,
    OverallVerdict,
    ProviderName,
    ReportArtifact,
    RepositorySnapshot,
    RunStatus,
    Severity,
    StaticSignal,
    TopologyDimension,
    TrajectoryAction,
    TrajectoryEvent,
    VerificationRecommendation,
)

COMMIT_ID = "a" * 40
EVENT_TIME = datetime(2026, 8, 30, tzinfo=UTC)
EARLIER_EVENT_TIME = datetime(2026, 8, 29, tzinfo=UTC)


@pytest.fixture
def evidence_location() -> EvidenceLocation:
    """Create candidate-commit evidence valid for dependent contracts."""
    return EvidenceLocation(
        path=PurePosixPath("src/webhook.py"),
        line=12,
        line_end=14,
        symbol="handle_webhook",
        commit_id=COMMIT_ID,
        excerpt="    seen_events.add(event_id)\n",
    )


@pytest.fixture
def valid_finding_data(evidence_location: EvidenceLocation) -> dict[str, object]:
    """Create a complete serializable finding payload."""
    return {
        "finding_id": "finding-1",
        "title": "Process-local webhook deduplication",
        "category": TopologyDimension.STATE_LOCALITY,
        "severity": Severity.HIGH,
        "confidence": 0.8,
        "deployment_assumption": "Equivalent deliveries share one process-local set.",
        "topology_dimensions": (TopologyDimension.REPLICA_COUNT, TopologyDimension.STATE_LOCALITY),
        "evidence": (evidence_location,),
        "correctness_property": "An event produces at most one durable side effect.",
        "predicted_failure": "Duplicate side effects occur across workers.",
        "verification_recommendation": {
            "worth_running": True,
            "summary": "Route duplicate deliveries to separate workers.",
            "topology_dimensions": (TopologyDimension.REPLICA_COUNT,),
            "property_assertion": "The durable side-effect count remains at most one.",
        },
        "verdict": FindingVerdict.HIGH_RISK,
    }


@pytest.fixture
def valid_hypothesis_data(evidence_location: EvidenceLocation) -> dict[str, object]:
    """Create a complete serializable hypothesis payload."""
    return {
        "hypothesis_id": "hypothesis-1",
        "engineering_summary": "Local state is used for deduplication.",
        "correctness_property": "One event produces one side effect.",
        "deployment_assumption": "All deliveries share local state.",
        "predicted_failure": "Duplicates occur across workers.",
        "topology_dimensions": (TopologyDimension.STATE_LOCALITY,),
        "evidence": (evidence_location,),
        "confidence": 0.5,
        "recommendation_summary": "Exercise multiple workers.",
    }


def completed_run_payload() -> dict[str, object]:
    """Create a truthful completed-run payload for lifecycle mutations."""
    all_stages = tuple(AnalysisStage)
    return {
        "run_id": "run-1",
        "status": RunStatus.COMPLETED,
        "provider": ProviderName.OFFLINE,
        "created_at": EARLIER_EVENT_TIME,
        "updated_at": EVENT_TIME,
        "completed_stages": all_stages,
        "stage_timestamps": {stage: EVENT_TIME for stage in all_stages},
        "overall_verdict": OverallVerdict.NO_TESTED_TOPOLOGY_FAILURE,
    }


def test_taxonomy_has_exactly_five_wire_values() -> None:
    """Expose only the approved topology dimensions across API boundaries."""
    assert {dimension.value for dimension in TopologyDimension} == {
        "replica_count",
        "request_routing",
        "restart_recovery",
        "concurrency",
        "state_locality",
    }


def test_analysis_stages_have_exactly_eight_wire_values() -> None:
    """Keep externally observable pipeline stages stable and complete."""
    assert {stage.value for stage in AnalysisStage} == {
        "repository_loaded",
        "diff_parsed",
        "context_expanded",
        "static_analysis_completed",
        "assumption_mining_completed",
        "finding_synthesis_completed",
        "verification_recommendation_completed",
        "report_generated",
    }


def test_remaining_enums_expose_only_documented_wire_values() -> None:
    """Keep every public enum aligned with persisted API values."""
    assert {provider.value for provider in ProviderName} == {"offline", "openai"}
    assert {severity.value for severity in Severity} == {"critical", "high", "medium", "low"}
    assert {verdict.value for verdict in FindingVerdict} == {
        "high-risk",
        "review-required",
        "no-tested-failure",
    }
    assert {status.value for status in RunStatus} == {"queued", "running", "completed", "failed"}
    assert {action.value for action in TrajectoryAction} == {
        "repository_loaded",
        "diff_parsed",
        "changed_symbol_detected",
        "context_expanded",
        "static_signal_created",
        "hypothesis_created",
        "topology_dimension_assigned",
        "verification_proposed",
        "tool_result_observed",
        "hypothesis_updated",
        "finding_created",
        "report_generated",
    }


def test_analysis_request_uses_the_configured_ticket_limit(tmp_path: Path) -> None:
    """Keep request validation compatible with the approved settings boundary."""
    settings = Settings(provider=ProviderName.OPENAI, max_ticket_characters=5)
    request = AnalysisRequest.model_validate_with_settings(
        {
            "repo_path": tmp_path,
            "ticket": "12345",
            "base_ref": "main",
            "candidate_ref": "candidate",
        },
        settings,
    )

    assert request.ticket == "12345"
    assert request.provider is ProviderName.OPENAI
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate_with_settings(
            {
                "repo_path": tmp_path,
                "ticket": "123456",
                "base_ref": "main",
                "candidate_ref": "candidate",
            },
            settings,
        )


def test_analysis_request_explicit_provider_overrides_settings_default(tmp_path: Path) -> None:
    """Honor an explicit request provider over the injected application default."""
    request = AnalysisRequest.model_validate_with_settings(
        {
            "repo_path": tmp_path,
            "ticket": "Check durable deduplication.",
            "base_ref": "main",
            "candidate_ref": "candidate",
            "provider": ProviderName.OFFLINE,
        },
        Settings(provider=ProviderName.OPENAI),
    )

    assert request.provider is ProviderName.OFFLINE


def test_analysis_request_rejects_relative_repository_path() -> None:
    """Require repository paths to be explicit absolute paths."""
    with pytest.raises(ValidationError):
        AnalysisRequest(
            repo_path=Path("relative"),
            ticket="Check durable deduplication.",
            base_ref="main",
            candidate_ref="candidate",
            provider=ProviderName.OFFLINE,
        )


@pytest.mark.parametrize("field", ["ticket", "base_ref", "candidate_ref"])
def test_analysis_request_rejects_blank_text_fields(tmp_path: Path, field: str) -> None:
    """Require meaningful ticket and ref values independently."""
    payload: dict[str, object] = {
        "repo_path": tmp_path,
        "ticket": "Check durable deduplication.",
        "base_ref": "main",
        "candidate_ref": "candidate",
    }
    payload[field] = " \t\n"

    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(payload)


@pytest.mark.parametrize(
    "path",
    [
        "",
        ".",
        "../src/webhook.py",
        "/src/webhook.py",
        "src\\webhook.py",
        "src//webhook.py",
        "src/\nwebhook.py",
    ],
)
def test_evidence_rejects_noncanonical_or_root_paths(path: str) -> None:
    """Reject evidence paths that are not canonical non-root POSIX paths."""
    with pytest.raises(ValidationError):
        EvidenceLocation.model_validate(
            {
                "path": path,
                "line": 4,
                "commit_id": COMMIT_ID,
                "excerpt": "relevant source",
            }
        )


@pytest.mark.parametrize("commit_id", ["not-a-commit", "A" * 40, "a" * 39, "a" * 65])
def test_evidence_rejects_invalid_candidate_commit(commit_id: str) -> None:
    """Require a resolved lowercase SHA-1 or SHA-256 candidate commit."""
    with pytest.raises(ValidationError):
        EvidenceLocation(
            path=PurePosixPath("src/webhook.py"),
            line=4,
            commit_id=commit_id,
            excerpt="relevant source",
        )


def test_evidence_rejects_reverse_line_range() -> None:
    """Prevent evidence spans whose end precedes their first line."""
    with pytest.raises(ValidationError):
        EvidenceLocation(
            path=PurePosixPath("src/webhook.py"),
            line=4,
            line_end=3,
            commit_id=COMMIT_ID,
            excerpt="relevant source",
        )


def test_context_item_rejects_reverse_line_range() -> None:
    """Prevent source excerpts whose end precedes their start."""
    with pytest.raises(ValidationError):
        ContextItem(
            context_id="context-1",
            path=PurePosixPath("src/webhook.py"),
            commit=COMMIT_ID,
            line=5,
            line_end=4,
            excerpt="source excerpt",
            selection_reason="changed code",
            provenance="diff",
        )


def test_assumption_hypothesis_requires_topology_dimensions(
    valid_hypothesis_data: dict[str, object],
) -> None:
    """Reject semantic claims without a topology axis."""
    with pytest.raises(ValidationError):
        AssumptionHypothesis.model_validate(valid_hypothesis_data | {"topology_dimensions": ()})


def test_assumption_hypothesis_requires_unique_dimensions(
    valid_hypothesis_data: dict[str, object],
) -> None:
    """Reject semantic claims that count one topology axis twice."""
    with pytest.raises(ValidationError):
        AssumptionHypothesis.model_validate(
            valid_hypothesis_data
            | {"topology_dimensions": (TopologyDimension.STATE_LOCALITY,) * 2}
        )


def test_assumption_hypothesis_requires_evidence(
    valid_hypothesis_data: dict[str, object],
) -> None:
    """Reject semantic claims without checked candidate evidence."""
    with pytest.raises(ValidationError):
        AssumptionHypothesis.model_validate(valid_hypothesis_data | {"evidence": ()})


def test_evidence_bearing_contracts_reject_duplicate_locations(
    evidence_location: EvidenceLocation,
    valid_finding_data: dict[str, object],
) -> None:
    """Prevent one source location from being counted as repeated support."""
    duplicate_evidence = (evidence_location, evidence_location)
    invalid_payloads: tuple[tuple[type[StaticSignal | AssumptionHypothesis | Finding], dict[str, object]], ...] = (
        (
            StaticSignal,
            {
                "signal_id": "signal-1",
                "kind": "module_mutable_state",
                "module": "src/webhook.py",
                "facts": {"container": "set"},
                "evidence": duplicate_evidence,
            },
        ),
        (
            AssumptionHypothesis,
            {
                "hypothesis_id": "hypothesis-1",
                "engineering_summary": "Local state is used for deduplication.",
                "correctness_property": "One event produces one side effect.",
                "deployment_assumption": "All deliveries share local state.",
                "predicted_failure": "Duplicates occur across workers.",
                "topology_dimensions": (TopologyDimension.STATE_LOCALITY,),
                "evidence": duplicate_evidence,
                "confidence": 0.5,
                "recommendation_summary": "Exercise multiple workers.",
            },
        ),
        (Finding, valid_finding_data | {"evidence": duplicate_evidence}),
    )

    for model, payload in invalid_payloads:
        with pytest.raises(ValidationError):
            model.model_validate(payload)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_finding_rejects_confidence_outside_closed_unit_interval(
    valid_finding_data: dict[str, object], confidence: float
) -> None:
    """Keep confidence values comparable across finding consumers."""
    with pytest.raises(ValidationError):
        Finding.model_validate(valid_finding_data | {"confidence": confidence})


def test_finding_requires_checked_evidence(valid_finding_data: dict[str, object]) -> None:
    """Reject findings that do not retain exact candidate evidence."""
    with pytest.raises(ValidationError):
        Finding.model_validate(valid_finding_data | {"evidence": []})


def test_verification_recommendation_requires_distinct_dimensions() -> None:
    """Reject ambiguous recommendation scopes with repeated dimensions."""
    with pytest.raises(ValidationError):
        VerificationRecommendation(
            worth_running=True,
            summary="Compare two workers.",
            topology_dimensions=(TopologyDimension.REPLICA_COUNT,) * 2,
            property_assertion="The side-effect count remains at most one.",
        )


def test_contract_models_forbid_unknown_fields() -> None:
    """Reject misspelled or unsupported wire fields."""
    with pytest.raises(ValidationError):
        ChangedPath.model_validate({"path": "src/webhook.py", "change_type": "M", "extra": True})


def test_contract_models_forbid_attribute_reassignment() -> None:
    """Keep accepted wire contracts immutable after validation."""
    changed_path = ChangedPath(path=PurePosixPath("src/webhook.py"), change_type="M")
    with pytest.raises(ValidationError):
        changed_path.path = PurePosixPath("src/other.py")


def test_run_failure_requires_a_safe_error_payload() -> None:
    """Prevent failed run states without a public diagnostic contract."""
    with pytest.raises(ValidationError):
        AnalysisRun(
            run_id="run-1",
            status=RunStatus.FAILED,
            provider=ProviderName.OFFLINE,
            created_at=EVENT_TIME,
            updated_at=EVENT_TIME,
        )


def test_error_response_rejects_blank_optional_field() -> None:
    """Keep optional API field names meaningful when they are supplied."""
    with pytest.raises(ValidationError):
        ErrorResponse(code="invalid_request", message="Invalid request.", field=" \t")


def test_contracts_serialize_to_json_boundary_data(
    valid_finding_data: dict[str, object]
) -> None:
    """Serialize nested contracts without retaining Python-only values."""
    finding = Finding.model_validate(valid_finding_data)
    artifact = DiffArtifact(
        patch="@@ -1 +1 @@",
        changed_paths=(ChangedPath(path=PurePosixPath("src/webhook.py"), change_type="M"),),
        summary=DiffSummary(
            changed_file_count=1,
            changed_python_file_count=1,
            additions=1,
            deletions=1,
        ),
    )
    trajectory = TrajectoryEvent(
        run_id="run-1",
        step=1,
        occurred_at=EVENT_TIME,
        component="intake",
        action=TrajectoryAction.REPOSITORY_LOADED,
        summary="Repository resolved.",
    )
    report = ReportArtifact(run_id="run-1", filename="report.md", content="# Report")

    assert '"state_locality"' in finding.model_dump_json()
    assert artifact.model_dump(mode="json")["summary"]["changed_file_count"] == 1
    assert trajectory.model_dump(mode="json")["occurred_at"] == "2026-08-30T00:00:00Z"
    assert report.model_dump(mode="json")["filename"] == "report.md"


def test_source_contracts_preserve_whitespace_and_use_planned_field_types(
    evidence_location: EvidenceLocation,
) -> None:
    """Preserve exact source while exposing downstream path and line fields."""
    context = ContextItem(
        context_id="context-1",
        path=PurePosixPath("src/webhook.py"),
        commit=COMMIT_ID,
        line=12,
        line_end=14,
        excerpt="    seen_events.add(event_id)\n",
        selection_reason="changed code",
        provenance="diff",
    )

    assert evidence_location.path == PurePosixPath("src/webhook.py")
    assert evidence_location.line == 12
    assert evidence_location.excerpt == "    seen_events.add(event_id)\n"
    assert context.path.as_posix() == "src/webhook.py"
    assert context.commit == COMMIT_ID
    assert context.excerpt == "    seen_events.add(event_id)\n"


def test_static_signal_facts_are_deeply_immutable_and_serializable(
    evidence_location: EvidenceLocation,
) -> None:
    """Freeze nested signal facts while preserving their JSON wire form."""
    signal = StaticSignal(
        signal_id="signal-1",
        kind="module_mutable_collection",
        module=PurePosixPath("src/webhook.py"),
        facts={"nested": {"containers": ["set"]}},
        evidence=(evidence_location,),
    )

    mutable_facts = cast(dict[str, object], signal.facts)
    nested_facts = cast(dict[str, object], signal.facts["nested"])
    with pytest.raises(TypeError):
        mutable_facts["new"] = True
    with pytest.raises(TypeError):
        nested_facts["new"] = True
    assert '"containers":["set"]' in signal.model_dump_json()


def test_static_signal_rejects_non_json_facts(evidence_location: EvidenceLocation) -> None:
    """Reject opaque signal values that cannot cross artifact boundaries."""
    with pytest.raises(ValidationError):
        StaticSignal.model_validate(
            {
                "signal_id": "signal-2",
                "kind": "invalid",
                "module": "src/webhook.py",
                "facts": {"opaque": object()},
                "evidence": (evidence_location,),
            }
        )


def test_error_detail_is_deeply_immutable_and_serializable() -> None:
    """Freeze nested safe error detail while retaining a JSON wire form."""
    error = ErrorResponse(code="invalid_request", message="Invalid request.", detail={"fields": ["ticket"]})

    assert error.detail is not None
    mutable_detail = cast(dict[str, object], error.detail)
    with pytest.raises(TypeError):
        mutable_detail["new"] = True
    assert '"fields":["ticket"]' in error.model_dump_json()


def test_trajectory_metadata_is_deeply_immutable_and_serializable() -> None:
    """Freeze nested trajectory metadata while retaining a JSON wire form."""
    event = TrajectoryEvent(
        run_id="run-1",
        step=1,
        occurred_at=EVENT_TIME,
        component="intake",
        action=TrajectoryAction.REPOSITORY_LOADED,
        summary="Repository resolved.",
        metadata={"counts": {"files": 1}},
    )

    nested_metadata = cast(dict[str, object], event.metadata["counts"])
    with pytest.raises(TypeError):
        nested_metadata["files"] = 2
    assert '"files":1' in event.model_dump_json()


def test_trajectory_rejects_non_json_metadata() -> None:
    """Reject opaque trajectory values that cannot cross artifact boundaries."""
    with pytest.raises(ValidationError):
        TrajectoryEvent.model_validate(
            {
                "run_id": "run-1",
                "step": 1,
                "occurred_at": EVENT_TIME,
                "component": "intake",
                "action": TrajectoryAction.REPOSITORY_LOADED,
                "summary": "Repository resolved.",
                "metadata": {"opaque": object()},
            }
        )


def test_high_risk_finding_requires_high_or_critical_severity(
    valid_finding_data: dict[str, object],
) -> None:
    """Reject a high-risk label when impact is below the documented gate."""
    with pytest.raises(ValidationError):
        Finding.model_validate(
            valid_finding_data | {"severity": Severity.LOW, "verdict": FindingVerdict.HIGH_RISK}
        )


def test_high_risk_finding_requires_high_confidence(
    valid_finding_data: dict[str, object],
) -> None:
    """Reject a high-risk label below the named confidence threshold."""
    with pytest.raises(ValidationError):
        Finding.model_validate(
            valid_finding_data | {"confidence": 0.79, "verdict": FindingVerdict.HIGH_RISK}
        )


def test_finding_category_must_be_one_of_its_topology_dimensions(
    valid_finding_data: dict[str, object],
) -> None:
    """Reject a primary category absent from the finding's supported axes."""
    with pytest.raises(ValidationError):
        Finding.model_validate(
            valid_finding_data
            | {"topology_dimensions": (TopologyDimension.REPLICA_COUNT,)}
        )


def test_finding_recommendation_dimensions_must_be_supported(
    valid_finding_data: dict[str, object],
) -> None:
    """Reject an experiment axis absent from the supported finding axes."""
    recommendation = {
        "worth_running": True,
        "summary": "Test concurrency.",
        "topology_dimensions": (TopologyDimension.CONCURRENCY,),
        "property_assertion": "One durable effect remains.",
    }
    with pytest.raises(ValidationError):
        Finding.model_validate(valid_finding_data | {"verification_recommendation": recommendation})


def test_finding_list_requires_unique_ids(
    valid_finding_data: dict[str, object],
) -> None:
    """Keep finding identifiers unique within one aggregate."""
    finding = Finding.model_validate(valid_finding_data)

    with pytest.raises(ValidationError):
        FindingList(
            overall_verdict=OverallVerdict.TOPOLOGY_SENSITIVE_CORRECTNESS_RISK,
            findings=(finding, finding),
        )


def test_finding_list_requires_matching_overall_verdict(
    valid_finding_data: dict[str, object],
) -> None:
    """Reject aggregate verdicts that contradict their findings."""
    finding = Finding.model_validate(valid_finding_data)

    with pytest.raises(ValidationError):
        FindingList(
            overall_verdict=OverallVerdict.NO_TESTED_TOPOLOGY_FAILURE,
            findings=(finding,),
        )


def test_diff_summary_rejects_more_python_files_than_changed_files() -> None:
    """Reject an impossible language-specific changed-file count."""
    with pytest.raises(ValidationError):
        DiffSummary(
            changed_file_count=1,
            changed_python_file_count=2,
            additions=0,
            deletions=0,
        )


def test_diff_artifact_requires_summary_counts_to_match_changed_paths() -> None:
    """Reject diff summaries that disagree with their changed-path records."""
    with pytest.raises(ValidationError):
        DiffArtifact(
            patch="@@ -1 +1 @@",
            changed_paths=(ChangedPath(path=PurePosixPath("src/webhook.py"), change_type="M"),),
            summary=DiffSummary(
                changed_file_count=2,
                changed_python_file_count=1,
                additions=1,
                deletions=1,
            ),
        )


def test_diff_artifact_requires_python_count_to_match_changed_paths() -> None:
    """Reject Python-file counts that disagree with changed path suffixes."""
    with pytest.raises(ValidationError):
        DiffArtifact(
            patch="@@ -1 +1 @@",
            changed_paths=(ChangedPath(path=PurePosixPath("README.md"), change_type="M"),),
            summary=DiffSummary(
                changed_file_count=1,
                changed_python_file_count=1,
                additions=1,
                deletions=1,
            ),
        )


def test_repository_snapshot_requires_canonical_resolved_root(tmp_path: Path) -> None:
    """Reject absolute repository roots that retain traversal segments."""
    with pytest.raises(ValidationError):
        RepositorySnapshot(
            repository_root=tmp_path / "child" / "..",
            base_commit="a" * 40,
            candidate_commit="b" * 40,
            repository_id="repo-1",
        )


@pytest.mark.parametrize(
    "span",
    [{"new_line_start": 4}, {"new_line_end": 4}, {"new_line_start": 5, "new_line_end": 4}],
)
def test_changed_symbol_rejects_incomplete_or_reverse_line_spans(
    span: dict[str, int],
) -> None:
    """Require changed-symbol ranges to be paired, positive, and forward."""
    with pytest.raises(ValidationError):
        ChangedSymbol(
            path=PurePosixPath("src/webhook.py"),
            kind="function",
            name="handle_webhook",
            candidate_commit=COMMIT_ID,
            **span,
        )


def test_changed_symbol_requires_an_old_or_new_line_span() -> None:
    """Reject changed symbols that do not locate either revision."""
    with pytest.raises(ValidationError):
        ChangedSymbol(
            path=PurePosixPath("src/webhook.py"),
            kind="function",
            name="handle_webhook",
            candidate_commit=COMMIT_ID,
        )


def test_completed_run_accepts_complete_ordered_utc_stage_history() -> None:
    """Represent a truthful completed pipeline lifecycle."""
    completed = AnalysisRun.model_validate(completed_run_payload())

    assert completed.completed_stages == tuple(AnalysisStage)


def test_run_stage_timestamps_are_immutable() -> None:
    """Prevent persisted stage completion history from mutating in place."""
    completed = AnalysisRun.model_validate(completed_run_payload())

    with pytest.raises(TypeError):
        completed.stage_timestamps[AnalysisStage.REPOSITORY_LOADED] = EARLIER_EVENT_TIME


def test_running_run_tracks_the_next_incomplete_stage() -> None:
    """Represent progress as a completed prefix plus its next stage."""
    running = AnalysisRun(
        run_id="run-1",
        status=RunStatus.RUNNING,
        provider=ProviderName.OFFLINE,
        created_at=EVENT_TIME,
        updated_at=EVENT_TIME,
        current_stage=AnalysisStage.DIFF_PARSED,
        completed_stages=(AnalysisStage.REPOSITORY_LOADED,),
        stage_timestamps={AnalysisStage.REPOSITORY_LOADED: EVENT_TIME},
    )

    assert running.current_stage is AnalysisStage.DIFF_PARSED


def test_running_run_rejects_out_of_order_current_stage() -> None:
    """Reject progress that skips the next incomplete pipeline stage."""
    with pytest.raises(ValidationError):
        AnalysisRun(
            run_id="run-1",
            status=RunStatus.RUNNING,
            provider=ProviderName.OFFLINE,
            created_at=EVENT_TIME,
            updated_at=EVENT_TIME,
            current_stage=AnalysisStage.CONTEXT_EXPANDED,
            completed_stages=(AnalysisStage.REPOSITORY_LOADED,),
            stage_timestamps={AnalysisStage.REPOSITORY_LOADED: EVENT_TIME},
        )


def test_queued_run_rejects_stage_progress() -> None:
    """Reject completed work on a run that still claims to be queued."""
    with pytest.raises(ValidationError):
        AnalysisRun(
            run_id="run-1",
            status=RunStatus.QUEUED,
            provider=ProviderName.OFFLINE,
            created_at=EVENT_TIME,
            updated_at=EVENT_TIME,
            completed_stages=(AnalysisStage.REPOSITORY_LOADED,),
            stage_timestamps={AnalysisStage.REPOSITORY_LOADED: EVENT_TIME},
        )


def test_run_rejects_update_before_creation() -> None:
    """Reject run metadata that moves backward in time."""
    with pytest.raises(ValidationError):
        AnalysisRun(
            run_id="run-1",
            status=RunStatus.QUEUED,
            provider=ProviderName.OFFLINE,
            created_at=EVENT_TIME,
            updated_at=EARLIER_EVENT_TIME,
        )


def test_run_rejects_non_utc_timestamps() -> None:
    """Require unambiguous UTC timestamps for persisted run state."""
    naive_time = EVENT_TIME.replace(tzinfo=None)
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(
            completed_run_payload() | {"created_at": naive_time, "updated_at": naive_time}
        )


def test_run_rejects_non_utc_stage_timestamp() -> None:
    """Require every recorded stage completion time to use UTC."""
    timestamps = completed_run_payload()["stage_timestamps"]
    assert isinstance(timestamps, dict)
    timestamps = timestamps | {AnalysisStage.REPOSITORY_LOADED: EVENT_TIME.replace(tzinfo=None)}
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(completed_run_payload() | {"stage_timestamps": timestamps})


@pytest.mark.parametrize(
    "completed_stages",
    [
        (AnalysisStage.DIFF_PARSED, AnalysisStage.REPOSITORY_LOADED),
        (AnalysisStage.REPOSITORY_LOADED,) * 2,
        (AnalysisStage.DIFF_PARSED,),
    ],
)
def test_run_rejects_non_prefix_completed_stage_history(
    completed_stages: tuple[AnalysisStage, ...],
) -> None:
    """Require completed stages to be a unique pipeline prefix."""
    stage_timestamps = {stage: EVENT_TIME for stage in set(completed_stages)}
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(
            completed_run_payload()
            | {"completed_stages": completed_stages, "stage_timestamps": stage_timestamps}
        )


def test_run_requires_one_timestamp_per_completed_stage() -> None:
    """Keep stage timestamps exactly aligned with completed work."""
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(completed_run_payload() | {"stage_timestamps": {}})


def test_run_rejects_nonmonotonic_stage_timestamps() -> None:
    """Prevent later stages from appearing to finish before earlier stages."""
    timestamps = completed_run_payload()["stage_timestamps"]
    assert isinstance(timestamps, dict)
    timestamps = timestamps | {AnalysisStage.DIFF_PARSED: EARLIER_EVENT_TIME}
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(completed_run_payload() | {"stage_timestamps": timestamps})


def test_completed_run_requires_overall_verdict() -> None:
    """Reject completed run state without its aggregate analysis result."""
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(completed_run_payload() | {"overall_verdict": None})


def test_completed_run_rejects_current_stage() -> None:
    """Reject an in-progress stage once the run has completed."""
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(
            completed_run_payload() | {"current_stage": AnalysisStage.REPORT_GENERATED}
        )


def test_completed_run_rejects_m2_only_reproducible_verdict() -> None:
    """Keep runtime-verified verdicts impossible before M2 has a verifier."""
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(
            completed_run_payload()
            | {"overall_verdict": OverallVerdict.REPRODUCIBLE_TOPOLOGY_SENSITIVE_FAILURE}
        )


def test_failed_run_rejects_completed_pipeline_history() -> None:
    """Reject a failed state after every pipeline stage claims success."""
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(
            completed_run_payload()
            | {
                "status": RunStatus.FAILED,
                "overall_verdict": None,
                "error": ErrorResponse(code="analysis_failed", message="Analysis failed."),
            }
        )


def test_failed_run_rejects_unrelated_current_stage() -> None:
    """Require a failed run's current stage to be the next incomplete stage."""
    with pytest.raises(ValidationError):
        AnalysisRun(
            run_id="run-1",
            status=RunStatus.FAILED,
            provider=ProviderName.OFFLINE,
            created_at=EARLIER_EVENT_TIME,
            updated_at=EVENT_TIME,
            current_stage=AnalysisStage.CONTEXT_EXPANDED,
            completed_stages=(AnalysisStage.REPOSITORY_LOADED,),
            stage_timestamps={AnalysisStage.REPOSITORY_LOADED: EVENT_TIME},
            error=ErrorResponse(code="analysis_failed", message="Analysis failed."),
        )


def test_analysis_run_serializes_unique_artifact_references() -> None:
    """Expose immutable storage-safe artifact references in run status."""
    completed = AnalysisRun.model_validate(
        completed_run_payload() | {"artifact_refs": ("findings.json", "report.md")}
    )

    assert completed.model_dump(mode="json")["artifact_refs"] == ["findings.json", "report.md"]


def test_analysis_run_rejects_duplicate_artifact_references() -> None:
    """Reject ambiguous duplicate artifact references in run status."""
    with pytest.raises(ValidationError):
        AnalysisRun.model_validate(
            completed_run_payload() | {"artifact_refs": ("report.md", "report.md")}
        )


@pytest.mark.parametrize(
    "run_id",
    [
        "../run",
        "run/child",
        "run\\child",
        " run",
        "run id",
        "run:child",
        "run\nchild",
        "CON",
        "NUL.json",
        "run.",
    ],
)
def test_trajectory_rejects_storage_unsafe_run_ids(run_id: str) -> None:
    """Reject run identifiers that could escape artifact ownership."""
    with pytest.raises(ValidationError):
        TrajectoryEvent(
            run_id=run_id,
            step=1,
            occurred_at=EVENT_TIME,
            component="intake",
            action=TrajectoryAction.REPOSITORY_LOADED,
            summary="Repository resolved.",
        )


@pytest.mark.parametrize(
    "filename",
    [
        "../report.md",
        "nested/report.md",
        "report\\file.md",
        ".",
        "report:bad.md",
        "CON",
        "NUL.md",
        "report.",
        "report.md\r\nX-Test: bad",
    ],
)
def test_report_rejects_storage_or_header_unsafe_filenames(filename: str) -> None:
    """Reject report names that can traverse paths or inject headers."""
    with pytest.raises(ValidationError):
        ReportArtifact(run_id="run-1", filename=filename, content="# Report")


def test_overall_verdict_exposes_documented_wire_values() -> None:
    """Preserve the aggregate verdict labels rendered by reports and UI."""
    assert {verdict.value for verdict in OverallVerdict} == {
        "topology-sensitive-correctness-risk",
        "reproducible-topology-sensitive-failure",
        "review-required",
        "no-tested-topology-failure",
    }
