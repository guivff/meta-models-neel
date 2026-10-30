"""E36 v2 definition-only structure bank. No W1 inputs or generated labels.

Public API: render(feature, template_index, filler_index, value_index).
Templates 0..5 are dev; templates 6..11 are test. Final whitespace is absent.
"""

FEATURES = (
    'prose_paren', 'python_string', 'table_role', 'python_indent',
    'table_column', 'list_index', 'json_type', 'latex_environment',
    'latex_section', 'list_depth', 'prose_quote', 'prose_sentence',
    'python_argument', 'python_comment', 'python_depth', 'table_row',
)

FILLERS = (
    ('copper marker', 'copper_marker', '164803'),
    ('linen sample', 'linen_sample', '275914'),
    ('cedar panel', 'cedar_panel', '386025'),
    ('silver ribbon', 'silver_ribbon', '497136'),
    ('marble token', 'marble_token', '508247'),
    ('velvet cover', 'velvet_cover', '619358'),
    ('amber seal', 'amber_seal', '720469'),
)


def _paren(t, f, v):
    name, ident, digits = f
    layouts = (
        ('The curator ', 'after inspecting the ' + name, 'carefully checked the nearby display'),
        ('Before the doors opened ', 'while the ' + name + ' was still on the desk', 'the assistant reviewed the written record'),
        ('A note beside the ' + name + ' ', 'which the clerk had copied by hand', 'remained clearly visible beside the ledger'),
        ('The inspector requested a second reading ', 'especially of the ' + name, 'before the morning review began'),
        ('The revised inventory includes a description ', 'with particular attention to the ' + name, 'for the team responsible for storage'),
        ('Our guide paused at the display ', 'near the recently catalogued ' + name, 'to explain the sequence of repairs'),
        ('The ' + name + ' appeared undamaged ', 'at least according to the initial inspection', 'when the technician returned with the checklist'),
        ('One detail mattered during the review ', 'the position of the ' + name, 'above the narrow shelf by the window'),
        ('The apprentice made a sketch ', 'using the ' + name + ' as a reference', 'with the measurements written along the margin'),
        ('Every visitor received a short explanation ', 'including a description of the ' + name, 'during the afternoon tour of the collection'),
        ('The delivery record ', 'a copy of the original note (about the ' + name + ')', 'was waiting beside the unopened package'),
        ('For the final check ', 'after comparing the ' + name + ' with its earlier photograph', 'the supervisor opened the matching entry'),
    )
    pre, inner, tail = layouts[t]
    return pre + '(' + inner + (') ' if v else ' ') + tail


def _quote(t, f, v):
    name = f[0]
    layouts = (
        ('The guide described ', 'the ' + name + ' near the doorway', 'for the visitors arriving that morning', '"', '"'),
        ('The clerk copied ', 'a description of the ' + name, 'into the notebook kept beside the register', '“', '”'),
        ('We discussed the phrase ', 'inspection of the ' + name, 'during the meeting about the collection', '"', '"'),
        ('The caption mentions ', 'the ' + name + ' on the upper shelf', 'in the account of the restored display', '“', '”'),
        ('In the report, Mira underlined ', 'a small mark beside the ' + name, 'with a pencil borrowed from the desk', '"', '"'),
        ('The notice refers to ', 'a photograph of the ' + name, 'for anyone checking the storage records', '“', '”'),
        ('An editor suggested ', 'a closer view of the ' + name, 'as part of the illustrated catalogue', '"', '"'),
        ('The archivist translated ', 'the note about the ' + name, 'for readers consulting the original ledger', '“', '”'),
        ('We retained the wording ', 'a comparison with the ' + name, 'in the revised description of the exhibit', '"', '"'),
        ('The instructor wrote ', 'measurements taken beside the ' + name, 'on the board facing the workbench', '“', '”'),
        ('A visitor asked about ', 'the label attached to the ' + name, 'after the tour reached the final cabinet', '"', '"'),
        ('The narrator repeated ', 'the story behind the ' + name, 'throughout the recording made for the gallery', '“', '”'),
    )
    pre, inner, tail, opening, closing = layouts[t]
    return pre + opening + inner + (closing + ' ' if v else ' ') + tail


