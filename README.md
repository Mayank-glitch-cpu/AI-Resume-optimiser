# Resume Optimizer Service

A full-stack resume optimization service that uses Claude AI to optimize LaTeX resumes for specific job descriptions. Dockerized and deployable to Render.

## Features

- **AI-Powered Optimization**: Uses Claude Opus 4.5 with a detailed multi-phase system prompt
- **LaTeX Support**: Full LaTeX input/output with Monaco editor and syntax highlighting
- **PDF Compilation**: Compiles optimized LaTeX to PDF using pdflatex (TeX Live in Docker)
- **Auto-Fix Loop**: If the optimized LaTeX fails to compile, Claude automatically fixes it (up to 2 retries)
- **Page-Shrink Loop**: If the compiled PDF exceeds 1 page, Claude automatically condenses it (up to 2 retries)
- **Detailed Logging**: Every step of the pipeline is logged for full observability via `docker logs`
- **CORS-Enabled API**: Ready for external integration (JobHunt AI)
- **Modern UI**: Dark theme with custom color palette
- **Single-Container Deployment**: Frontend and backend served from one Docker container on one port

## Optimization Pipeline

When the user clicks "Optimize Resume", the backend runs a 3-phase pipeline:

```
Phase 1: OPTIMIZATION
  Claude reads the system prompt (prompt.md) and optimizes the LaTeX
  for the target job description.

Phase 2: COMPILE-TEST + AUTO-FIX (up to 2 attempts)
  The optimized LaTeX is test-compiled with pdflatex.
  If compilation fails, the error is sent back to Claude
  with the full conversation history to fix.

Phase 3: PAGE-SHRINK (up to 2 attempts)
  If the PDF compiles but is >1 page, Claude is asked to
  condense it using spacing, bullet reduction, and content
  trimming strategies — then recompiled to verify.
```

## System Prompt

The optimization logic is driven by a detailed system prompt at `backend/prompts/prompt.md`. It covers:

- **5-Phase Framework**: Job Analysis, Gap Analysis, Optimization Rules, One-Page Enforcement, Keyword Density Check
- **STAR-K Method**: Each bullet point is optimized with Situation, Task, Action, Result, Keywords
- **Critical LaTeX Rules**: Argument counting, list nesting, brace balancing, package preservation
- **Correct/Wrong Examples**: Explicit examples of proper `\resumeSubHeadingListStart` / `\resumeItemListStart` nesting to prevent the "missing \item" error
- **Self-Validation Checklist**: Claude verifies its own output before returning
- **Edge Case Handling**: Missing skills, vague JDs, career changers, overqualified candidates

## Docker Deployment

### Build and Run Locally

```bash
# Build the image (installs TeX Live, builds Next.js frontend)
docker build -t resume-optimizer .

# Run with your API key
docker run -d -p 8000:8000 --env-file backend/.env --name resume-optimizer resume-optimizer

# Or pass the key directly
docker run -d -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... --name resume-optimizer resume-optimizer

# View logs (shows full pipeline activity)
docker logs -f resume-optimizer
```

Open `http://localhost:8000` — frontend and API are served from the same port.

### Deploy to Render

This project includes a `render.yaml` blueprint for one-click deployment on Render Pro:

1. Push the repo to GitHub
2. In Render dashboard: **New > Blueprint** and connect the repo
3. Render reads `render.yaml` and creates the service
4. Set `ANTHROPIC_API_KEY` in the Render dashboard environment variables
5. Deploy

The `render.yaml` configures:
- Docker runtime with the included `Dockerfile`
- Pro plan (required for TeX Live image size)
- Health check at `/api/health`
- Auto-deploy on push

### Docker Log Output

