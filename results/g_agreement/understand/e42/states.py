"""§151 clarification 1 lexical state functions; no score or continuation reads.
None means undetermined (carry forward); OTHER is a determined out-of-bin state.
The original excerpt offset is fixed by the frozen item's body, not re-detected.
"""
import importlib.util
import re
from pathlib import Path
OTHER = '__OTHER__'
p = Path(__file__).resolve().parent.parent / 'e36/check_structure.py'
spec = importlib.util.spec_from_file_location('e36_lexical_helpers_e42', p)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def band(n, a, b, labels):
    return labels[0] if n in a else labels[1] if n in b else OTHER


def unit_end(feature, added):
    if feature in ('paragraph_index', 'paragraph_start'):
        return bool(re.search(r'\n[ \t\r]*\n', added))
    if feature in ('sentence_type', 'sentence_position'):
        return bool(re.search(r'[.!?]', added))
    # Require a completed conjunction word, including its right delimiter.
    return bool(re.search(r'[,;:.]|(?<!\w)(?:and|but|or|nor|for|yet|so)(?=\W)', added, re.I))


def python_state(feature, text, values):
    try:
        tokens, mode, closed = C._python_lex(text)
        if feature == 'python_string':
            return values[0] if mode == 'string' else values[1] if mode == 'code' else OTHER
        if feature == 'python_comment':
            return values[0] if mode == 'comment' else values[1] if mode == 'code' else OTHER
        if feature == 'python_indent':
            line = text.split('\n')[-1]
            if not line.strip() or '\t' in line[:len(line)-len(line.lstrip())]:return None
            width = len(line)-len(line.lstrip(' '))
            return band(width, {4}, {12}, values)
        frames = C._python_frames(tokens)
        if feature == 'python_depth':return band(len(frames), {1}, {3}, values)
        calls = [f for f in frames if f['call']]
        return band(calls[-1]['commas']+1, {1}, {5}, values) if calls else OTHER
    except ValueError:
        return None


def prose_state(feature, text, values):
    if feature == 'prose_sentence':
        paragraph = re.split(r'\n\s*\n', text)[-1]
        if not paragraph.strip():return None
        # A terminator closes the sentence; the next starts with nonspace content.
        n = 1 + len(re.findall(r'[.!?]+\s+(?=\S)', paragraph))
        return band(n, {1,2}, {6,7,8}, values)
    depth, quote = 0, None
    for i,c in enumerate(text):
        if i and text[i-1]=='\\':continue
        if feature == 'prose_paren':
            if c=='(':depth+=1
            elif c==')':
                if depth==0:return None
                depth-=1
        elif c in ('"','“','”'):
            if quote is None:
                if c=='”':return None
                quote='”' if c=='“' else '"'
            elif c==quote:quote=None
            else:return None
    return values[0] if (depth>0 if feature=='prose_paren' else quote is not None) else values[1]


def latex_state(feature, text, values):
    text = re.sub(r'(?<!\\)%[^\n]*', '', text)
    if feature == 'latex_math':
        # Ignore escaped dollars, count inline and display delimiters as switches.
        return values[len(re.findall(r'(?<!\\)\$\$?',text))%2 == 0]
    if feature == 'latex_section':
        n=0
        for match in re.finditer(r'(?<!\\)\\section\s*(?:\[[^\]]*\]\s*)?\{',text):
            depth=1
            for token in re.finditer(r'(?<!\\)[{}]',text[match.end():]):
                depth += 1 if token.group()=='{' else -1
                if depth==0:
                    n+=1
                    break
            else:return None  # unfinished heading: carry last determined state
        return band(n,{1,2},{6,7,8},values)
    if feature == 'latex_item':
        parts=re.split(r'\\begin\{enumerate\}',text)
        if len(parts)<2:return None
        if '\\end{enumerate}' in parts[-1]:return OTHER
        return band(len(re.findall(r'\\item\b',parts[-1])),{1},{6,7,8},values)
    if feature == 'latex_environment':
        stack=[]
        for action,name in re.findall(r'(?<!\\)\\(begin|end)\s*\{([^{}]+)\}',text):
            if action=='begin':stack.append(name)
            elif not stack or stack.pop()!=name:return None
        return stack[-1] if stack and stack[-1] in values else OTHER
    # A lexical brace stack identifies the current fraction argument.
    stack=[];pending=None;last_closed=None
    for m in re.finditer(r'\\(?:dfrac|tfrac|frac)\b|(?<!\\)[{}]|[^\s{}\\]+',text):
        token=m.group()
        if token in ('\\frac','\\dfrac','\\tfrac'):pending='numerator'
        elif token=='{':
            role=pending or ('denominator' if last_closed=='numerator' else None)
            stack.append(role);pending=None;last_closed=None
        elif token=='}':
            if not stack:return None
            last_closed=stack.pop()
        elif token.strip():last_closed=None
    for role in reversed(stack):
        if role in ('numerator','denominator'):return role
    return OTHER


def table_state(feature,text,values):
    lines=text.split('\n');block=[]
    for line in reversed(lines):
        if not line.strip():
            if not block:return None
            break
        if '|' not in line:
            if not block:
                if feature in ('table_column','table_row'):
                    block.append(line)  # first cell may precede its first pipe
                    continue
                return OTHER
            break
        block.append(line)
    block.reverse()
    try:rows=[C._table_cells(line, reject_terminal=False) for line in block]
    except ValueError:return None
    if not rows:return None
    separators=[i for i,row in enumerate(rows) if row and all(re.fullmatch(r':?-{3,}:?',cell) for cell in row)]
    if not separators:
        return values[0] if feature=='table_role' and len(rows)==1 else None
    sep=separators[-1]
    if sep==len(rows)-1:return OTHER
    if feature=='table_role':return values[1]
    if feature=='table_row':return band(len(rows)-sep-1,{1,2},{6,7,8},values)
    # A trailing pipe starts the next cell only after content follows it.
    return band(len(rows[-1]),{1},{5},values)


def list_state(feature,text,values):
    markers=[]
    for line in text.split('\n'):
        match=re.match(r'^( *)([-+*])\s+',line)
        if match:markers.append((len(match[1]),match[2]))
        elif line.strip() and markers and not line.startswith(' '):markers=[]
    if not markers:return None
    levels=[]
    for indent,_ in markers:
        while levels and indent<levels[-1]:levels.pop()
        if not levels or indent>levels[-1]:levels.append(indent)
    if feature=='list_depth':return band(len(levels),{1},{3},values)
    index=0;indent,marker=markers[-1]
    for i,m in reversed(markers):
        if i<indent:break
        if i==indent:
            if m!=marker:break
            index+=1
    return band(index,{1},{6,7,8},values)


def state(item,full_text):
    if item['bank']=='W12':
        # Frozen label attaches to original word/unit; state flips at its next end.
        return OTHER if unit_end(item['feature'],full_text[item['prefix_chars']:]) else item['value']
    text=full_text[item['body_offset']:]
    f,v=item['feature'],item['values']
    if f.startswith('python_'):return python_state(f,text,v)
    if f.startswith('prose_'):return prose_state(f,text,v)
    if f.startswith('latex_'):return latex_state(f,text,v)
    if f.startswith('table_'):return table_state(f,text,v)
    if f.startswith('list_'):return list_state(f,text,v)
    if f=='json_type':
        try:return C._json_type(text)['value']
        except ValueError:
            # After a completed field/container, the former value type has ended.
            if re.search(r'[,}\]]\s*$',text):return OTHER
            return None
    raise ValueError('unregistered state function: '+f)