def _python_string(t, f, v):
    name, ident, digits = f
    name = 'inspection record for the ' + name
    ident = 'inspection_record_for_' + ident
    # Exactly one closing delimiter distinguishes each pair.
    layouts = (
        ('caption = "', name, '"', ' + caption_tail'),
        ("save_record('", name, "'", ', current_record'),
        ('record = {"caption": "', name, '"', ', count_key: total_count'),
        ("labels = ['", name, "'", ', pending_label'),
        ('entry = ("""', name, '"""', ', current_position'),
        ('register(label=r"', name, '"', ', count=current_count'),
        ('assert caption == "', name, '"', ' and record_is_ready'),
        ("description += '", name, "'", ' + descriptive_suffix'),
        ("selected = captions['", name, "'", '] if has_caption else fallback_caption'),
        ('message = """Inspection notes\nItem: ', name, '"""', ' + detail_suffix'),
        ("def encode_label():\n    return b'", ident, "'", ' + encoded_suffix'),
        ('with open("', ident + '.txt', '"', ', mode=current_mode'),
    )
    pre, content, closing, tail = layouts[t]
    return pre + content + (closing if v else '') + tail


def _python_indent(t, f, v):
    name, ident, digits = f
    layouts = (
        ('if record_is_ready:', 'if entry_is_visible:', 'selected_count = current_count + reserved_count'),
        ('for entry in record_entries:', 'if entry_is_visible:', 'selected_record = entry'),
        ('if record_is_ready:', 'for entry in record_entries:', 'selected_record = entry'),
        ('while work_remains:', 'if record_is_ready:', 'remaining_count = current_count - completed_count'),
        ('for entry in record_entries:', 'for label in entry_labels:', 'selected_label = label'),
        ('with open_record() as record:', 'if record_is_ready:', 'selected_record = record'),
        ('if record_is_ready:', 'with open_record() as record:', 'selected_record = record'),
        ('while work_remains:', 'for entry in record_entries:', 'selected_record = entry'),
        ('with open_record() as record:', 'for entry in record_entries:', 'selected_record = entry'),
        ('for entry in record_entries:', 'while work_remains:', 'remaining_count = current_count - completed_count'),
        ('if record_is_ready:', 'while work_remains:', 'remaining_count = current_count - completed_count'),
        ('with open_record() as record:', 'with open_labels() as labels:', 'selected_labels = labels'),
    )
    outer, inner, statement = layouts[t]
    return (f'def inspect_{ident}():\n    current_label = "{name}"\n'
            f'    {outer}\n        {inner}\n            inspected_count = current_count\n'
            + ('            ' if v else '    ') + statement)


def _python_comment(t, f, v):
    name, ident, digits = f
    layouts = (
        ('current_count = base_count ', '+ reserved_count'),
        ('', 'selected_record = current_record'),
        ('def inspect_record():\n    ', 'return selected_record'),
        ('if record_is_ready:\n    ', 'selected_record = current_record'),
        ('record_label = "mark # retained"\n', 'save_record(record_label, current_record)'),
        ('assert record_is_ready ', 'and label_is_visible'),
        ('labels = [first_label, second_label]\n', 'labels.append(current_label)'),
        ('current_count += base_count ', '+ reserved_count'),
        ('for entry in record_entries:\n    ', 'inspect_record(entry)'),
        ('selected_label = current_label ', 'if record_is_ready else fallback_label'),
        ('record_data = {"label": current_label}\n', 'del record_data["label"]'),
        ('def inspect_record():\n    selected_record = current_record\n    ', 'yield selected_record'),
    )
    pre, tail = layouts[t]
    # A source comment can begin at the start or middle of a statement prefix.
    return f'record_description = "Inspection of the {name} in the current collection"\n' + pre + ('' if v else '# ') + tail


def _python_argument(t, f, v):
    name, ident, digits = f
    expressions = ('initial_count', 'reserved_count', 'measured_count', 'verified_count', ident + '_count')
    layouts = (
        ('combine_counts(', '', '', ' + '),
        ('record.combine_counts(', '', '', ' + '),
        ('counts = combine_counts(', '(', '', ', '),
        ('counts = record.combine_counts(\n    ', '[', '', ',\n    '),
        ('counts: int = combine_counts(', '(', '', ' + '),
        ('register_counts(total=', '(', '', ' + '),
        ('record.handlers[index](', '', '', ' | '),
        ('return_value = combine_counts(\n    ', '', '', '\n    + '),
        ('assert combine_counts(', '[', '', ', '),
        ('result = factory().combine_counts(', '', '', ' + '),
        ('count_sink.accept(*', '(', '', ', '),
        ('if combine_counts(', '(', '', ', '),
    )
    pre, opening, unused, sep = layouts[t]
    if t == 5:
        # The aggregate is a first keyword argument; the split version is fifth.
        pre = 'register_counts(' if v else pre
        values = list(expressions)
        if v:
            values[-1] = 'total=' + values[-1]
        body = ', '.join(values) if v else ' + '.join(values)
    elif t == 10:
        pre = 'count_sink.accept(' if v else pre
        body = ', '.join(expressions) if v else ', '.join(expressions)
    else:
        body = (',\n    ' if '\n' in sep else ', ').join(expressions) if v else sep.join(expressions)
    return f'current_label = "Detailed count record for the {name}"\n' + pre + (opening if not v else '') + body


