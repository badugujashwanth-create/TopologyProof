# TopologyProof architecture

TopologyProof is a local static-first verification workbench. A FastAPI backend accepts a local Git repository, ticket, and base/candidate refs. The bounded shell-free Git client feeds repository intake, changed-symbol detection, provenance-bounded context, and deterministic mutable-state signals. The offline assumption provider turns factual evidence into structured deployment hypotheses; finding synthesis validates candidate evidence, applies the scoped verdict policy, and emits recommendation-only verification data.

Runs are persisted by `RunStore` with atomic UTF-8 artifacts and observable JSONL trajectories plus Markdown reports. An in-process executor runs the explicit pipeline. React/Vite provides four M1 screens backed by the real API.

Target repositories remain untrusted and read-only; source code is never executed. Runtime topology falsification (including multi-replica experiments) is future M2 scope.
