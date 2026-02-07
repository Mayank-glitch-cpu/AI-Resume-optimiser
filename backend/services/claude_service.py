import os
import time
import logging
from anthropic import Anthropic
from dotenv import load_dotenv
from prompts.optimizer_prompt import OPTIMIZER_SYSTEM_PROMPT, get_optimization_prompt
from services.latex_service import compile_latex_to_pdf

load_dotenv()

logger = logging.getLogger("resume_optimizer")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MAX_FIX_ATTEMPTS = 2
MAX_PAGE_SHRINK_ATTEMPTS = 2


def _clean_latex_response(text: str) -> str:
    """Strip markdown code fences from Claude's response."""
    if text.startswith("```latex"):
        text = text[8:]
        logger.info("Stripped ```latex prefix")
    elif text.startswith("```"):
        text = text[3:]
        logger.info("Stripped ``` prefix")
    if text.endswith("```"):
        text = text[:-3]
        logger.info("Stripped ``` suffix")
    return text.strip()


def _run_validation_checks(latex: str) -> None:
    """Log basic LaTeX structural checks."""
    logger.info("-" * 40)
    logger.info("RUNNING VALIDATION CHECKS")

    has_documentclass = "\\documentclass" in latex
    has_begin_doc = "\\begin{document}" in latex
    has_end_doc = "\\end{document}" in latex
    brace_balance = latex.count("{") - latex.count("}")

    logger.info("  \\documentclass present: %s", has_documentclass)
    logger.info("  \\begin{document} present: %s", has_begin_doc)
    logger.info("  \\end{document} present: %s", has_end_doc)
    logger.info("  Brace balance (should be 0): %d", brace_balance)

    if not has_documentclass or not has_begin_doc or not has_end_doc:
        logger.warning("VALIDATION WARNING: Missing essential LaTeX structure")
    if brace_balance != 0:
        logger.warning("VALIDATION WARNING: Unbalanced braces (diff=%d)", brace_balance)


async def _try_compile(latex: str) -> tuple[str | None, int]:
    """Try to compile LaTeX. Returns (error_string | None, page_count)."""
    logger.info("-" * 40)
    logger.info("TEST COMPILATION — checking if LaTeX compiles cleanly")
    pdf_bytes, error, page_count = await compile_latex_to_pdf(latex)
    if error:
        logger.warning("TEST COMPILATION FAILED: %s", error[:300])
        return error, 0
    logger.info("TEST COMPILATION PASSED — %d page(s), %.1f KB", page_count, len(pdf_bytes) / 1024)
    return None, page_count


async def _ask_claude_to_fix(latex: str, compile_error: str, conversation: list) -> str:
    """Send the compile error back to Claude and ask for a fix."""
    fix_prompt = f"""The LaTeX you returned failed to compile with this error:

```
{compile_error}
```

The error is in the LaTeX output you generated. Common causes:
- \\resumeItem placed directly inside \\resumeSubHeadingListStart without a \\resumeItemListStart wrapper
- Custom command called with wrong number of arguments (e.g. \\eduSubheading expects 5 args)
- Bare text inside an itemize/enumerate without \\item

Fix the error and return the COMPLETE corrected LaTeX. No explanations, no markdown fences — only the full LaTeX code."""

    conversation.append({"role": "user", "content": fix_prompt})

    logger.info("CALLING CLAUDE API for fix attempt")
    start = time.time()

    message = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=8192,
        system=OPTIMIZER_SYSTEM_PROMPT,
        messages=conversation,
    )

    elapsed = time.time() - start
    logger.info("Fix response in %.2f seconds (tokens: in=%d, out=%d)",
                elapsed, message.usage.input_tokens, message.usage.output_tokens)

    fixed = _clean_latex_response(message.content[0].text)
    conversation.append({"role": "assistant", "content": fixed})
    return fixed


async def _ask_claude_to_shrink(page_count: int, conversation: list) -> str:
    """Ask Claude to reduce the resume to exactly one page."""
    shrink_prompt = f"""The LaTeX you returned compiles successfully but produces {page_count} page(s). It MUST fit on exactly 1 page.

Apply these reduction strategies in order until it fits:
1. Cut bullet points from older or less-relevant roles (keep max 3 per role)
2. Shorten verbose bullet text — tighter wording, fewer filler words
3. Remove or condense the least-relevant project
4. Consolidate similar skills onto fewer lines
5. Tighten vertical spacing with \\vspace{{-Xpt}} adjustments (don't go below -15pt between sections)
6. If still too long, drop the ADDITIONAL/Awards section entirely

Do NOT reduce font below 10pt or margins below 0.5in.

Return the COMPLETE corrected LaTeX that fits on exactly 1 page. No explanations, no markdown fences — only the full LaTeX code."""

    conversation.append({"role": "user", "content": shrink_prompt})

    logger.info("CALLING CLAUDE API for page-shrink")
    start = time.time()

    message = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=8192,
        system=OPTIMIZER_SYSTEM_PROMPT,
        messages=conversation,
    )

    elapsed = time.time() - start
    logger.info("Shrink response in %.2f seconds (tokens: in=%d, out=%d)",
                elapsed, message.usage.input_tokens, message.usage.output_tokens)

    shrunk = _clean_latex_response(message.content[0].text)
    conversation.append({"role": "assistant", "content": shrunk})
    return shrunk