def _python_depth(t, f, v):
    name, ident, digits = f
    layouts = (
        ('adjusted_count = ', '(', '(((', 'measured_count + reserved_count + ' + ident + '_count'),
        ('record_counts = ', '[', '[[[', 'measured_count, reserved_count, ' + ident + '_count'),
        ('record_data = ', '{', '([{', '"measured": measured_count, "reserved": ' + ident + '_count'),
        ('distinct_counts = ', '{', '([{', 'measured_count, reserved_count, ' + ident + '_count'),
        ('selected_counts = all_counts', '[', '[((', 'base_index + offset_index + current_step'),
        ('record_counts = ', '[', '([[', 'count for count in available_counts if count > ' + ident + '_count'),
        ('count_stream = ', '(', '([(', 'count for count in available_counts if count > ' + ident + '_count'),
        ('record_counts: list = ', '[', '([[', 'measured_count, reserved_count, ' + ident + '_count'),
        ('if ', '(', '(((', 'measured_count > reserved_count and current_count > ' + ident + '_count'),
        ('def current_counts():\n    return ', '[', '([[', 'measured_count, reserved_count, ' + ident + '_count'),
        ('scaled_count = scale_factor * ', '(', '(((', 'measured_count + reserved_count + ' + ident + '_count'),
        ('record_data = ', '{', '([{', '"label": current_label, "count": ' + ident + '_count'),
    )
    pre, shallow, deep, body = layouts[t]
    return f'current_label = "Detailed inspection record for the {name}"\n' + pre + (deep if v else shallow) + body


def _json_type(t, f, v):
    name, ident, digits = f
    prefixes = (
        '{"record": "' + name + '", "measurements": {"reading": ',
        '{"records": [{"caption": "' + name + '", "reading": ',
        '{"caption": "' + name + '", "accepted": true, "reading": ',
        '{"caption": "' + name + '", "previous": null, "reading": ',
        '{"caption": "' + name + '", "range": [10, 20, 30], "reading": ',
        '{\n  "caption": "' + name + '",\n  "reading": ',
        '{"summary": {"caption": "' + name + '"}, "reading": ',
        '[{"caption": "' + name + '", "reading": ',
        '{"caption": "' + name + '", "history": [{"reading": 12}], "reading": ',
        '{"caption": "' + name + '", "flags": [true, false], "reading": ',
        '{"caption": "' + name + '", "metadata": {}, "values": {"reading": ',
        '{"caption": "' + name + '", "series": [[], {"reading": ',
    )
    numeric_forms = (digits, '-' + digits, digits + '.25', digits + 'e2', digits + 'E+3', digits + '.125',
                     '-' + digits + '.5', digits + 'e-2', digits + '.75e2', '0.' + digits, digits + 'E4', '-' + digits + 'e3')
    return prefixes[t] + ('' if v else '"') + numeric_forms[t]


def _latex_environment(t, f, v):
    name = f[0]
    env = 'quote' if v else 'equation'
    frames = (
        ('', '\\begin{' + env + '}\n', '\\mbox{The recorded item is the '),
        ('\\documentclass{article}\n\\begin{document}\n', '\\begin{' + env + '}\n', '\\mbox{The selected reference is the '),
        ('\\begin{center}\n', '\\begin{' + env + '}\n', '\\mbox{The displayed specimen is the '),
        ('\\begin{itemize}\n\\item Inspection record\n', '\\begin{' + env + '}\n', '\\mbox{The item under review is the '),
        ('\\begin{enumerate}\n\\item Collection detail\n', '\\begin{' + env + '}\n', '\\mbox{The comparison concerns the '),
        ('\\begin{minipage}{0.8\\textwidth}\n', '\\begin{' + env + '}\n', '\\mbox{The illustrated reference is the '),
        ('\\begin{quote}Earlier inspection notes\\end{quote}\n', '\\begin {' + env + '}\n', '\\mbox{The next inspection concerns the '),
        ('\\begin{equation}x = y\\end{equation}\n', '\\begin\n{' + env + '}\n', '\\mbox{The physical reference is the '),
        ('{\\small\n', '\\begin{' + env + '}\n', '\\mbox{The described object is the '),
        ('', '\\begin{' + env + '}\\label{current-record}\n', '\\mbox{The labelled item is the '),
        ('\\begin{flushleft}\n', '\\begin{' + env + '} % current inspection\n', '\\mbox{The item shown in the record is the '),
        ('\\subsection{Inspection notes}\n', '\\begin% environment follows\n{' + env + '}\n', '\\mbox{The reference used for comparison is the '),
    )
    before, opening, body = frames[t]
    return before + opening + body + name + ' beside the storage ledger'


