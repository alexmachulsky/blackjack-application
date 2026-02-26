# Best Practices Plan

## Scope
This plan adds engineering best practices on top of the current backend/frontend/infra setup.

## Current Strengths
- Backend tests, linting, security scans, and smoke checks already exist in CI.
- Dockerized dev/prod workflows are present.
- Infra has Terraform modules, Kubernetes manifests, and network policies.

## Phase 1 (High Priority)
1. Replace in-memory active game state with shared state.
- Why: Active games are process-local (`active_games`) and can break with multi-worker/multi-replica runtime.
- Evidence: `backend/app/routes/game.py` stores active engines in a module dict; `docker-compose.prod.yml` runs backend with `--workers 2`.
- Action: Move active hand state to Redis or fully DB-driven transitions.
- Done when: No API behavior depends on in-process memory.

2. Add frontend quality gates (lint + tests).
- Why: Frontend has no lint/test scripts, so regressions can land without checks.
- Evidence: `frontend/package.json` only has `dev`, `build`, `preview` scripts.
- Action: Add ESLint + Prettier + Vitest/RTL, then enforce in CI.
- Done when: PRs fail if frontend lint/tests fail.

3. Enforce type/security checks already listed in dev dependencies.
- Why: `mypy` and `bandit` are installed dependencies but not part of current CI gate.
- Evidence: Present in `backend/requirements-dev.txt`; CI currently runs ruff/black/pytest/pip-audit/trivy.
- Action: Add `mypy app tests` and `bandit -r app` to CI and Makefile.
- Done when: CI blocks merges on mypy/bandit failures.

4. Add a coverage threshold.
- Why: Tests run, but minimum coverage is not enforced.
- Action: Add `--cov-fail-under=<target>` (start at 80%) in CI.
- Done when: Coverage regressions fail CI.

## Phase 2 (Medium Priority)
1. Standardize monetary precision across API contracts.
- Why: DB uses numeric/decimal, but response schemas expose floats.
- Evidence: float fields in `backend/app/schemas/game.py`, `backend/app/schemas/auth.py`, `backend/app/schemas/stats.py`.
- Action: Use integer cents or Decimal-safe serialization at API boundary.
- Done when: No money math relies on float.

2. Add auth abuse protections.
- Why: Login/register endpoints need brute-force protections in production.
- Action: Add rate limiting (per IP/account), lockout/backoff policy, and audit events.
- Done when: Repeated failed auth attempts are throttled and observable.

3. Add local guardrails for developers.
- Why: Faster feedback before push.
- Action: Add `.editorconfig`, `pre-commit` hooks (ruff, black, mypy, frontend lint/test), and consistent `make` targets.
- Done when: Same checks run locally and in CI.

4. Add IaC validation checks in CI.
- Why: Terraform/K8s drift or syntax issues should fail fast.
- Action: Add `terraform fmt -check`, `terraform validate`, `tflint`, and kube manifest validation (`kubeconform` or `kubectl apply --dry-run=client`).
- Done when: Infra PRs are validated automatically.

## Phase 3 (Platform Maturity)
1. Improve release governance.
- Why: CI currently writes back to `main` by mutating manifests.
- Action: Move to GitOps-style deployment (separate deploy repo/branch or ArgoCD/Flux flow) with approval gates.
- Done when: Deployments are auditable and promotion-based.

2. Add observability beyond logs.
- Why: Faster incident triage.
- Action: Add metrics (Prometheus), request IDs, and alerting for `/ready`, error rate, latency, and auth failures.
- Done when: SLO-style dashboards/alerts exist.

3. Add PostgreSQL backup + restore drills.
- Why: StatefulSet DB needs recovery guarantees.
- Action: Schedule backups (volume snapshots or logical dumps) and test restore quarterly.
- Done when: Documented and tested RPO/RTO.

## Suggested Execution Order
1. Phase 1.1, 1.2, 1.3
2. Phase 1.4 + Phase 2.1
3. Phase 2.2, 2.3, 2.4
4. Phase 3 items
