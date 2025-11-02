# 8. Development Workflow

### 8.1 Environment Setup

1. Install uv package manager
2. Clone repository
3. Run `uv sync` to install dependencies
4. Configure environment variables
5. Start LMStudio with required models

### 8.2 Docker Workflow

1. **Build:** `task build` - Build Docker image
2. **Start:** `task start` - Start all services
3. **Stop:** `task stop` - Stop all services
4. **Development:** `task dev` - Start in development mode with hot reload

### 8.3 Testing Strategy

- Unit tests for individual components
- Integration tests for pipeline
- End-to-end tests for complete workflow
- Performance benchmarking
