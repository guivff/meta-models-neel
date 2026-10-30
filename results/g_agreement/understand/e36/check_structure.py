"""Independent lexical/structural inference for E36 structure prefixes.

No author import, family identifier, expected label, or frozen-bank access.
Unsupported or ambiguous states raise ValueError rather than guessing.
"""
import ast
import re


def _answer(value, **evidence):
    return {'value': value, 'evidence': evidence}


def _validate_text(text):
    if not isinstance(text, str) or not text or text[-1].isspace():
        raise ValueError('Expected a nonempty prefix ending at its read token')


def _python_lex(text):
    """Lex strings/comments separately; retain real punctuation with offsets."""
    tokens = []
    closed_strings = 0
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if c == '#':
            end = text.find('\n', i)
            if end < 0:
                if not text[i+1:].strip():
                    raise ValueError('Read token does not contain comment content')
                return tokens, 'comment', closed_strings
            i = end + 1
            continue
        if c in "\"'":
            start = i
            delimiter = c * (3 if text.startswith(c*3, i) else 1)
            if tokens and tokens[-1][0] == 'name' and tokens[-1][3] == i:
                prefix = tokens[-1][1].lower()
                if prefix in ('f', 'fr', 'rf', 't', 'tr', 'rt'):
                    raise ValueError('Interpolated literal requires a different parser')
            i += len(delimiter)
            while i < len(text):
                if text.startswith(delimiter, i):
                    i += len(delimiter)
                    closed_strings += 1
                    tokens.append(('string', '', start, i))
                    break
                if text[i] == '\\':
                    i += 2
                    continue
                if text[i] in '\r\n' and len(delimiter) == 1:
                    raise ValueError('A short string cannot contain an unescaped newline')
                i += 1
            else:
                return tokens, 'string', closed_strings
            continue
        if c.isalpha() or c == '_':
            match = re.match(r'[A-Za-z_][A-Za-z_0-9]*', text[i:])
            if not match:
                raise ValueError('Unsupported identifier')
            value = match.group()
            tokens.append(('name', value, i, i+len(value)))
            i += len(value)
            continue
        if c.isdigit():
            match = re.match(r'[0-9]+(?:\.[0-9]+)?', text[i:])
            value = match.group()
            tokens.append(('number', value, i, i+len(value)))
            i += len(value)
            continue
        tokens.append(('punct', c, i, i+1))
        i += 1
    return tokens, 'code', closed_strings


def _python_frames(tokens):
    frames = []
    previous = None
    before_previous = None
    excluded_names = {'if', 'while', 'for', 'return', 'yield', 'assert', 'in', 'not', 'and', 'or', 'lambda', 'with', 'except', 'match', 'case'}
    for token in tokens:
        kind, value, start, end = token
        if value in ('(', '[', '{') and kind == 'punct':
            call = value == '(' and previous is not None and (
                previous[0] == 'name' and previous[1] not in excluded_names
                and (before_previous is None or before_previous[1] not in ('def', 'class'))
                or previous[1] in (')', ']'))
            frames.append({'opening': value, 'call': call, 'commas': 0, 'offset': start, 'has_argument': False})
        elif value in (')', ']', '}') and kind == 'punct':
            if not frames or frames[-1]['opening'] != {')': '(', ']': '[', '}': '{'}[value]:
                raise ValueError('Unbalanced Python delimiters')
            frames.pop()
        elif value == ',' and kind == 'punct' and frames:
            frames[-1]['commas'] += 1
            frames[-1]['has_argument'] = False
        elif frames:
            frames[-1]['has_argument'] = True
        before_previous = previous
        previous = token
    return frames