def _section_heading(command, title, t, i):
    styles = (
        '\\{c}{{{title}}}', '\\{c}[Record {i}]{{{title}}}', '\\{c} {{ {title} }}',
        '\\{c}\n{{{title}}}', '\\{c}{{\\textbf{{{title}}}}}', '\\{c}{{{title}: observations}}',
        '\\{c}[Inspection]{{{title}}}', '\\{c}{{{title}\ncontinued}}',
        '\\{c}{{{title} and \\emph{{comparison}}}}', '\\{c}% heading follows\n{{{title}}}',
        '\\{c}[Part {i}]\n{{{title}}}', '\\{c}{{{title} -- collection notes}}',
    )
    return styles[t].format(c=command, title=title, i=i)


def _latex_section(t, f, v):
    name = f[0]
    count = 6 + t % 3
    early = 1 + t % 2
    titles = ('Arrival', 'Inspection', 'Measurements', 'Comparison', 'Documentation', 'Storage', 'Review', 'Summary')
    parts = ['\\documentclass{article}\n\\begin{document}'] if t % 2 else []
    for i in range(count):
        command = 'section' if v or i < early else 'subsection'
        parts.append(_section_heading(command, titles[i], t, i + 1))
        if i != count - 1:
            parts.append('The ' + name + ' is described in the corresponding collection record.')
    parts.append('The current account describes the ' + name + ' beside the storage ledger')
    return '\n'.join(parts)


# Each list family changes item syntax (task boxes, emphasis, code, links,
# block-spanning content, and labelled subclauses), not just the heading.
def _list_item(t, text, ident, final=False):
    if t == 0: return text
    if t == 1: return '**Record:** ' + text
    if t == 2: return '*Observation* — ' + text
    if t == 3: return '[ ] ' + text
    if t == 4: return '[x] **Checked:** ' + text
    if t == 5: return '`' + ident + '` — ' + text
    if t == 6: return '[Reference](records/' + ident + ') — ' + text
    if t == 7: return 'Purpose: ' + text + '; responsible team: collection staff'
    if t == 8: return 'Inspection — **' + text + (' details' if final else ' complete') + '**'
    if t == 9: return 'Record (' + ident + '): ' + text
    if t == 10: return text + ' — _reviewed against the written inventory_'
    return '**Reference** `' + ident + '`; details: ' + text


def _list_depth(t, f, v):
    name, ident, digits = f
    marker = ('-', '+', '*')[t % 3]
    parent = _list_item(t, 'Review the collection record and its linked inspection notes', ident)
    child = _list_item(t, 'Check the recorded location and the measurements beside the photograph', ident)
    target = _list_item(t, 'Inspect the ' + name + ' beside the storage ledger', ident, True)
    return marker + ' ' + parent + '\n  ' + marker + ' ' + child + '\n' + ('    ' if v else '') + marker + ' ' + target


def _list_index(t, f, v):
    name, ident, digits = f
    marker = ('-', '+', '*')[t % 3]
    previous = (
        'Consult the original collection register and confirm the recorded name of the item before beginning the inspection',
        'Compare the dated arrival note with the storage record and retain the matching reference for the written account',
        'Inspect the photograph under ordinary light and describe any marks that can be seen beside the identifying label',
        'Check the measurement sheet against the accompanying drawing and record the units used for each dimension of the object',
        'Review the earlier handling instructions with the collection staff and confirm which support should be used during the inspection',
        'Read the latest condition report and identify the parts of the object that require a closer visual comparison',
        'Locate the packaging note in the archive and copy the relevant storage instructions into the working inspection record',
    )[:5 + t % 3]
    if v:
        pre = '\n'.join(marker + ' ' + _list_item(t, s, ident) for s in previous) + '\n'
    else:
        pre = '\n\n'.join(_list_item(t, s, ident) for s in previous) + '\n\n'
    return pre + marker + ' ' + _list_item(t, 'Inspect the ' + name + ' beside the storage ledger', ident, True)


