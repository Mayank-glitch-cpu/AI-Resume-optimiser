import os
import re
import subprocess
import tempfile
import shutil
import platform
import logging

logger = logging.getLogger("resume_optimizer")


def get_pdflatex_command() -> str:
    """Get the pdflatex command, using full path on Windows if available."""
    if platform.system() == "Windows":
        miktex_path = os.path.expandvars(
            r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
        )
        if os.path.exists(miktex_path):
            logger.info("Using MiKTeX pdflatex: %s", miktex_path)
            return miktex_path
    logger.info("Using system pdflatex from PATH")
    return "pdflatex"


def _parse_page_count(log_path: str) -> int:
    """Parse page count from pdflatex log file.

    Looks for: 'Output written on resume.pdf (N page...'
    """
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            log_content = f.read()
        match = re.search(r"Output written on .+?\((\d+) pages?", log_content)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 0


async def compile_latex_to_pdf(latex: str) -> tuple[bytes | None, str | None, int]:
    """
    Compile LaTeX code to PDF using pdflatex.

    Returns:
        (pdf_bytes, error_message, page_count)
        - Success: (pdf_bytes, None, page_count)
        - Failure: (None, error_message, 0)
    """
    logger.info("=" * 60)
    logger.info("PDF COMPILATION REQUEST")
    logger.info("=" * 60)
    logger.info("LaTeX source length: %d chars", len(latex))

    temp_dir = tempfile.mkdtemp(prefix="latex_compile_")
    logger.info("Created temp directory: %s", temp_dir)

    try:
        # Write source file
        tex_path = os.path.join(temp_dir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex)
        logger.info("Wrote LaTeX source to %s", tex_path)

        # Run pdflatex twice
        pdflatex_cmd = get_pdflatex_command()
        for run_num in range(1, 3):
            logger.info("-" * 40)
            logger.info("pdflatex pass %d/2", run_num)
            logger.info("Command: %s -interaction=nonstopmode -halt-on-error resume.tex", pdflatex_cmd)

            result = subprocess.run(
                [
                    pdflatex_cmd,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-output-directory", temp_dir,
                    tex_path
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=temp_dir,
            )

            logger.info("Pass %d exit code: %d", run_num, result.returncode)
            if result.returncode != 0:
                stdout_lines = result.stdout.strip().split("\n")
                logger.warning("Pass %d FAILED — last 20 lines of output:", run_num)
                for line in stdout_lines[-20:]:
                    logger.warning("  | %s", line)
                if result.stderr.strip():
                    logger.warning("stderr: %s", result.stderr.strip()[:500])
            else:
                logger.info("Pass %d succeeded", run_num)

        # Parse page count from log (do this before cleanup)
        log_path = os.path.join(temp_dir, "resume.log")
        page_count = _parse_page_count(log_path)

        # Check for PDF output
        pdf_path = os.path.join(temp_dir, "resume.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            logger.info("=" * 60)
            logger.info("COMPILATION SUCCESS — PDF size: %d bytes (%.1f KB), %d page(s)",
                        len(pdf_bytes), len(pdf_bytes) / 1024, page_count)
            logger.info("=" * 60)
            return pdf_bytes, None, page_count
        else:
            error_msg = "PDF compilation failed."
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    log_content = f.read()
                lines = log_content.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith("!"):
                        error_lines = lines[i:i+5]
                        error_msg = "\n".join(error_lines)
                        break
            logger.error("=" * 60)
            logger.error("COMPILATION FAILED — no PDF generated")
            logger.error("Error: %s", error_msg)
            logger.error("=" * 60)
            return None, error_msg, 0

    except subprocess.TimeoutExpired:
        logger.error("COMPILATION TIMEOUT — pdflatex exceeded 60s")
        return None, "LaTeX compilation timed out after 60 seconds.", 0
    except FileNotFoundError:
        logger.error("pdflatex NOT FOUND — is TeX Live / MiKTeX installed?")
        return None, "pdflatex not found. Please ensure LaTeX is installed and in PATH.", 0
    except Exception as e:
        logger.error("COMPILATION EXCEPTION: %s", str(e), exc_info=True)
        return None, f"Compilation error: {str(e)}", 0
    finally:
        try:
            shutil.rmtree(temp_dir)
            logger.info("Cleaned up temp directory: %s", temp_dir)
        except Exception:
            pass


def check_pdflatex_available() -> bool:
    """Check if pdflatex is available in the system."""
    try:
        pdflatex_cmd = get_pdflatex_command()
        result = subprocess.run(
            [pdflatex_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        available = result.returncode == 0
        if available:
            version_line = result.stdout.strip().split("\n")[0]
            logger.info("pdflatex available: %s", version_line)
        else:
            logger.warning("pdflatex found but returned non-zero exit code")
        return available
    except Exception as e:
        logger.warning("pdflatex not available: %s", str(e))
        return False
