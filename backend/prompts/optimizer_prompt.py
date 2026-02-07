import os
import logging

logger = logging.getLogger("resume_optimizer")

# Load system prompt from prompt.md at module load time
_PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt.md")

with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
    OPTIMIZER_SYSTEM_PROMPT = f.read()

logger.info("Loaded system prompt from %s (%d chars)", _PROMPT_PATH, len(OPTIMIZER_SYSTEM_PROMPT))


def get_optimization_prompt(latex: str, job_description: str) -> str:
    return f"""Please optimize the following LaTeX resume for this job description.

## Job Description:
{job_description}

## Current LaTeX Resume:
{latex}

## Instructions:
1. Follow every phase in your system prompt (Job Analysis → Gap Analysis → Optimization → One-Page Enforcement → Keyword Check).
2. Before returning the LaTeX, run the SELF-VALIDATION CHECKLIST from your system prompt. If any check fails, fix it before outputting.
3. Pay special attention to CRITICAL LATEX RULES — count arguments for every custom command, ensure list environments only contain \\item entries, and verify all braces are balanced.
4. Return ONLY the complete, compilable LaTeX code. No markdown fences, no explanations, no commentary."""
