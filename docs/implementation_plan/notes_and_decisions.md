# 15. Notes & Decisions

### Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2025-10-20 | Use Pydantic Settings for config | Type-safe, validated, extensible | All phases |
| 2025-10-20 | Stateless agent architecture | Simplifies scaling, clearer boundaries | Phase 5 |
| 2025-10-20 | LMStudio for v1.0 | Local inference, no cloud costs | Phase 5 |
| 2025-10-20 | FastAPI for REST API | Modern, async, auto-docs | Phase 7 |
| TBD | Circuit breaker library choice | TBD after research | Phase 6 |

### Open Questions

- [ ] Which circuit breaker library: tenacity vs pybreaker?
- [ ] Exact Google ADK package name and import structure?
- [ ] Docling API specifics for different file formats?
- [ ] LMStudio embedding model dimensions (for ES schema)?
- [ ] Production deployment target (single server, K8s, etc.)?

### Implementation Notes

**Phase-Specific Notes:**

**Phase 1:**

- Ensure Docker Desktop has enough resources (8GB+ RAM recommended)
- LMStudio models can be large - ensure sufficient disk space
- Consider using Docker build cache for faster rebuilds

**Phase 2:**

- Keep `.env.example` updated as new config parameters added
- Document all validation rules in config classes
- Consider environment-specific configs (dev, staging, prod)

**Phase 3:**

- Test with various document formats early
- Monitor memory usage during document processing
- Consider chunking strategy for very large documents

**Phase 4:**

- Elasticsearch version 8.x has different defaults than 7.x
- Vector dimensions must match embedding model output
- Test with realistic document corpus size

**Phase 5:**

- Stateless design means no session management needed
- Each query should be self-contained
- Prompt engineering is critical for answer quality

**Phase 6:**

- Circuit breaker thresholds may need tuning based on testing
- Health probe timeouts should be conservative
- Consider implementing metrics collection

**Phase 7:**

- API rate limiting may be needed for production
- Consider async background processing for large uploads
- Document size limits should be configurable

**Phase 8:**

- Use pytest fixtures for test setup/teardown
- Mock external services (LMStudio, ES) for unit tests
- Integration tests need real services running

**Phase 9:**

- Keep documentation in sync with code changes
- Consider using automated documentation tools
- Plan for ongoing maintenance and updates
