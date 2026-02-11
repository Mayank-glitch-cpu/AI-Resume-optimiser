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


def _clean_latex_response(text: str) -> str:
    """Strip markdown code fences from Claude's response."""
    if text.startswith("```latex"):
        text = text[8:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


async def _compile_check(latex: str) -> tuple[str | None, int]:
    """Compile LaTeX and return (error_or_None, page_count)."""
    pdf_bytes, error, page_count = await compile_latex_to_pdf(latex)
    if error:
        logger.warning("Compilation failed: %s", error[:300])
        return error, 0
    logger.info("Compilation passed — %d page(s), %.1f KB", page_count, len(pdf_bytes) / 1024)
    return None, page_count


def _call_claude(system: str, messages: list) -> str:
    """Single Claude API call. Returns cleaned LaTeX."""
    start = time.time()
    message = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=8192,
        system=system,
        messages=messages,
    )
    elapsed = time.time() - start
    logger.info("Claude responded in %.2fs (in=%d, out=%d tokens)",
                elapsed, message.usage.input_tokens, message.usage.output_tokens)
    return _clean_latex_response(message.content[0].text)


async def optimize_resume(latex: str, job_description: str) -> dict:
    """
    Optimize a LaTeX resume for a job description.

    Flow:
      1. Send resume + JD to Claude with the full optimization prompt.
      2. Check if the output compiles — if not, ask Claude to fix once.
      3. Check if the output is one page — if not, ask Claude to shrink once.
    """
    logger.info("=" * 60)
    logger.info("OPTIMIZATION REQUEST — LaTeX: %d chars, JD: %d chars", len(latex), len(job_description))
    logger.info("=" * 60)

    try:
        # ── Step 1: Main optimization call ────────────────────────
        user_prompt = get_optimization_prompt(latex, job_description)
        conversation = [{"role": "user", "content": user_prompt}]

        logger.info("Calling Claude for optimization...")
        optimized_latex = _call_claude(OPTIMIZER_SYSTEM_PROMPT, conversation)
        conversation.append({"role": "assistant", "content": optimized_latex})

        logger.info("Optimized LaTeX: %d chars", len(optimized_latex))

        # ── Step 2: Compilation check ─────────────────────────────
        compile_error, page_count = await _compile_check(optimized_latex)

        if compile_error:
            logger.info("Asking Claude to fix compilation error...")
            fix_prompt = f"""The LaTeX you returned failed to compile with this error:

```
{compile_error}
```

Find and fix the issue. Common causes:
- \\resumeItem placed directly inside \\resumeSubHeadingListStart without a \\resumeItemListStart wrapper
- Custom command called with wrong number of arguments
- Bare text inside an itemize/enumerate without \\item
- Unbalanced braces

Return ONLY the complete corrected LaTeX. No explanations, no markdown fences."""

            conversation.append({"role": "user", "content": fix_prompt})
            optimized_latex = _call_claude(OPTIMIZER_SYSTEM_PROMPT, conversation)
            conversation.append({"role": "assistant", "content": optimized_latex})

            compile_error, page_count = await _compile_check(optimized_latex)
            if compile_error:
                logger.warning("Fix attempt failed — returning last version")

        # ── Step 3: One-page check ────────────────────────────────
        if page_count > 1:
            logger.info("Resume is %d pages — asking Claude to shrink to 1 page...", page_count)
            shrink_prompt = f"""The LaTeX you returned compiles but produces {page_count} pages. It MUST fit on exactly 1 page.

Apply these reduction strategies (Phase 4 from your instructions):

Reduction priority (cut first → cut last):
1. Oldest or least relevant experience details
2. Publications (keep if research role, summarize to 1-2 lines otherwise)
3. Additional/Awards section (keep most impressive only)
4. Reduce bullet points per role (3 max for older roles)
5. Consolidate similar skills

Space-saving LaTeX techniques:
- Reduce vertical spacing with \\vspace{{-Xpt}} adjustments
- Tighten margins (minimum 0.5in)
- Use 10-11pt font (never below 10pt)
- Remove blank lines that create extra space

Do NOT degrade the content quality — preserve the optimized wording and keywords.

Return ONLY the complete corrected LaTeX that fits on 1 page. No explanations, no markdown fences."""

            conversation.append({"role": "user", "content": shrink_prompt})
            optimized_latex = _call_claude(OPTIMIZER_SYSTEM_PROMPT, conversation)
            conversation.append({"role": "assistant", "content": optimized_latex})

            compile_error, page_count = await _compile_check(optimized_latex)
            if compile_error:
                logger.warning("Shrunk version failed to compile — attempting fix...")
                fix_prompt = f"""The LaTeX failed to compile:

```
{compile_error}
```

Fix the error and return ONLY the complete corrected LaTeX."""
                conversation.append({"role": "user", "content": fix_prompt})
                optimized_latex = _call_claude(OPTIMIZER_SYSTEM_PROMPT, conversation)
                _, page_count = await _compile_check(optimized_latex)

            if page_count > 1:
                logger.warning("Still %d pages after shrink — returning as-is", page_count)

        logger.info("=" * 60)
        logger.info("DONE — %d chars, %d page(s)", len(optimized_latex), page_count)
        logger.info("=" * 60)

        return {
            "optimized_latex": optimized_latex,
            "optimization_summary": "Resume optimized successfully for the target position.",
            "success": True,
        }

    except Exception as e:
        logger.error("OPTIMIZATION FAILED: %s", str(e), exc_info=True)
        return {
            "optimized_latex": latex,
            "optimization_summary": f"Optimization failed: {str(e)}",
            "success": False,
        }