async def optimize_resume(latex: str, job_description: str) -> dict:
    """
    Optimize a LaTeX resume, then compile-test it.
    If compilation fails, ask Claude to fix up to MAX_FIX_ATTEMPTS times.
    """
    logger.info("=" * 60)
    logger.info("OPTIMIZATION REQUEST RECEIVED")
    logger.info("=" * 60)
    logger.info("LaTeX input length: %d chars", len(latex))
    logger.info("Job description length: %d chars", len(job_description))

    jd_preview = job_description[:200].replace("\n", " ")
    logger.info("Job description preview: %s...", jd_preview)

    try:
        # ── Phase 1: Initial optimization ─────────────────────────
        user_prompt = get_optimization_prompt(latex, job_description)
        logger.info("System prompt length: %d chars", len(OPTIMIZER_SYSTEM_PROMPT))
        logger.info("User prompt length: %d chars", len(user_prompt))

        logger.info("-" * 40)
        logger.info("CALLING CLAUDE API (model: claude-opus-4-5-20251101)")
        logger.info("Max tokens: 8192")
        start_time = time.time()

        message = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=8192,
            system=OPTIMIZER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        elapsed = time.time() - start_time
        logger.info("Claude API responded in %.2f seconds", elapsed)
        logger.info("Response — stop_reason: %s", message.stop_reason)
        logger.info("Response — input_tokens: %d, output_tokens: %d",
                     message.usage.input_tokens, message.usage.output_tokens)

        optimized_latex = _clean_latex_response(message.content[0].text)
        logger.info("Cleaned output length: %d chars", len(optimized_latex))

        _run_validation_checks(optimized_latex)

        # ── Phase 2: Compile-test and auto-fix loop ───────────────
        # Keep conversation history so Claude sees its own output + the error
        conversation = [
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": optimized_latex},
        ]

        page_count = 0
        for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
            compile_error, page_count = await _try_compile(optimized_latex)
            if compile_error is None:
                break  # compiles fine

            logger.info("=" * 40)
            logger.info("AUTO-FIX ATTEMPT %d/%d", attempt, MAX_FIX_ATTEMPTS)
            logger.info("=" * 40)

            optimized_latex = await _ask_claude_to_fix(
                optimized_latex, compile_error, conversation
            )
            _run_validation_checks(optimized_latex)
        else:
            # Ran all attempts — check one last time
            final_error, page_count = await _try_compile(optimized_latex)
            if final_error:
                logger.warning("All %d fix attempts exhausted — returning last version anyway", MAX_FIX_ATTEMPTS)

        # ── Phase 3: Page-count check — shrink to 1 page ─────────
        if page_count > 1:
            logger.info("=" * 40)
            logger.info("PAGE COUNT CHECK: %d pages detected (must be 1)", page_count)
            logger.info("=" * 40)

            for shrink in range(1, MAX_PAGE_SHRINK_ATTEMPTS + 1):
                logger.info("PAGE-SHRINK ATTEMPT %d/%d", shrink, MAX_PAGE_SHRINK_ATTEMPTS)

                optimized_latex = await _ask_claude_to_shrink(
                    page_count, conversation
                )
                _run_validation_checks(optimized_latex)

                compile_error, page_count = await _try_compile(optimized_latex)
                if compile_error:
                    logger.warning("Shrunk version failed to compile — running fix loop")
                    optimized_latex = await _ask_claude_to_fix(
                        optimized_latex, compile_error, conversation
                    )
                    _, page_count = await _try_compile(optimized_latex)

                if page_count <= 1:
                    logger.info("PAGE-SHRINK SUCCESS — now %d page(s)", page_count)
                    break
            else:
                logger.warning("Could not shrink to 1 page after %d attempts (still %d pages)",
                               MAX_PAGE_SHRINK_ATTEMPTS, page_count)

        logger.info("=" * 60)
        logger.info("OPTIMIZATION COMPLETE — returning %d chars of LaTeX (%d page(s))",
                     len(optimized_latex), page_count)
        logger.info("=" * 60)

        return {
            "optimized_latex": optimized_latex,
            "optimization_summary": "Resume optimized successfully for the target position.",
            "success": True,
        }

    except Exception as e:
        logger.error("=" * 60)
        logger.error("OPTIMIZATION FAILED: %s", str(e))
        logger.error("=" * 60, exc_info=True)
        return {
            "optimized_latex": latex,
            "optimization_summary": f"Optimization failed: {str(e)}",
            "success": False,
        }
