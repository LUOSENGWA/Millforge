"""Millforge compiler pipeline — six pure stages (MF-6).

Parse → Validate → Budget → Compile → Render → Verify

Every stage is a pure function: same inputs (document, template library,
explicit clock) → same outputs, no wall clock, no LLM, no writes, no global
mutation. Any stage raising ``PipelineError`` = the whole pipeline fails and
nothing is emitted (no truncated output).

The CLI and the ``compile_team`` / ``validate_team`` module API live in
``compiler/millforge-compile.py`` (thin facade: I/O, file writes, exit codes).
"""
from pipeline.pipeline import (  # noqa: F401
    BUDGETS,
    EXIT_BUDGET,
    EXIT_COMPILE,
    EXIT_OK,
    EXIT_RENDER,
    EXIT_USAGE,
    EXIT_VALIDATE,
    EXIT_VERIFY,
    LANGS,
    PipelineError,
    SCRUB_WORDS,
    STAGES,
    TIER_CAPS,
    TemplateLib,
    budget,
    compile_stage,
    default_root,
    estimate_tokens,
    load_index,
    load_team_schema,
    parse,
    render_stage,
    run_pipeline,
    tier_exceeded,
    validate,
    verify_stage,
)
