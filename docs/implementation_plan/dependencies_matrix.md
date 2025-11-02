# 13. Dependencies Matrix

| Phase | Depends On | Blocks |
|-------|-----------|--------|
| Phase 1: Setup | None | All phases |
| Phase 2: Configuration | Phase 1 | Phases 3-9 |
| Phase 3: Document Pipeline | Phases 1, 2 | Phases 4, 5 |
| Phase 4: Elasticsearch | Phases 2, 3 | Phase 5 |
| Phase 5: LLM & Agent | Phases 2, 4 | Phases 6, 7 |
| Phase 6: Resilience | Phase 5 | Phase 7 |
| Phase 7: API | Phases 5, 6 | Phase 8 |
| Phase 8: Testing | All previous | Phase 9 |
| Phase 9: Documentation | Phase 8 | None |

### Critical Path

1. Phase 1 (Setup) → 2 (Config) → 3 (Pipeline) → 4 (Elasticsearch) → 5 (Agent) → 7 (API) → 8 (Testing) → 9 (Deployment)

### Parallel Work Opportunities

- While waiting for LMStudio setup, work on configuration
- Document processing can be developed in parallel with ES setup
- Health probes can be developed while agent is in progress
