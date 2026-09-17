"""
Guard for the styling conventions in `gui.theme`.

Two things are checked:

1. **No retired spellings** in the files migrated to the shared constants. The
   scan walks `.classes()` / `.style()` call arguments in the AST rather than
   searching raw text, so `theme.py` legitimately *defining* a value and this
   module legitimately *listing* the retired spellings do not trip it.
2. **The migrated screens actually render with the constants.** The existing
   tests for both screens stop at an early return before any styled element is
   built, so they stay green even with the migration broken.

`GUARDED_FILES` widens one directory at a time as the sweep progresses.
"""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import polars as pl
from nicegui import ui
from nicegui.testing import User

from cibmangotree.analyzer_interface import AnalyzerParam, IntegerParam
from cibmangotree.analyzers.hashtags.hashtags_base.interface import (
    OUTPUT_COL_GINI,
    OUTPUT_COL_TIMESPAN,
)
from cibmangotree.analyzers.ngrams.ngrams_base.interface import (
    COL_NGRAM_ID,
    COL_NGRAM_LENGTH,
)
from cibmangotree.analyzers.ngrams.ngrams_stats.interface import (
    COL_NGRAM_DISTINCT_POSTER_COUNT,
    COL_NGRAM_TOTAL_REPS,
    COL_NGRAM_WORDS,
)
from cibmangotree.gui import theme
from cibmangotree.gui.components.analysis import AnalysisParamsCard
from cibmangotree.gui.dashboards.hashtags.plots import plot_gini_echart
from cibmangotree.gui.dashboards.ngrams.plots import plot_scatter_echart
from cibmangotree.gui.pages.analysis_workflow.run_step import RunAnalysisStep
from cibmangotree.gui.session import GuiSession
from cibmangotree.gui.theme import (
    CARD_CONTENT,
    CARD_PARAM,
    CHART_HIGHLIGHT,
    ICON_INFO,
    STYLE_CENTERED,
)

GUI_ROOT = Path(theme.__file__).parent

#: Files migrated to the shared constants, and therefore guarded. Not repo-wide:
#: the remaining GUI files are legitimately unmigrated until the sweep reaches
#: them.
GUARDED_FILES = [
    GUI_ROOT / "components" / "analysis.py",
    GUI_ROOT / "pages" / "analysis_workflow" / "run_step.py",
]

#: Retired class tokens mapped to what replaces them. Quasar spellings of
#: concerns Tailwind owns, plus `text-medium`, which neither framework defines.
RETIRED_CLASS_TOKENS = {
    "text-grey": "TEXT_MUTED",
    "text-grey-5": "TEXT_MUTED",
    "text-grey-6": "TEXT_MUTED (or ICON_INFO on an info affordance)",
    "text-grey-7": "TEXT_MUTED (or ICON_INFO on an info affordance)",
    "text-gray-500": "TEXT_MUTED",
    "text-gray-600": "TEXT_MUTED",
    "text-medium": "font-medium — `text-medium` is dead CSS in both frameworks",
    "no-shadow": "shadow-none",
    "text-bold": "font-bold",
    "text-weight-bold": "font-bold",
    "text-weight-medium": "font-medium",
    "q-mb-xs": "mb-1",
    "q-mb-sm": "mb-2",
    "q-mb-md": "mb-4",
    "q-mb-lg": "mb-6",
    "q-mt-xs": "mt-1",
    "q-mt-sm": "mt-2",
    "q-mt-md": "mt-4",
    "q-pa-md": "p-4",
}

#: CSS declarations that now have a named constant.
RETIRED_STYLE_DECLARATIONS = {
    "max-width: 960px": "STYLE_CENTERED",
    "min-width: 160px": "STYLE_LABEL_GUTTER",
}


def _style_literals(source: str) -> list[tuple[int, str, str]]:
    """Yield `(lineno, method, literal)` for `.classes()` / `.style()` arguments.

    Literal parts of f-strings are included, so a partially composed string such
    as `f"{TEXT_MUTED} q-mb-md"` is still inspected.
    """
    found: list[tuple[int, str, str]] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in ("classes", "style"):
            continue
        for arg in [*node.args, *(kw.value for kw in node.keywords)]:
            parts = arg.values if isinstance(arg, ast.JoinedStr) else [arg]
            for part in parts:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    found.append((part.lineno, node.func.attr, part.value))
    return found


