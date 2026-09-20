"""Shared pure renderer contract for the docs build scripts.

Side-effect free by construction: stdlib only (re, csv, pathlib), no file
reads, no writes, no package imports at module level. verify.py imports
from here, never from the build scripts, so validation never triggers a
build. docs/build_dashboard.py delegates to these helpers; every check runs
across both pages before either output file is replaced.
"""
import csv
import re
from pathlib import Path

ANALYSIS_STEPS_COLUMNS = ['order', 'id', 'stage', 'question', 'why', 'inputs',
                          'method', 'assumptions', 'result', 'interpretation',
                          'conclusion', 'source']

ANALYSIS_STEPS_PATH = Path(__file__).resolve().parents[1] / 'results' / 'analysis_steps.csv'

_PLACEHOLDER_RE = re.compile(r'\{\{([A-Za-z0-9_]+)\}\}')
_KEY_RE = re.compile(r'^\{\{[A-Za-z0-9_]+\}\}$')


def _tokens(text):
    """Exact placeholder tokens in one template, e.g. {'{{X}}'}."""
    return {'{{' + m + '}}' for m in _PLACEHOLDER_RE.findall(text)}


def validate_render(templates, values_by_page):
    """Validate and render every page. templates maps template name to its
    text; values_by_page maps template name to {placeholder: value}.
    Returns {template name: rendered text}. Fails on: page-set mismatch
    (a template with no values entry, or values for an unknown template),
    malformed keys, computed keys no template uses, placeholders left
    unfilled, and values supplied under the wrong page. Key comparison
    uses exact placeholder tokens ({{NAME}}), never substrings. No I/O."""
    want = set(templates)
    got = set(values_by_page)
    if want != got:
        raise ValueError(
            f'template/value page-set mismatch: templates without values '
            f'{sorted(want - got)[:8]}, values without template '
            f'{sorted(got - want)[:8]}')
    page_tokens = {}
    union_tokens = set()
    for name, text in templates.items():
        toks = _tokens(text)
        page_tokens[name] = toks
        union_tokens |= toks
    for page, values in values_by_page.items():
        for key in values:
            if not _KEY_RE.match(key):
                raise ValueError(
                    f'{page}: malformed placeholder key (want {{{{NAME}}}}): '
                    f'{key!r}')
            if key not in union_tokens:
                raise ValueError(
                    f'computed key never placed in any template: {key}')
    rendered = {}
    for name in templates:
        toks = page_tokens[name]
        keys = set(values_by_page[name])
        missing = sorted(toks - keys)
        if missing:
            raise ValueError(
                f'{name}: placeholders left unfilled: {missing[:8]}')
        extra = sorted(keys - toks)
        if extra:
            raise ValueError(
                f'{name}: values with no placeholder in this template '
                f'(wrong page?): {extra[:8]}')
        html = templates[name]
        for key, val in values_by_page[name].items():
            html = html.replace(key, str(val))
        still = sorted(_tokens(html))
        if still:
            raise ValueError(
                f'{name}: placeholders remain after rendering: {still[:8]}')
        rendered[name] = html
    return rendered


def escape_html(text):
    """Escape one cell of the analysis-steps record for HTML output."""
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def render_steps_sections(rows):
    """Build one <details> section per analysis step, in numeric order,
    each exposing     question, reason, inputs/timing, method and assumptions,
    measured result, interpretation, decision, and source. rows are dicts
    with the 12 contract columns. Returns HTML. All cells HTML-escaped.
    No I/O, no fallback rows."""
    parts = []
    for r in sorted(rows, key=lambda d: float(d['order'])):
        e = {k: escape_html(r.get(k, '')) for k in ANALYSIS_STEPS_COLUMNS}
        parts.append(
            f'<details id="step-{e["id"]}">'
            f'<summary><b>{e["order"]}. {e["question"]}</b> '
            f'<span class="sub">{e["stage"]} · {e["id"]}</span></summary>'
            f'<dl>'
            f'<dt>Reason</dt><dd>{e["why"]}</dd>'
            f'<dt>Inputs and timing</dt><dd>{e["inputs"]}</dd>'
            f'<dt>Method and assumptions</dt><dd>{e["method"]} '
            f'Assumptions: {e["assumptions"]}</dd>'
            f'<dt>Measured result</dt><dd>{e["result"]}</dd>'
            f'<dt>Interpretation</dt><dd>{e["interpretation"]}</dd>'
            f'<dt>Decision</dt><dd>{e["conclusion"]}</dd>'
            f'<dt>Source</dt><dd>{e["source"]}</dd>'
            f'</dl></details>')
    return '\n'.join(parts)


def validate_analysis_steps(path, expected_ids=None):
    """Gate the analysis-steps record written by the statistics agent.
    Raises ValueError when the file is missing, its columns differ from
    the 12-column contract, it holds no rows, or (when expected_ids is
    given) it does not cover every declared step id from all four
    notebooks. Returns the row count. Reads one CSV; writes nothing and
    fabricates no fallback rows."""
    p = Path(path)
    if not p.exists():
        raise ValueError(f'analysis_steps record missing: {p}')
    with p.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ANALYSIS_STEPS_COLUMNS:
            raise ValueError(
                f'analysis_steps columns {reader.fieldnames} '
                f'!= contract {ANALYSIS_STEPS_COLUMNS}')
        rows = list(reader)
    if not rows:
        raise ValueError('analysis_steps record holds no rows')
    seen = [r['id'] for r in rows]
    dupes = sorted({i for i in seen if seen.count(i) > 1})
    if dupes:
        raise ValueError(f'analysis_steps record has duplicate ids: {dupes[:12]}')
    try:
        orders = [float(r['order']) for r in rows]
    except ValueError:
        raise ValueError('analysis_steps record has non-numeric order values')
    if orders != sorted(orders):
        raise ValueError('analysis_steps record is not in numeric order')
    if expected_ids is not None:
        have = {r['id'] for r in rows}
        missing = [i for i in expected_ids if i not in have]
        if missing:
            raise ValueError(
                f'analysis_steps record missing step ids: {missing[:12]}')
        extra = sorted(have - set(expected_ids))
        if extra:
            raise ValueError(
                f'analysis_steps record has undeclared step ids: {extra[:12]}')
    return len(rows)
