"""Freeze 50 independently labelled, hand-checkable examples per E73 state.

The marker is an exclusive character endpoint, immediately after the read text.
These are extractor unit fixtures, never candidates for the real corpus bank.
Expected labels are authored here, not obtained from the extractor under test.
"""
from __future__ import annotations

import json
from pathlib import Path

MARK = "⟦READ⟧"


def examples():
    out = []

    def add(state, language, marked, label, reason, **metadata):
        assert marked.count(MARK) == 1
        offset = marked.index(MARK)
        out.append(dict(id=f"{state}-{sum(r['state'] == state for r in out)+1:02}",
                        state=state, language=language,
                        text=marked.replace(MARK, ""), offset=offset,
                        expected=label, reason=reason, **metadata))

    for i, word in enumerate(["apple", "river", "copper", "window", "planet"]):
        # 5 positive and 5 negative lexical cases, with five distinct contents.
        for language, marked, label, reason in [
            ("python", f'x = "{word}{MARK} rest"\n', 0, "Inside a double-quoted Python literal."),
            ("python", f"x = '{word}{MARK} rest'\n", 0, "Inside a single-quoted Python literal."),
            ("python", f'x = """first\n{word}{MARK}\nlast"""\n', 0, "Inside a multiline triple-quoted literal."),
            ("python", f'x = "escaped \\" {word}{MARK} end"\n', 0, "Escaped quote does not close the literal."),
            ("javascript", f'const x = "{word}{MARK} rest";\n', 0, "Inside a JavaScript string."),
            ("python", f'x = "{word}"{MARK}\n', 1, "Closing quote has already been consumed."),
            ("python", f'{word} = {i+3}{MARK}\n', 1, "Numeric expression outside a string."),
            ("python", f'# "{word}{MARK}\nx = 1\n', 1, "Quote in a comment is not a string opener."),
            ("javascript", f'const x = "{word}";{MARK}\n', 1, "JavaScript string has closed."),
            ("python", f'x = "{word}"\ny = x{MARK}\n', 1, "Later statement is outside the closed literal."),
        ]:
            add("W1", language, marked, label, reason)
        for depth in [1, 3]:
            for pattern in range(5):
                if pattern == 0:
                    marked = f'x = {"["*depth}{i+1}{MARK}{"]"*depth}\n'
                elif pattern == 1:
                    marked = f'x = {"("*depth}{i+1}{MARK}{")"*depth}\n'
                elif pattern == 2:
                    marked = f'x = {"["*depth}"{word} (["{MARK}{"]"*depth}\n'
                elif pattern == 3:
                    marked = f'x = {"["*depth}\n # ] ) ignored\n {i+1}{MARK}{"]"*depth}\n'
                else:
                    marked = f'x = {"["*depth}({i+1}){MARK}{"]"*depth}\n'
                add("W2", "python", marked, 0 if depth == 1 else 1,
                    f"Exactly {depth} unmatched code delimiters; strings/comments excluded.")
        for spaces in [0, 1, 2, 3, 4, 12, 13, 16, 20, 24]:
            add("W3", "python", f'if ready:\n{" "*spaces}{word}{MARK} = {i}\n',
                int(spaces >= 12), f"Current line has {spaces} leading spaces.")
        for marked, label, reason in [
            (f'f({word}{MARK}, 2)\n', 0, "Within a positional call argument."),
            (f'f(key={word}{MARK})\n', 0, "Within a keyword call argument."),
            (f'obj.method({word}{MARK})\n', 0, "Within a method call argument."),
            (f'f([{word}{MARK}, 2])\n', 0, "A list nested inside a call argument."),
            (f'f(g({word}{MARK}))\n', 0, "Inside nested call arguments."),
            (f'{word}{MARK} = {i}\n', 1, "Top-level assignment target."),
            (f'value = {word}{MARK}\n', 1, "Statement expression with no open call."),
            (f'f({word})\nnext_value{MARK} = 2\n', 1, "New statement after a completed call."),
            (f'import {word}{MARK}\n', 1, "Import at statement level."),
            (f'{word}{MARK}\n', 1, "Bare expression at statement level."),
        ]:
            add("W4", "python", marked, label, reason)
        for length in [1, 5, 10, 14, 15, 55, 56, 60, 80, 100]:
            add("W5", "prose", f'Previous {word}.\n' + (word[0]*length) + MARK + ' trailing text\n',
                int(length >= 55), f"{length} characters since the last newline.")
        for column in [1, 3]:
            for pattern in range(5):
                leading = "|" if pattern != 1 else ""
                trailing = "|" if pattern != 1 else ""
                cells = [word, str(i+1), "value", "end"]
                cells[column-1] += MARK
                if pattern == 2:
                    cells[0] = "escaped \\| " + cells[0]
                if pattern == 3:
                    cells[0] = "`a|b` " + cells[0]
                header = "h1 | h2 | h3 | h4"
                separator = "--- | :---: | ---: | ---"
                marked = f'{leading}{header}{trailing}\n{leading}{separator}{trailing}\n{leading}' + " | ".join(cells) + f'{trailing}\n'
                if pattern == 4:
                    marked = f'# Table {i}\n\n' + marked
                add("W6", "markdown", marked, 0 if column == 1 else 1,
                    f"Column {column} of a table with a separator row.")
        for j in range(5):
            add("W7", "python" if j % 2 == 0 else "javascript",
                f'{word}_{j} = {i+j}{MARK}\n', 0, "Source file is code.")
            add("W7", "prose", f'The {word} appears in passage {j}.{MARK}\n',
                1, "Source is a WikiText prose article.")
            add("W8", "prose", f'This sporting event has round {i+j}.{MARK}\n',
                0, "Frozen title classifier supplied sports membership.",
                title=f"Football {i}-{j}", topic="sports")
            add("W8", "prose", f'This scientific account has section {i+j}.{MARK}\n',
                1, "Frozen title classifier supplied science membership.",
                title=f"Physics {i}-{j}", topic="science")
    return out


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(examples(), indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
