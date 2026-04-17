# API Reference

Interactive Swagger UI is available at `http://localhost:8000/api/docs`
when the API is running locally.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/v1/health`          | Service health check |
| GET  | `/api/v1/algorithms`      | List available algorithms |
| POST | `/api/v1/jobs`            | Submit a retrieval job |
| GET  | `/api/v1/jobs`            | List all jobs |
| GET  | `/api/v1/jobs/{id}`       | Get job status and details |
| DELETE | `/api/v1/jobs/{id}`     | Cancel or delete a job |

## Request / Response Schemas

See `snowsar.api.schemas` for full Pydantic model definitions.

---

*Auto-generated reference with mkdocstrings coming in Phase 3.*
