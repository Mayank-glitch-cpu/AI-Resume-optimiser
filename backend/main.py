import logging
import sys
import os
import time

# ── Logging setup (must come before any app imports) ──────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("resume_optimizer")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel

# Add the backend directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.claude_service import optimize_resume
from services.latex_service import compile_latex_to_pdf, check_pdflatex_available

app = FastAPI(
    title="Resume Optimizer API",
    description="Optimize LaTeX resumes for specific job descriptions using Claude AI",
    version="1.0.0"
)

# Configure CORS for external API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    logger.info(">>> %s %s", request.method, request.url.path)
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info("<<< %s %s — %d (%.2fs)", request.method, request.url.path, response.status_code, elapsed)
    return response


# ── Startup event ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("RESUME OPTIMIZER API STARTING")
    logger.info("=" * 60)
    pdflatex_ok = check_pdflatex_available()
    logger.info("pdflatex available: %s", pdflatex_ok)
    has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    logger.info("ANTHROPIC_API_KEY set: %s", has_api_key)
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    logger.info("Static dir exists: %s (%s)", os.path.isdir(static_dir), static_dir)
    logger.info("=" * 60)


class OptimizeRequest(BaseModel):
    latex: str
    job_description: str


class OptimizeResponse(BaseModel):
    optimized_latex: str
    optimization_summary: str
    success: bool


class CompileRequest(BaseModel):
    latex: str


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    pdflatex_available = check_pdflatex_available()
    return {
        "status": "healthy",
        "pdflatex_available": pdflatex_available,
        "message": "Resume Optimizer API is running"
    }


@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_endpoint(request: OptimizeRequest):
    """
    Optimize a LaTeX resume for a specific job description.

    - **latex**: The original LaTeX resume code
    - **job_description**: The target job description to optimize for
    """
    if not request.latex.strip():
        raise HTTPException(status_code=400, detail="LaTeX content is required")
    if not request.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required")

    result = await optimize_resume(request.latex, request.job_description)
    return OptimizeResponse(**result)


@app.post("/api/compile")
async def compile_endpoint(request: CompileRequest):
    """
    Compile LaTeX code to PDF.

    - **latex**: The LaTeX code to compile

    Returns the PDF file as binary data.
    """
    if not request.latex.strip():
        raise HTTPException(status_code=400, detail="LaTeX content is required")

    pdf_bytes, error, page_count = await compile_latex_to_pdf(request.latex)

    if error:
        raise HTTPException(status_code=400, detail=error)

    logger.info("COMPILE RESULT — %d page(s), %.1f KB", page_count, len(pdf_bytes) / 1024)
    if page_count > 1:
        logger.warning("PDF is %d pages (expected 1)", page_count)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=resume.pdf"
        }
    )


# ── Serve frontend static files in production ─────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(STATIC_DIR):
    logger.info("Mounting frontend static files from %s", STATIC_DIR)

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the Next.js static export."""
        file_path = os.path.join(STATIC_DIR, full_path)

        # Serve the exact file if it exists
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # Try adding .html extension (Next.js export convention)
        html_path = file_path + ".html"
        if os.path.isfile(html_path):
            return FileResponse(html_path)

        # Fallback to index.html for SPA routing
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)

        raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