def _python(feature, text):
    tokens, state, closed_strings = _python_lex(text)
    if feature == 'python_comment':
        if state == 'string':
            raise ValueError('The read token is in an unclosed string')
        return _answer('comment' if state == 'comment' else 'code', lexical_state=state)
    if feature == 'python_string':
        if state == 'comment':
            raise ValueError('The read token is in a comment')
        if state == 'string':
            return _answer('inside', open_string=True, closed_strings=closed_strings)
        if closed_strings and tokens and tokens[-1][0] != 'string':
            return _answer('outside', open_string=False, closed_strings=closed_strings)
        raise ValueError('No earlier closed string and later code token')
    if state != 'code':
        raise ValueError('The read token is not executable syntax')
    if feature == 'python_indent':
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            raise ValueError('Indentation source must form a Python statement') from exc
        final_line = len(text.splitlines())
        found = []
        def walk_suite(statements, depth):
            for statement in statements:
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if statement.lineno == final_line:
                    found.append((depth, statement.col_offset))
                for field, value in ast.iter_fields(statement):
                    if field in ('body', 'orelse', 'finalbody') and isinstance(value, list):
                        walk_suite(value, depth + 1)
                    elif field == 'handlers':
                        for handler in value:
                            walk_suite(handler.body, depth + 1)
                    elif field == 'cases':
                        for case in value:
                            walk_suite(case.body, depth + 1)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk_suite(node.body, 1)
        if len(found) != 1 or found[0][0] not in (1, 3):
            raise ValueError('Final statement is not at supported function-body depth')
        depth, column = found[0]
        return _answer('shallow' if depth == 1 else 'deep', suite_depth=depth, indentation_columns=column)
    frames = _python_frames(tokens)
    if feature == 'python_depth':
        depth = len(frames)
        if depth not in (1, 3):
            raise ValueError('Bracket depth is outside the two defined values')
        return _answer('shallow' if depth == 1 else 'deep', bracket_depth=depth)
    if feature == 'python_argument':
        calls = [frame for frame in frames if frame['call']]
        if not calls or not tokens or tokens[-1][1] == ',':
            raise ValueError('No current argument in an open call')
        current = calls[-1]
        argument_tokens = [token for token in tokens if token[2] > current['offset']]
        if not any(token[0] in ('name', 'number', 'string') for token in argument_tokens):
            raise ValueError('The open call has no argument content yet')
        if any(token[0] == 'name' and token[1] == 'lambda' for token in argument_tokens):
            raise ValueError('Lambda parameter commas require a separate expression parser')
        index = current['commas'] + 1
        if index not in (1, 5):
            raise ValueError('Current call argument is neither first nor fifth')
        return _answer('first' if index == 1 else 'later', argument_index=index, call_open_offset=current['offset'])
    raise ValueError('Unknown Python feature')


def _prose(feature, text):
    if '\n\n' in text:
        raise ValueError('Multiple paragraphs are ambiguous')
    if feature == 'prose_sentence':
        if text[-1] in '.!?':
            raise ValueError('Read token must be inside the current sentence')
        if re.search(r'\.\.|\d\.\d|\b[A-Za-z]\.|\b(?:Mr|Mrs|Ms|Dr|Prof|St|etc)\.', text):
            raise ValueError('Abbreviation or decimal needs disambiguation')
        boundaries = list(re.finditer(r'[.!?]+(?=\s)', text))
        index = 1 + len(boundaries)
        tail = text[boundaries[-1].end():] if boundaries else text
        if len(re.findall(r'\b[\w]+\b', tail)) < 2:
            raise ValueError('Read token is not a few words into the sentence')
        if index not in (1, 2, 6, 7, 8):
            raise ValueError('Sentence index is outside the defined bands')
        return _answer('early' if index <= 2 else 'late', sentence_index=index)
    # Retain only the actual current sentence; generated prefixes avoid
    # abbreviations and terminal punctuation inside their parenthetical text.
    sentence = re.split(r'[.!?]+\s+', text)[-1]
    if feature == 'prose_paren':
        if sentence.endswith(')'):
            raise ValueError('The closing parenthesis is at the read endpoint, not earlier')
        depth = 0
        closed = 0
        for char in sentence:
            if char == '(':
                depth += 1
            elif char == ')':
                if not depth:
                    raise ValueError('Unmatched closing parenthesis')
                depth -= 1
                closed += 1
        if depth:
            return _answer('inside', parenthesis_depth=depth, closed_parentheses=closed)
        if closed:
            return _answer('outside', parenthesis_depth=0, closed_parentheses=closed)
        raise ValueError('No parenthesis in the current sentence')
    if feature == 'prose_quote':
        if sentence.endswith(('"', '”')):
            raise ValueError('The quotation delimiter is at the read endpoint, not earlier')
        delimiter = None
        closed = 0
        for i, char in enumerate(sentence):
            if char == '\\':
                raise ValueError('Escaped quotation is unsupported')
            if char == '“':
                if delimiter:
                    raise ValueError('Nested mixed quotations are ambiguous')
                delimiter = '”'
            elif char == '”':
                if delimiter != '”':
                    raise ValueError('Unmatched typographic quotation')
                delimiter = None
                closed += 1
            elif char == '"':
                if delimiter is None:
                    delimiter = '"'
                elif delimiter == '"':
                    delimiter = None
                    closed += 1
                else:
                    raise ValueError('Nested mixed quotations are ambiguous')
        if delimiter:
            return _answer('inside', open_quotation=True, closed_quotations=closed)
        if closed:
            return _answer('outside', open_quotation=False, closed_quotations=closed)
        raise ValueError('No unambiguous quotation in the current sentence')
    raise ValueError('Unknown prose feature')


