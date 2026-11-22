"""Core logic for the Math Word Problem Solver (PS 26).

Flow: word problem -> prompt ("think step by step, final answer on last line")
      -> LLM -> parse steps / CHECK expression / FINAL ANSWER
      -> verify the arithmetic with sympy -> result dictionary.
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

import sympy
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
)

# ---------------------------------------------------------------- providers
# All four providers expose an OpenAI-compatible API, so one code path is enough.
PROVIDERS = {
    "Gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash",
        "env_key": "GEMINI_API_KEY",
    },
    "Groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    "OpenAI": {
        "base_url": None,
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "Ollama (local)": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "env_key": None,  # no key needed
    },
}

# ------------------------------------------------------------------- prompt
SYSTEM_PROMPT = """You are a patient maths tutor for school and first-year college students.
Solve the word problem the user gives you.

Think step by step. Use EXACTLY this output format and nothing else:

Step 1: <what you do and why, with the calculation>
Step 2: <what you do and why, with the calculation>
... (as many steps as needed)
CHECK: <ONE plain arithmetic expression that computes the final answer from the
numbers in the problem, using only digits, + - * / ( ) and decimal points>
FINAL ANSWER: <number with unit, on the last line>

Rules:
- Explain each step in simple words a student can follow.
- Do not skip any calculation.
- CHECK must contain no words, no units, no '=' sign, no percent sign (write 20/100 instead of 20%).
- The last line of your reply must be the FINAL ANSWER line.
- If the text is not a solvable maths problem, reply only: FINAL ANSWER: Not a maths problem."""

STEP_RE = re.compile(r"^\s*\**\s*Step\s*(\d+)\s*[:.)-]\s*\**\s*(.+)$", re.I)
CHECK_RE = re.compile(r"^\s*\**\s*CHECK\s*:\s*\**\s*(.+?)\s*\**\s*$", re.I)
FINAL_RE = re.compile(r"^\s*\**\s*FINAL\s*ANSWER\s*:\s*\**\s*(.+?)\s*\**\s*$", re.I)
NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")
SAFE_EXPR_RE = re.compile(r"^[0-9+\-*/().\s^]+$")


@dataclass
class SolveResult:
    steps: List[str] = field(default_factory=list)
    check_expression: Optional[str] = None
    final_answer: Optional[str] = None
    raw: str = ""
    verified: Optional[bool] = None      # True / False / None (could not verify)
    computed_value: Optional[str] = None
    verify_note: str = ""


# ------------------------------------------------------------------ parsing
def parse_response(text: str) -> SolveResult:
    """Split the model's reply into steps, CHECK expression and FINAL ANSWER."""
    res = SolveResult(raw=text)
    for line in text.splitlines():
        if (m := STEP_RE.match(line)):
            res.steps.append(m.group(2).strip())
        elif (m := CHECK_RE.match(line)):
            res.check_expression = m.group(1).strip().strip("`")
        elif (m := FINAL_RE.match(line)):
            res.final_answer = m.group(1).strip()
    if res.final_answer is None:  # fallback: use the last non-empty line
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        res.final_answer = lines[-1] if lines else ""
    return res


def first_number(text: str) -> Optional[float]:
    """Pull the first number out of text such as 'Rs. 1,250.50 per kg'."""
    m = NUM_RE.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


# ------------------------------------------------------------ verification
def safe_eval(expression: str) -> sympy.Expr:
    """Evaluate a pure-arithmetic expression with sympy.
    Only digits and + - * / ( ) . ^ are accepted, so arbitrary code cannot run."""
    expr = expression.replace("×", "*").replace("÷", "/").replace(",", "")
    if not SAFE_EXPR_RE.match(expr):
        raise ValueError("expression contains characters other than arithmetic")
    expr = expr.replace("^", "**")
    transformations = standard_transformations + (implicit_multiplication_application,)
    return parse_expr(expr, transformations=transformations, evaluate=True)


def verify(res: SolveResult, tol: float = 1e-2) -> SolveResult:
    """Re-compute the CHECK expression with sympy and compare to the final answer."""
    if not res.check_expression:
        res.verify_note = "No CHECK expression was given, so the arithmetic was not verified."
        return res
    try:
        value = safe_eval(res.check_expression)
        res.computed_value = str(sympy.N(value, 10)).rstrip("0").rstrip(".")
    except Exception as exc:  # noqa: BLE001 - show any parsing problem to the user
        res.verify_note = f"Could not evaluate the CHECK expression ({exc})."
        return res

    claimed = first_number(res.final_answer or "")
    if claimed is None:
        res.verify_note = "Final answer has no number to compare with."
        return res

    res.verified = abs(float(value) - claimed) <= max(tol, abs(claimed) * 1e-4)
    res.verify_note = (
        f"Python (sympy) computed {res.computed_value} and the LLM answered {claimed:g}: "
        + ("they MATCH." if res.verified else "they DO NOT match - re-check the steps.")
    )
    return res


# -------------------------------------------------------------- LLM calling
def get_client(provider: str, api_key: Optional[str] = None):
    """Create an OpenAI-compatible client for the chosen provider."""
    from openai import OpenAI  # imported here so tests run without the package

    cfg = PROVIDERS[provider]
    key = api_key or (os.getenv(cfg["env_key"]) if cfg["env_key"] else "ollama")
    if not key:
        raise RuntimeError(
            f"No API key found. Set {cfg['env_key']} in your .env file or paste it in the sidebar."
        )
    return OpenAI(api_key=key, base_url=cfg["base_url"])


def solve(problem: str, provider: str = "Gemini", model: Optional[str] = None,
          api_key: Optional[str] = None, client=None, temperature: float = 0.0) -> SolveResult:
    """Solve one word problem and verify it. `client` can be injected for tests."""
    problem = (problem or "").strip()
    if not problem:
        raise ValueError("Please enter a word problem.")
    client = client or get_client(provider, api_key)
    model = model or PROVIDERS[provider]["model"]

    reply = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Problem: {problem}"},
        ],
    )
    text = reply.choices[0].message.content or ""
    return verify(parse_response(text))
