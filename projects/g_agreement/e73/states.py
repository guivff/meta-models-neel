"""CPU-only E73 labels at exclusive Unicode-character endpoints.

A=0 and B=1 follow §191's order. State is measured *after* the read token.
The full document is used to establish syntax; no source text is rewritten.

Implementation conventions, to be frozen before sampling:
* W1 uses Python ``tokenize`` STRING spans (not quote-count parity). Python
  f-strings and JavaScript template interpolations are excluded as ambiguous;
  ordinary/raw/byte/triple strings and non-interpolated templates are supported.
  The completed closing delimiter is outside; an opening delimiter is inside.
* W2 counts (), [], {} outside strings, comments and JS regex literals. Unmatched
  closing brackets invalidate subsequent structural labels. Depth 0 or 2 is
  unlabelled. F-string/interpolated-template spans are unlabelled for W1/W2/W4.
* Python W4 uses ``ast.Call`` argument spans on syntactically valid documents;
  syntax-invalid documents have no W4 labels. Outside calls, only positions at
  bracket depth zero are statement-level. JS W4 uses lexical call frames and
  excludes grouping, arrays, object literals, declarations and arrow parameters;
  ordinary statement blocks do not change statement level. Strings/comments do
  not manufacture calls. A completed closing parenthesis is outside its call.
* W3 counts leading ASCII spaces in the current prefix line; leading tabs/form
  feeds are unlabelled. W5 counts Unicode characters since the latest newline,
  including the read token (zero immediately after a newline).
* W6 recognises pipe tables with a header and a GFM separator row, excludes
  fenced code and separator rows, and ignores escaped / inline-code pipes. An
  opening outer pipe is not a column; after an internal pipe the next column is
  current. A completed closing outer pipe is outside the table row.
* W7 labels Python/JavaScript as code and WikiText/prose as prose. Markdown is
  used for W6 and W5, not as a prose surrogate. W8 only accepts the sampler's
  frozen-title membership result (sports/science), never classifies body text.

``None`` means inapplicable, between bins, or conservatively ambiguous. The
caller must retain exclusion counts and must never coerce it to either class.
"""
from __future__ import annotations

import ast
import bisect
import io
import re
import sys
import token
import tokenize
from dataclasses import dataclass


STATE_VALUES = {
    "W1": ("inside an unclosed string literal", "not inside an unclosed string literal"),
    "W2": ("exactly 1 unclosed bracket", "at least 3 unclosed brackets"),
    "W3": ("at most 4 leading spaces", "at least 12 leading spaces"),
    "W4": ("inside call arguments", "at statement level"),
    "W5": ("at most 15 characters on the current line", "at least 55 characters on the current line"),
    "W6": ("markdown table column 1", "markdown table column at least 3"),
    "W7": ("code", "prose"),
    "W8": ("sports", "science"),
}


@dataclass(frozen=True)
class _Tok:
    value: str
    start: int
    end: int
    kind: str = "code"


def _lines(text: str) -> list[int]:
    return [0] + [m.end() for m in re.finditer("\n", text)]