def _strip_latex_comments(text):
    output = []
    for line_number, line in enumerate(text.splitlines(keepends=True)):
        for position, char in enumerate(line):
            if char != '%':
                continue
            backslashes = 0
            earlier = position - 1
            while earlier >= 0 and line[earlier] == '\\':
                backslashes += 1
                earlier -= 1
            if backslashes % 2 == 0:
                if not line.endswith(('\n', '\r')):
                    raise ValueError('The final read token is inside a LaTeX comment')
                line = line[:position] + '\n'
                break
        output.append(line)
    return ''.join(output)


def _latex(feature, text):
    source = _strip_latex_comments(text)
    if re.search(r'\\(?:verb\b|begin\s*\{(?:verbatim|lstlisting|minted)\})', source):
        raise ValueError('Verbatim material requires a separate LaTeX parser')
    if feature == 'latex_environment':
        stack = []
        for match in re.finditer(r'(?<!\\)\\(begin|end)\s*\{\s*([A-Za-z*]+)\s*\}', source):
            action, environment = match.groups()
            if action == 'begin':
                stack.append((environment, match.end()))
            elif not stack or stack.pop()[0] != environment:
                raise ValueError('Unbalanced LaTeX environments')
        if not stack or stack[-1][0] not in ('equation', 'quote'):
            raise ValueError('Current environment is outside the defined pair')
        if not source[stack[-1][1]:].strip():
            raise ValueError('Read token is not in environment body text')
        return _answer(stack[-1][0], open_environment_depth=len(stack), body_started=True)
    headings = []
    for match in re.finditer(r'(?<!\\)\\section\b', source):
        rest = source[match.end():]
        if rest.lstrip().startswith('*'):
            raise ValueError('Unnumbered section makes ordinal ambiguous')
        opening = re.match(r'\s*(?:\[[^\]]*\]\s*)?\{', rest)
        if not opening:
            raise ValueError('Malformed section heading')
        pos = match.end() + opening.end()
        depth = 1
        while pos < len(source) and depth:
            if source[pos] == '{' and (pos == 0 or source[pos-1] != '\\'):
                depth += 1
            elif source[pos] == '}' and (pos == 0 or source[pos-1] != '\\'):
                depth -= 1
            pos += 1
        if depth:
            raise ValueError('Read token is still inside a section heading')
        headings.append(pos)
    count = len(headings)
    if count not in (1, 2, 6, 7, 8) or not source[headings[-1]:].strip():
        raise ValueError('Section count or body position is outside definition')
    return _answer('early' if count <= 2 else 'late', section_count=count)


def _bullet_rows(text):
    lines = text.splitlines()
    rows = []
    for line in reversed(lines):
        match = re.match(r'^( *)([-+*]) +(.+)$', line)
        if not match:
            break
        rows.append((len(match[1]), match[2]))
    rows.reverse()
    if not rows:
        raise ValueError('Read token is not in a Markdown bullet item')
    return rows


