# =============================================================================
# Stage 1: Build the Next.js frontend as static export
# =============================================================================
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

# Install dependencies first (layer caching)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source and build static export
COPY frontend/ ./
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# =============================================================================
# Stage 2: Production runtime — Python + TeX Live + static frontend
# =============================================================================
FROM python:3.11-slim

# Install TeX Live and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-recommended \
    texlive-plain-generic \
    lmodern \
    cm-super \
    && rm -rf /var/lib/apt/lists/*

# Verify pdflatex is installed
RUN pdflatex --version

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy the built frontend into backend/static for serving
COPY --from=frontend-build /app/frontend/out ./static

# Render sets PORT env var; default to 8000
ENV PORT=8000

EXPOSE ${PORT}

# Start the FastAPI server
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