def _py_lex(text: str):
    starts = _lines(text)
    tokens: list[_Tok] = []
    strings: list[tuple[int, int]] = []
    ambiguous: list[tuple[int, int]] = []
    bad_from = len(text) + 1
    f_depth, f_start = 0, 0
    fstring_start = getattr(token, "FSTRING_START", -1)
    fstring_end = getattr(token, "FSTRING_END", -1)

    def pos(rc):
        row, col = rc
        return min(len(text), starts[min(row - 1, len(starts) - 1)] + col)

    try:
        for t in tokenize.generate_tokens(io.StringIO(text).readline):
            a, b = pos(t.start), pos(t.end)
            # Python 3.12+ exposes interpolation as normal code tokens between
            # FSTRING_START / END. Suppress the complete nested f-string so its
            # interpolation brackets cannot contaminate the surrounding depth.
            if t.type == fstring_start:
                if f_depth == 0:
                    f_start = a
                f_depth += 1
                continue
            if f_depth:
                if t.type == fstring_end:
                    f_depth -= 1
                    if f_depth == 0:
                        ambiguous.append((f_start + 1, b))
                        tokens.append(_Tok(text[f_start:b], f_start, b, "string"))
                continue
            if t.type == token.STRING:
                m = re.match(r"(?i)([rubf]*)(\"\"\"|'''|\"|')", t.string)
                if m is None:
                    ambiguous.append((a, b))
                    continue
                prefix, quote = m.groups()
                if "f" in prefix.lower():
                    ambiguous.append((a + 1, b))
                else:
                    opening_end = a + len(prefix) + len(quote)
                    strings.append((opening_end, b))
                    if len(quote) > 1:
                        ambiguous.append((a + len(prefix) + 1, opening_end))
                tokens.append(_Tok(t.string, a, b, "string"))
            elif t.type == token.COMMENT:
                tokens.append(_Tok(t.string, a, b, "comment"))
            elif t.type == token.ERRORTOKEN and not t.string.isspace():
                # An incomplete single-quoted literal is not a valid STRING.
                # Exclude the suffix instead of pretending its quote is closed.
                bad_from = min(bad_from, a + 1)
            elif t.type in (token.NAME, token.NUMBER, token.OP):
                tokens.append(_Tok(t.string, a, b))
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        if isinstance(exc, tokenize.TokenError) and len(exc.args) > 1:
            error_row, error_col = exc.args[1]
            # Python's C tokenizer (3.12+) reports these errors with 1-based
            # columns, unlike the old generate_tokens implementation.
            if sys.version_info >= (3, 12):
                error_col = max(0, error_col - 1)
            a = pos((error_row, error_col))
            if "multi-line string" in str(exc.args[0]):
                m = re.match(r"(?i)([rubf]*)(\"\"\"|''')", text[a:])
                if m and "f" not in m.group(1).lower():
                    opening_end = a + len(m.group(0))
                    strings.append((opening_end, len(text) + 1))
                    ambiguous.append((a + 1, opening_end))
                else:
                    bad_from = min(bad_from, a + 1)
            elif "multi-line statement" not in str(exc.args[0]):
                bad_from = min(bad_from, a + 1)
            # EOF in a bracketed statement is expected for truncated code;
            # tokens already emitted still establish its lexical state.
        else:
            row = getattr(exc, "lineno", None)
            bad_from = starts[min(max((row or 1) - 1, 0), len(starts) - 1)]
    if f_depth:
        ambiguous.append((f_start + 1, len(text) + 1))
    return tokens, strings, ambiguous, bad_from


def _py_calls(text: str) -> list[tuple[int, int]] | None:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return None
    starts = _lines(text)
    rows = text.splitlines(keepends=True)

    def pos(row, byte_col):
        # AST columns count UTF-8 bytes; tokenize / our offsets count characters.
        return starts[row - 1] + len(rows[row - 1].encode("utf-8")[:byte_col].decode("utf-8"))

    spans = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        begin = pos(node.func.end_lineno, node.func.end_col_offset)
        end = pos(node.end_lineno, node.end_col_offset)
        # Comments/newlines may intervene between the callable and '('.
        suffix = text[begin:end]
        for t in tokenize.generate_tokens(io.StringIO(suffix).readline):
            if t.type == token.OP and t.string == "(":
                row_starts = _lines(suffix)
                opening = begin + row_starts[t.start[0] - 1] + t.start[1]
                spans.append((opening + 1, end))
                break
    return spans