```
RESUME OPTIMIZER API STARTING
pdflatex available: True
ANTHROPIC_API_KEY set: True
Static dir exists: True

>>> POST /api/optimize
OPTIMIZATION REQUEST RECEIVED
LaTeX input length: 13559 chars
Job description length: 5338 chars
CALLING CLAUDE API (model: claude-opus-4-5-20251101)
Claude API responded in 44.02 seconds
Response — input_tokens: 7993, output_tokens: 3328
RUNNING VALIDATION CHECKS
  \documentclass present: True
  \begin{document} present: True
  Brace balance (should be 0): 0
TEST COMPILATION PASSED — 2 page(s), 92.6 KB
PAGE COUNT CHECK: 2 pages detected (must be 1)
PAGE-SHRINK ATTEMPT 1/2
CALLING CLAUDE API for page-shrink
Shrink response in 25.41 seconds
TEST COMPILATION PASSED — 1 page(s), 68.3 KB
PAGE-SHRINK SUCCESS — now 1 page(s)
OPTIMIZATION COMPLETE — returning 8540 chars of LaTeX (1 page(s))
<<< POST /api/optimize — 200 (95.20s)
```

## Local Development (without Docker)

### Prerequisites

- Python 3.10+
- Node.js 18+
- pdflatex (MiKTeX on Windows, TeX Live on Linux/macOS)
- Anthropic API key

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# Add your API key to backend/.env
# ANTHROPIC_API_KEY=sk-ant-...

uvicorn main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend at `http://localhost:3000`, API at `http://localhost:8001`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check (includes pdflatex status) |
| `POST` | `/api/optimize` | Optimize LaTeX resume for a job description |
| `POST` | `/api/compile` | Compile LaTeX to PDF |
| `GET` | `/docs` | Swagger UI (interactive API docs) |

### POST /api/optimize

```json
{
  "latex": "\\documentclass{article}...",
  "job_description": "We are looking for..."
}
```

Response:
```json
{
  "optimized_latex": "\\documentclass{article}...",
  "optimization_summary": "Resume optimized successfully for the target position.",
  "success": true
}
```

### POST /api/compile

```json
{
  "latex": "\\documentclass{article}..."
}
```

Response: Binary PDF file (`application/pdf`)

## Project Structure

```
resume-optimizer/
├── Dockerfile                  # Multi-stage build (Node.js + Python + TeX Live)
├── .dockerignore
├── render.yaml                 # Render deployment blueprint
├── README.md
├── backend/
│   ├── main.py                 # FastAPI app with logging middleware + static serving
│   ├── requirements.txt
│   ├── .env                    # ANTHROPIC_API_KEY (not committed)
│   ├── services/
│   │   ├── claude_service.py   # Optimization + auto-fix + page-shrink pipeline
│   │   └── latex_service.py    # pdflatex compilation with page count parsing
│   └── prompts/
│       ├── prompt.md           # Full system prompt (loaded at runtime)
│       └── optimizer_prompt.py # Reads prompt.md, builds user prompt
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Main page
│   │   ├── layout.tsx          # Root layout
│   │   └── globals.css         # Custom theme + animations
│   ├── components/
│   │   ├── ResumeInput.tsx     # LaTeX code editor (Monaco)
│   │   ├── JobDescInput.tsx    # Job description textarea
│   │   ├── ResultView.tsx      # Optimized LaTeX editor
│   │   └── PdfPreview.tsx      # PDF preview iframe + download
│   ├── package.json
│   ├── next.config.js          # Static export for Docker
│   └── tailwind.config.js      # Custom color palette
```

## Color Palette

| Name | Hex | Usage |
|------|-----|-------|
| Mountain Shadow | `#101357` | Primary background |
| Old Makeup | `#fea49f` | Accent pink |
| Goldenrod | `#fbaf08` | Highlights / CTAs |
| Bluebell | `#00a0a0` | Secondary / links |
| Bold Green | `#007f4f` | Success states |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |
| `PORT` | No | Server port (default: `8000`, set by Render) |
| `NEXT_PUBLIC_API_URL` | No | API URL for frontend (empty in Docker, `http://localhost:8001` for local dev) |

## License

MIT