def _list(feature, text):
    rows = _bullet_rows(text)
    if feature == 'list_index':
        preceding = text.splitlines()[:-len(rows)]
        if preceding and not preceding[-1].strip():
            previous_nonblank = next((line for line in reversed(preceding) if line.strip()), '')
            if re.match(r'^ *[-+*] +', previous_nonblank) or previous_nonblank.startswith(('  ', '\t')):
                raise ValueError('A blank-separated bullet may continue a loose Markdown list')
    levels = []
    for indent, marker in rows:
        if not levels:
            if indent:
                raise ValueError('No enclosing top-level item establishes nesting')
            levels.append(indent)
        elif indent > levels[-1]:
            if indent - levels[-1] < 2:
                raise ValueError('Insufficient bullet nesting indentation')
            levels.append(indent)
        else:
            while levels and levels[-1] > indent:
                levels.pop()
            if not levels or levels[-1] != indent:
                raise ValueError('Inconsistent Markdown nesting')
    if feature == 'list_depth':
        depth = len(levels)
        if depth not in (1, 3):
            raise ValueError('List nesting is outside the defined pair')
        return _answer('shallow' if depth == 1 else 'deep', nesting_level=depth)
    indent, marker = rows[-1]
    index = 0
    for earlier_indent, earlier_marker in reversed(rows):
        if earlier_indent < indent:
            break
        if earlier_indent == indent:
            if earlier_marker != marker:
                raise ValueError('Changed marker can start a separate Markdown list')
            index += 1
    if index not in (1, 6, 7, 8):
        raise ValueError('List item index is outside the defined pair')
    return _answer('first' if index == 1 else 'later', item_index=index)


def _table_cells(line, reject_terminal=False):
    cells = []
    start = 0
    code_delimiter = None
    terminal_separator = False
    i = 0
    while i < len(line):
        char = line[i]
        if char == '\\':
            i += 2
            continue
        if char == '`':
            end = i + 1
            while end < len(line) and line[end] == '`':
                end += 1
            delimiter = line[i:end]
            if code_delimiter is None:
                code_delimiter = delimiter
            elif code_delimiter == delimiter:
                code_delimiter = None
            i = end
            continue
        if char == '|' and code_delimiter is None:
            terminal_separator = i == len(line.rstrip()) - 1
            if terminal_separator and reject_terminal:
                raise ValueError('The final read token is a table cell delimiter')
            cells.append(line[start:i].strip())
            start = i + 1
        i += 1
    cells.append(line[start:].strip())
    if line.lstrip().startswith('|'):
        cells = cells[1:]
    if terminal_separator:
        cells = cells[:-1]
    return cells


def _table(feature, text):
    lines = text.splitlines()
    block = []
    for offset, line in enumerate(reversed(lines)):
        if not line.strip():
            break
        if offset and '|' not in line:
            break
        block.append(line)
    block.reverse()
    if not block or ('|' not in block[0] and len(block) == 1):
        raise ValueError('No Markdown table structure establishes the current row')
    rows = [_table_cells(line, reject_terminal=i == len(block)-1) for i, line in enumerate(block)]
    separator_indices = [i for i, row in enumerate(rows) if row and all(re.fullmatch(r':?-{3,}:?', cell) for cell in row)]
    if not separator_indices:
        if feature == 'table_role' and len(rows) == 1 and rows[-1] and rows[-1][-1]:
            return _answer('header', prior_separator=False, current_column=len(rows[-1]))
        raise ValueError('No table delimiter row establishes a data region')
    if separator_indices != [1] or len(rows) < 3 or len(rows[0]) != len(rows[1]):
        raise ValueError('Malformed or ambiguous table delimiter structure')
    width = len(rows[1])
    if any(len(row) != width for row in rows[2:-1]):
        raise ValueError('Completed data rows disagree with the table width')
    if not rows[-1] or not rows[-1][-1] or len(rows[-1]) > width:
        raise ValueError('The read token is not inside a current cell')
    if feature == 'table_role':
        return _answer('data', prior_separator=True, data_row_index=len(rows)-2)
    if feature == 'table_column':
        column = len(rows[-1])
        if column not in (1, 5):
            raise ValueError('Current column is neither first nor fifth')
        return _answer('first' if column == 1 else 'later', column_index=column)
    row_index = len(rows) - 2
    if row_index not in (1, 2, 6, 7, 8):
        raise ValueError('Data-row index is outside the defined bands')
    return _answer('early' if row_index <= 2 else 'late', data_row_index=row_index)