_JS_KEYWORDS_NOT_CALL = {
    "if", "for", "while", "switch", "catch", "with", "function", "typeof",
    "delete", "void", "return", "throw", "class", "superclass", "yield",
}
_JS_REGEX_PREFIX = {
    "(", "[", "{", "=", ":", ",", ";", "!", "?", "&&", "||", "??",
    "=>", "return", "throw", "case", "yield", "in", "of", "~",
    "/", "*", "+", "-", "%", "&", "|", "^", "<", ">", "==", "!=",
}


def _after_js_control(tokens: list[_Tok]) -> bool:
    """A slash after if/while/for (...) starts a statement, not division."""
    code = [t.value for t in tokens if t.kind != "comment"]
    if not code or code[-1] != ")":
        return False
    depth = 0
    for i in range(len(code) - 1, -1, -1):
        if code[i] == ")":
            depth += 1
        elif code[i] == "(":
            depth -= 1
            if depth == 0:
                return i > 0 and code[i - 1] in {"if", "while", "for", "with"}
    return False


def _js_lex(text: str):
    """String/comment/regex tracker; interpolation is explicitly unlabelled."""
    out: list[_Tok] = []
    strings = []
    ambiguous = []
    n, i = len(text), 0
    bad_from = n + 1
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if text.startswith("//", i):
            end = text.find("\n", i + 2)
            end = n if end < 0 else end
            out.append(_Tok(text[i:end], i, end, "comment"))
            i = end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            out.append(_Tok(text[i:end], i, end, "comment"))
            i = end
            continue
        if c in "'\"`":
            start, quote = i, c
            i += 1
            interpolated = False
            closed = False
            while i < n:
                if text[i] == "\\":
                    i += min(2, n - i)
                elif text[i] == quote:
                    i += 1
                    closed = True
                    break
                elif quote != "`" and text[i] in "\r\n":
                    bad_from = min(bad_from, start + 1)
                    break
                elif quote == "`" and text.startswith("${", i):
                    interpolated = True
                    # The remainder may contain nested template quotes; do not
                    # infer any lexical state after an unsupported interpolation.
                    ambiguous.append((start, n + 1))
                    bad_from = min(bad_from, start + 1)
                    i = n
                else:
                    i += 1
            if not interpolated:
                strings.append((start + 1, i if closed else n + 1))
            out.append(_Tok(text[start:i], start, i, "string"))
            continue
        previous = next((t.value for t in reversed(out) if t.kind != "comment"), None)
        if c == "/" and (previous is None or previous in _JS_REGEX_PREFIX or _after_js_control(out)):
            start = i
            i += 1
            in_class, closed = False, False
            while i < n and text[i] not in "\r\n":
                if text[i] == "\\":
                    i += min(2, n - i)
                    continue
                if text[i] == "[":
                    in_class = True
                elif text[i] == "]":
                    in_class = False
                elif text[i] == "/" and not in_class:
                    i += 1
                    closed = True
                    break
                i += 1
            if closed:
                while i < n and text[i].isalpha():
                    i += 1
            else:
                bad_from = min(bad_from, start + 1)
            out.append(_Tok(text[start:i], start, i, "regex"))
            continue
        if c.isalpha() or c in "_$" or ord(c) > 127:
            end = i + 1
            while end < n and (text[end].isalnum() or text[end] in "_$" or ord(text[end]) > 127):
                end += 1
            out.append(_Tok(text[i:end], i, end, "name"))
            i = end
            continue
        op = next((s for s in ("=>", "?.", "&&", "||", "??", "==", "!=", "++", "--", "**") if text.startswith(s, i)), c)
        out.append(_Tok(op, i, i + len(op)))
        i += len(op)
    return out, strings, ambiguous, bad_from


