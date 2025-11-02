# 8. Security Architecture

### 8.1 Configuration Security

**Principles:**

1. **Secrets Separation:** Secrets isolated from regular config
2. **Environment Variables:** All sensitive data via env vars
3. **No Hard-Coding:** Zero credentials in source code
4. **Secret Masking:** Pydantic SecretStr masks values in logs
5. **Validation:** Startup validation prevents misconfiguration

**Implementation:**

```python
from pydantic import SecretStr

class LMStudioSettings:
    api_key: SecretStr = SecretStr("")  # Masked in logs

    def get_api_key(self) -> str:
        """Safe access to secret value."""
        return self.api_key.get_secret_value()
```

### 8.2 Network Security

**Current State (v1.0):**

- Local deployment only
- No authentication on Elasticsearch (development)
- LMStudio on localhost (not exposed)
- No TLS (internal communication)

**Future Enhancements (v2.0):**

- Elasticsearch authentication (username/password)
- TLS for external communication
- API key authentication for REST API
- Rate limiting on endpoints
- JWT token authentication

### 8.3 Data Security

| Data Type | Storage | Encryption | Access Control |
|-----------|---------|------------|----------------|
| Documents | Elasticsearch | At rest (future) | No auth (v1.0) |
| Vectors | Elasticsearch | At rest (future) | No auth (v1.0) |
| Secrets | Environment | Masked in logs | File permissions |
| Logs | File system | None | File permissions |

### 8.4 Dependency Security

**Practices:**

- Dependency pinning in `pyproject.toml`
- Regular security audits (`uv` tooling)
- Minimal dependency footprint
- Official package sources only
