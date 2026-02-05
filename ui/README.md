# RFSN Control Center UI

Modern web UI for monitoring and controlling RFSN safety-gated agent runs.

## Features

- **Run Management**: Create, start, stop agent or harness runs
- **Live Log Streaming**: Real-time SSE-based log streaming
- **Ledger Timeline**: Visual timeline of proposals, decisions, and results
- **Artifact Browser**: Browse and view run artifacts with path confinement
- **Hash Chain Verification**: Verify ledger integrity
- **Settings**: Configure LLM model and API settings

## Quick Start

### One-time Setup

```bash
# Install dependencies
make install
```

### Development

Run in two terminals:

```bash
# Terminal 1: Backend (FastAPI)
make dev-backend

# Terminal 2: Frontend (Vite)
make dev-frontend
```

Then open: **<http://localhost:5173>**

### Production Build

```bash
make build
make prod
```

## Architecture

```
ui/
├── backend/
│   ├── main.py           # FastAPI endpoints
│   ├── run_manager.py    # Process spawning and lifecycle
│   ├── security.py       # Path confinement, validation
│   ├── ledger_parse.py   # Ledger parsing, timeline
│   ├── sse.py            # Server-sent events streaming
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # Typed API client
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Route pages
│   │   ├── App.tsx       # Main router and layout
│   │   └── types.ts      # TypeScript types
│   └── package.json
└── Makefile
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/runs` | List all runs |
| POST | `/runs/create` | Create new run |
| POST | `/runs/{id}/start` | Start a run |
| POST | `/runs/{id}/stop` | Stop a run |
| GET | `/runs/{id}/logs` | Get log content |
| GET | `/runs/{id}/logs/stream` | SSE log stream |
| GET | `/runs/{id}/ledger` | Get parsed ledger |
| GET | `/runs/{id}/ledger/timeline` | Get timeline view |
| POST | `/runs/{id}/verify` | Verify hash chain |
| GET | `/runs/{id}/artifacts/list` | List artifacts |
| GET | `/runs/{id}/artifacts/file` | Get file content |
| GET | `/settings` | Get saved settings |
| POST | `/settings` | Save settings |

## Security

- All artifact paths are confined to run directories
- Path traversal attempts are blocked
- API key stored locally (not exposed in responses)
- Run IDs are validated against injection

## Development Notes

- Frontend proxies `/api` to backend at port 8000
- SSE used for real-time log streaming
- Ledger hash chain verified with SHA-256
- White background theme as requested