def _brackets(tokens: list[_Tok], language: str):
    """Return endpoint events (position, depth, W4 lexical value)."""
    code = [t for t in tokens if t.kind not in ("string", "comment", "regex")]
    matching: dict[int, int] = {}
    stack_indices = []
    for i, t in enumerate(code):
        if t.value in ("(", "[", "{"):
            stack_indices.append(i)
        elif t.value in (")", "]", "}") and stack_indices:
            j = stack_indices[-1]
            if code[j].value == {")": "(", "]": "[", "}": "{"}[t.value]:
                stack_indices.pop()
                matching[j] = i
    events = [(0, 0, 1)]
    stack: list[tuple[str, str]] = []
    invalid = False
    for i, t in enumerate(code):
        if t.value in ("(", "[", "{"):
            role = "group"
            prev = code[i - 1] if i else None
            before = code[i - 2] if i > 1 else None
            if language == "javascript":
                if t.value == "(":
                    j = matching.get(i)
                    following = code[j + 1].value if j is not None and j + 1 < len(code) else None
                    declaration = following in ("{", "=>") or (before and before.value in ("function", "*"))
                    if prev and (prev.kind == "name" or prev.value in (")", "]", "?.")) and prev.value not in _JS_KEYWORDS_NOT_CALL and not declaration:
                        role = "call"
                elif t.value == "{":
                    if prev is None or prev.value in (";", "}", ")", "=>", "else", "try", "finally", "do") or (before and before.value == "class"):
                        role = "block"
            stack.append((t.value, role))
        elif t.value in (")", "]", "}"):
            expected = {")": "(", "]": "[", "}": "{"}[t.value]
            if not stack or stack[-1][0] != expected:
                invalid = True
            else:
                stack.pop()
        else:
            continue
        if invalid:
            events.append((t.end, -1, None))
        else:
            call = 0 if any(role == "call" for _, role in stack) else (1 if all(role == "block" for _, role in stack) else None)
            events.append((t.end, len(stack), call))
    return events


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for a, b in sorted(spans):
        if a >= b:
            continue
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return merged


def _contains(spans: list[tuple[int, int]], offset: int) -> bool:
    """Binary lookup in merged intervals, including nested call spans."""
    i = bisect.bisect_right(spans, (offset, float("inf"))) - 1
    return i >= 0 and offset < spans[i][1]


def _pipe_positions(line: str) -> list[int]:
    positions = []
    i, ticks = 0, 0
    while i < len(line):
        if line[i] == "\\":
            i += 2
            continue
        if line[i] == "`":
            end = i + 1
            while end < len(line) and line[end] == "`":
                end += 1
            width = end - i
            if ticks == 0:
                ticks = width
            elif ticks == width:
                ticks = 0
            i = end
            continue
        if line[i] == "|" and not ticks:
            positions.append(i)
        i += 1
    return positions


def _table_rows(text: str) -> dict[int, tuple[str, list[int], int]]:
    rows = text.splitlines(keepends=True)
    available = []
    fence = None
    for row in rows:
        m = re.match(r"^ {0,3}(`{3,}|~{3,})", row)
        if m:
            if fence is None:
                fence = (m.group(1)[0], len(m.group(1)))
            elif m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]:
                fence = None
            available.append(False)
        else:
            available.append(fence is None and not row.startswith(("    ", "\t")))
    result = {}
    start_offsets = _lines(text)
    for i in range(1, len(rows)):
        if not available[i] or not available[i - 1]:
            continue
        separator = rows[i].strip().strip("|")
        cells = separator.split("|")
        if len(cells) < 2 or not all(re.fullmatch(r"\s*:?-{3,}:?\s*", c) for c in cells):
            continue
        header = rows[i - 1].rstrip("\r\n")
        header_pipes = _pipe_positions(header)
        if not header_pipes:
            continue
        header_columns = len(header_pipes) + 1 - int(not header[:header_pipes[0]].strip()) - int(not header[header_pipes[-1] + 1:].strip())
        if header_columns != len(cells):
            continue
        result.pop(start_offsets[i], None)
        for j in [i - 1] + list(range(i + 1, len(rows))):
            row = rows[j].rstrip("\r\n")
            pipes = _pipe_positions(row)
            if not available[j] or not pipes or not row.strip():
                break
            result[start_offsets[j]] = (row, pipes, header_columns)
    return result