def _prose_sentence(t, f, v):
    name = f[0]
    clauses = (
        ('The clerk opened the register', 'The guide checked the display', 'The curator read the label', 'The assistant found the photograph', 'The technician compared the measurements', 'The supervisor reviewed the notes', 'The porter prepared the support'),
        ('The register was opened beside the window', 'The display was checked under ordinary light', 'The label was read aloud', 'The photograph was placed on the desk', 'The measurements were compared with the drawing', 'The notes were reviewed in order', 'The support was brought into the room'),
        ('Before the visit, the clerk opened the register', 'After the tour, the guide checked the display', 'During the inspection, the curator read the label', 'Near the doorway, the assistant found the photograph', 'At the workbench, the technician compared the measurements', 'By the cabinet, the supervisor reviewed the notes', 'In the corridor, the porter prepared the support'),
        ('Mira opened the register to find the entry', 'Jon checked the display to locate the object', 'Asha read the label to confirm the name', 'Leon found the photograph to compare the markings', 'Ruth compared the measurements to check the scale', 'Omar reviewed the notes to complete the account', 'Nina prepared the support to protect the base'),
        ('A fresh entry appeared in the register', 'A narrow label remained on the display', 'A clear photograph lay beside the drawer', 'A small ruler rested near the drawing', 'A written note described the earlier repair', 'A signed report recorded the comparison', 'A folded cloth covered the support'),
        ('There was a new entry in the register', 'There was a label beside the display', 'There was a photograph inside the drawer', 'There was a ruler beside the drawing', 'There was a note about the earlier repair', 'There was a report of the comparison', 'There was a cloth covering the support'),
        ('Because the room was quiet, the clerk read the entry', 'Because the light was steady, the guide checked the display', 'Because the label was clear, the curator copied the name', 'Because the drawer was open, the assistant found the photograph', 'Because the scale was marked, the technician checked the measurements', 'Because the notes were dated, the supervisor traced the repairs', 'Because the base was fragile, the porter prepared the support'),
        ('Opening the register, the clerk found the entry', 'Checking the display, the guide noticed the label', 'Reading the label, the curator confirmed the name', 'Searching the drawer, the assistant found the photograph', 'Comparing the drawings, the technician checked the measurements', 'Reviewing the notes, the supervisor traced the repairs', 'Preparing the support, the porter folded the cloth'),
        ('The register contained both the entry and its date', 'The display showed both the object and its label', 'The photograph recorded both the front and the base', 'The drawing marked both the height and the width', 'The note described both the damage and the repair', 'The report included both the account and the comparison', 'The support protected both the edge and the underside'),
        ('Although the register was old, its entry was clear', 'Although the display was narrow, its label was visible', 'Although the photograph was small, its details were sharp', 'Although the drawing was folded, its scale was legible', 'Although the note was brief, its purpose was clear', 'Although the report was lengthy, its order was simple', 'Although the support was light, its base was firm'),
        ('First the clerk found the entry in the register', 'Next the guide located the display in the room', 'Then the curator checked the wording on the label', 'Nearby the assistant retrieved the matching photograph', 'Meanwhile the technician compared the recorded measurements', 'Later the supervisor examined the account of the repairs', 'Finally the porter arranged the support beside the table'),
        ('The clerk asked where the register had been stored', 'The guide explained how the display had been arranged', 'The curator recalled when the label had been copied', 'The assistant described where the photograph had been found', 'The technician noted how the measurements had been taken', 'The supervisor explained why the repairs had been recorded', 'The porter showed how the support had been prepared'),
    )[t]
    previous = clauses[:5 + t % 3]
    target = 'The ' + name + ' remained clearly visible'
    result = previous[0]
    for i, clause in enumerate(previous[1:] + (target,), start=1):
        boundary = v or (t % 2 == 1 and i == 1)
        result += ('. ' if boundary else '; ') + clause
    return result


# Table families use different widths, outer-pipe conventions, alignments and
# inline cell structures. The final line is always a partial, unclosed row.
def _table_spec(t):
    widths = (2, 3, 4, 5, 2, 3, 5, 4, 2, 5, 3, 4)
    width = widths[t]
    outer = t not in (2, 5, 8, 11)
    alignments = ('---', ':---', '---:', ':---:')
    return width, outer, [alignments[(t + j) % 4] for j in range(width)]