def scan(paths: list[Path]) -> list[str]:
    """Report every retired spelling reaching a `.classes()` / `.style()` call."""
    problems: list[str] = []
    for path in paths:
        for lineno, method, literal in _style_literals(
            path.read_text(encoding="utf-8")
        ):
            where = f"{path.name}:{lineno}"
            if method == "classes":
                for token in literal.split():
                    if token in RETIRED_CLASS_TOKENS:
                        problems.append(
                            f"{where}  `{token}` is retired — "
                            f"use {RETIRED_CLASS_TOKENS[token]}"
                        )
            else:
                for declaration, constant in RETIRED_STYLE_DECLARATIONS.items():
                    if declaration in literal:
                        problems.append(
                            f"{where}  `{declaration}` is retired — use {constant}"
                        )
    return problems


# --- The guard -----------------------------------------------------------


def test_migrated_files_contain_no_retired_spellings() -> None:
    assert scan(GUARDED_FILES) == []


def test_scan_reports_a_reintroduced_spelling(tmp_path: Path) -> None:
    """A guard that cannot fail is worse than none."""
    offender = tmp_path / "regression.py"
    offender.write_text(
        'ui.label("x").classes("text-grey q-mb-md")\n'
        'ui.column().style("max-width: 960px; margin: 0 auto;")\n',
        encoding="utf-8",
    )

    problems = scan([offender])

    assert len(problems) == 3
    assert any("`text-grey` is retired" in p for p in problems)
    assert any("`q-mb-md` is retired" in p for p in problems)
    assert any("`max-width: 960px` is retired" in p for p in problems)


# --- The migrated screens actually render with the constants -------------


def _assert_styled(element, constant: str) -> None:
    """The constant's tokens are applied, and no *extra* retired token is.

    Tokens the constant itself owns are exempt: `ICON_INFO` is spelled
    `text-grey-7`, which is retired only as a hand-typed literal. Telling those
    apart is the AST scan's job, at the source level where it can.
    """
    expected = set(constant.split())
    applied = set(element.classes)
    assert expected <= applied, f"expected {constant!r}, got {sorted(applied)}"

    stray = (applied - expected) & RETIRED_CLASS_TOKENS.keys()
    assert not stray, f"retired tokens applied alongside {constant!r}: {sorted(stray)}"


async def test_populated_params_card_uses_shared_constants(user: User) -> None:
    params = [
        AnalyzerParam(
            id="window",
            human_readable_name="Window",
            description="How many rows to consider",
            type=IntegerParam(min=1, max=10),
        )
    ]

    @ui.page("/params-card-styles")
    def page() -> None:
        AnalysisParamsCard(params=params, default_values={"window": 3})

    await user.open("/params-card-styles")

    _assert_styled(next(iter(user.find(kind=ui.card).elements)), CARD_PARAM)
    _assert_styled(next(iter(user.find(kind=ui.icon).elements)), ICON_INFO)


async def test_valid_run_summary_uses_shared_constants(
    user: User, gui_session: GuiSession
) -> None:
    analyzer = MagicMock()
    analyzer.name = "Test Analyzer"
    gui_session.selected_analyzer = analyzer
    gui_session.column_mapping = {"user_id": "author"}
    gui_session.analysis_params = {}

    step = RunAnalysisStep(gui_session, MagicMock())

    @ui.page("/run-step-styles")
    def page() -> None:
        step.render()

    await user.open("/run-step-styles")

    _assert_styled(next(iter(user.find(kind=ui.card).elements)), CARD_CONTENT)

    expected = {
        part.split(":", 1)[0].strip(): part.split(":", 1)[1].strip()
        for part in STYLE_CENTERED.split(";")
        if part.strip()
    }
    assert any(
        expected.items() <= column.style.items()
        for column in user.find(kind=ui.column).elements
    ), "no column carries STYLE_CENTERED"


# --- Chart colours -------------------------------------------------------


def test_every_chart_highlight_is_the_same_constant() -> None:
    """One concept, one value — across both dashboards and every series."""
    gini = plot_gini_echart(
        pl.DataFrame(
            {
                OUTPUT_COL_TIMESPAN: [datetime(2024, 1, 1), datetime(2024, 1, 2)],
                OUTPUT_COL_GINI: [0.1, 0.9],
                "gini_smooth": [0.2, 0.8],
            }
        ),
        smooth=True,
    )
    scatter = plot_scatter_echart(
        pl.DataFrame(
            {
                COL_NGRAM_ID: [0, 1, 2],
                COL_NGRAM_LENGTH: [1, 2, 3],
                COL_NGRAM_DISTINCT_POSTER_COUNT: [5, 5, 5],
                COL_NGRAM_TOTAL_REPS: [10, 10, 10],
                COL_NGRAM_WORDS: ["w", "w", "w"],
            }
        )
    )

    emphasis = {
        series["emphasis"]["itemStyle"]["color"]
        for option in (gini, scatter)
        for series in option["series"]
    }
    assert emphasis == {CHART_HIGHLIGHT}