def extract_states(text: str, language: str, offsets: list[int], *, title: str = "", topic: str | None = None) -> dict[str, list[int | None]]:
    """Extract applicable W labels, aligned with exclusive character endpoints.

    ``topic`` must come from exact membership of the committed title list;
    ``title`` is accepted for a stable sampler interface, not classified here.
    Invalid offsets and unknown source languages raise, never silently clip.
    """
    del title
    aliases = {"py": "python", ".py": "python", "js": "javascript", ".js": "javascript", "md": "markdown", ".md": "markdown", "wikitext": "prose", "wikipedia": "prose", "text": "prose"}
    language = aliases.get(language.lower(), language.lower())
    if language not in {"python", "javascript", "markdown", "prose"}:
        raise ValueError(f"unsupported source language: {language}")
    if any(not isinstance(o, int) or isinstance(o, bool) or o < 1 or o > len(text) for o in offsets):
        raise ValueError("offsets must be integer exclusive endpoints in [1, len(text)]")
    if topic not in (None, "sports", "science"):
        raise ValueError("topic must be sports, science, or None")
    result: dict[str, list[int | None]] = {"W5": []}
    starts = _lines(text)
    code = language in ("python", "javascript")
    if code:
        lex = _py_lex(text) if language == "python" else _js_lex(text)
        tokens, strings, ambiguous, bad_from = lex
        strings, ambiguous = _merge(strings), _merge(ambiguous)
        events = _brackets(tokens, language)
        event_offsets = [e[0] for e in events]
        calls = _py_calls(text) if language == "python" else None
        if calls is not None:
            calls = _merge(calls)
        result.update({s: [] for s in ("W1", "W2", "W3", "W4", "W7")})
    elif language == "markdown":
        table = _table_rows(text)
        result["W6"] = []
    else:
        result["W7"] = []
        if topic is not None:
            result["W8"] = []
    for offset in offsets:
        line_start = starts[bisect.bisect_right(starts, offset) - 1]
        line_prefix = text[line_start:offset]
        length = len(line_prefix)
        result["W5"].append(0 if length <= 15 else (1 if length >= 55 else None))
        if code:
            unknown = offset >= bad_from or _contains(ambiguous, offset)
            inside = _contains(strings, offset)
            result["W1"].append(None if unknown else (0 if inside else 1))
            _, depth, js_call = events[bisect.bisect_right(event_offsets, offset) - 1]
            result["W2"].append(None if unknown or depth < 0 else (0 if depth == 1 else (1 if depth >= 3 else None)))
            leading = re.match(r"[ \t\f]*", line_prefix).group(0)
            indent = len(leading)
            result["W3"].append(None if "\t" in leading or "\f" in leading else (0 if indent <= 4 else (1 if indent >= 12 else None)))
            if unknown or depth < 0:
                call_label = None
            elif language == "python":
                call_label = None if calls is None else (0 if _contains(calls, offset) else (1 if depth == 0 else None))
            else:
                call_label = js_call
            result["W4"].append(call_label)
            result["W7"].append(0)
        elif language == "markdown":
            entry = table.get(line_start)
            label = None
            if entry is not None:
                row, pipes, columns = entry
                col_offset = offset - line_start
                leading_outer = row[:pipes[0]].strip() == ""
                trailing_outer = row[pipes[-1] + 1:].strip() == ""
                if not (trailing_outer and col_offset > pipes[-1]):
                    column = 1 + sum(p < col_offset for p in pipes) - int(leading_outer)
                    if 1 <= column <= columns:
                        label = 0 if column == 1 else (1 if column >= 3 else None)
            result["W6"].append(label)
        else:
            result["W7"].append(1)
            if "W8" in result:
                result["W8"].append(0 if topic == "sports" else 1)
    return result