def _cell(t, text, ident):
    if t == 1: return '**' + text + '**'
    if t == 2: return '*' + text + '*'
    if t == 3: return '`' + ident + '` ' + text
    if t == 4: return '[reference](records/' + ident + ') ' + text
    if t == 5: return text + ' (checked against the register)'
    if t == 6: return text + ' / inspection detail'
    if t == 7: return '**Record:** ' + text
    if t == 8: return text + ' — condition noted'
    if t == 9: return text + ' <em>reviewed</em>'
    if t == 10: return '`' + ident + '` — **' + text + '**'
    if t == 11: return text + ': collection entry'
    return text


def _table_line(cells, outer=True, complete=True):
    return ('| ' if outer else '') + ' | '.join(cells) + (' |' if outer and complete else '')


def _table_role(t, f, v):
    name, ident, digits = f
    width, outer, separators = _table_spec(t)
    head = ['Record description', 'Inspection note', 'Storage reference', 'Collection detail', 'Review comment'][:width]
    old = [_cell(t, 'Previous record ' + str(j + 1) + ' for the ' + name, ident) for j in range(width)]
    target = [_cell(t, 'Current description of the ' + name, ident)]
    if t % 2 or not outer:
        target = [_cell(t, 'Inspection reference for the ' + name, ident), _cell(t, 'Current review of the recorded measurements', ident)]
    return '\n'.join((_table_line(head, outer), _table_line(separators, outer), _table_line(old, outer))) + ('\n' if v else '\n\n') + _table_line(target, outer, False)


def _table_column(t, f, v):
    name, ident, digits = f
    outer = t not in (2, 5, 8, 11)
    separators = [('---', ':---', '---:', ':---:')[(t+j)%4] for j in range(5)]
    head = ['Record details', 'Handling notes', 'Inspection notes', 'Storage notes', 'Review details']
    chunks = [
        _cell(t, 'Description of the ' + name, ident),
        'handling recorded by the collection staff',
        'inspection compared with the original photograph',
        'storage confirmed beside the labelled cabinet',
        'review based on the current written register',
    ]
    target = _table_line(chunks, outer, False) if v else _table_line(['; '.join(chunks)], outer, False)
    return _table_line(head, outer) + '\n' + _table_line(separators, outer) + '\n' + target


def _table_row(t, f, v):
    name, ident, digits = f
    width, outer, separators = _table_spec(t)
    head = ['Description', 'Inspection record', 'Location record', 'Handling record', 'Review record'][:width]
    descriptions = ('Arrival', 'Condition', 'Measurement', 'Comparison', 'Storage', 'Handling', 'Documentation')[:5+t%3]
    rows = []
    for description in descriptions:
        cells = [_cell(t, description + ' entry for the ' + name + ' with the details copied from the original collection register', ident)]
        cells += [description + ' detail ' + str(j+1) + ' checked against the dated inspection note and retained with the corresponding photograph' for j in range(1, width)]
        rows.append(cells)
    if v:
        prior = [_table_line(row, outer) for row in rows]
    else:
        prior = [_table_line(['<br>'.join(row[j] for row in rows) for j in range(width)], outer)]
    target = _table_line([_cell(t, 'Current review of the ' + name + ' beside the storage ledger', ident)], outer, False)
    return '\n'.join([_table_line(head, outer), _table_line(separators, outer)] + prior + [target])


_RENDERERS = {name[1:]: value for name, value in list(globals().items())
              if name.startswith('_') and name[1:] in FEATURES}
_RENDERERS.update(prose_paren=_paren, prose_quote=_quote)


def render(feature, template_index, filler_index, value_index):
    """Return a raw text prefix, without an expected-label annotation."""
    if feature not in FEATURES:
        raise ValueError('Unknown structure feature')
    if type(template_index) is not int or not 0 <= template_index < 12:
        raise ValueError('Template index must be an integer in 0..11')
    if type(filler_index) is not int or not 0 <= filler_index < 7:
        raise ValueError('Filler index must be an integer in 0..6')
    if type(value_index) is not int or value_index not in (0, 1):
        raise ValueError('Value index must be 0 or 1')
    result = _RENDERERS[feature](template_index, FILLERS[filler_index], value_index)
    if not result or result[-1].isspace():
        raise AssertionError('A prefix must end at a non-whitespace read token')
    return result