def _json_tokens(text):
    tokens = []
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif c in '{}[]:,':
            tokens.append((c, c))
            i += 1
        elif c == '"':
            i += 1
            while i < len(text):
                if text[i] == '\\':
                    if i + 1 >= len(text):
                        raise ValueError('Incomplete JSON escape')
                    escape = text[i + 1]
                    if escape in '"\\/bfnrt':
                        i += 2
                    elif escape == 'u' and re.fullmatch(r'[0-9A-Fa-f]{4}', text[i+2:i+6]):
                        i += 6
                    else:
                        raise ValueError('Invalid JSON string escape')
                elif text[i] == '"':
                    i += 1
                    tokens.append(('string', ''))
                    break
                elif ord(text[i]) < 32:
                    raise ValueError('Invalid JSON string control character')
                else:
                    i += 1
            else:
                tokens.append(('open_string', ''))
        else:
            match = re.match(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|true\b|false\b|null\b', text[i:])
            if not match:
                raise ValueError('Invalid JSON token')
            value = match.group()
            kind = 'number' if value[0] in '-0123456789' else 'literal'
            tokens.append((kind, value))
            i += len(value)
    return tokens


def _json_type(text):
    tokens = _json_tokens(text)
    if not tokens or tokens[-1][0] not in ('open_string', 'number'):
        raise ValueError('Read token is not inside a string or numeric value')
    frames = []
    root_consumed = False
    def consume_value():
        nonlocal root_consumed
        if not frames:
            if root_consumed:
                raise ValueError('Multiple JSON roots')
            root_consumed = True
        else:
            frame = frames[-1]
            if frame['state'] not in ('value', 'value_or_end'):
                raise ValueError('JSON value is not expected')
            frame['state'] = 'comma_or_end'
    for kind, value in tokens[:-1]:
        if kind in ('{', '['):
            consume_value()
            frames.append({'kind': kind, 'state': 'key_or_end' if kind == '{' else 'value_or_end'})
        elif kind in ('}', ']'):
            expected = '{' if kind == '}' else '['
            if not frames or frames[-1]['kind'] != expected or frames[-1]['state'] not in ('key_or_end', 'value_or_end', 'comma_or_end'):
                raise ValueError('Unbalanced or incomplete JSON container')
            frames.pop()
        elif kind == 'string' and frames and frames[-1]['kind'] == '{' and frames[-1]['state'] in ('key_or_end', 'key'):
            frames[-1]['state'] = 'colon'
        elif kind == ':':
            if not frames or frames[-1]['state'] != 'colon':
                raise ValueError('Unexpected JSON colon')
            frames[-1]['state'] = 'value'
        elif kind == ',':
            if not frames or frames[-1]['state'] != 'comma_or_end':
                raise ValueError('Unexpected JSON comma')
            frames[-1]['state'] = 'key' if frames[-1]['kind'] == '{' else 'value'
        elif kind in ('string', 'number', 'literal'):
            consume_value()
        else:
            raise ValueError('Unexpected incomplete JSON token')
    if not frames or frames[-1]['kind'] != '{' or frames[-1]['state'] != 'value':
        raise ValueError('Read token is not a current object field value')
    string = tokens[-1][0] == 'open_string'
    return _answer('string' if string else 'number', value_type='string' if string else 'number', container_depth=len(frames))


def infer_label(feature, text):
    """Infer the packet's literal value from raw prefix structure only."""
    _validate_text(text)
    if feature in ('python_string', 'python_comment', 'python_depth', 'python_argument', 'python_indent'):
        return _python(feature, text)
    if feature in ('prose_paren', 'prose_quote', 'prose_sentence'):
        return _prose(feature, text)
    if feature in ('latex_environment', 'latex_section'):
        return _latex(feature, text)
    if feature in ('list_depth', 'list_index'):
        return _list(feature, text)
    if feature in ('table_role', 'table_column', 'table_row'):
        return _table(feature, text)
    if feature == 'json_type':
        return _json_type(text)
    raise ValueError('Unknown structure feature')
