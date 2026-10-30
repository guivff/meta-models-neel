"""Independent lexical checks for the two §157 long syntactic states."""
import re

def fenced(text):
    active=None
    for line in text.splitlines():
        m=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',line)
        if not m:continue
        marker,tail=m.groups()
        if active is None:active=(marker[0],len(marker))
        elif marker[0]==active[0] and len(marker)>=active[1] and not tail.strip():active=None
    return 'inside' if active else 'outside'

def latex_list(text):
    stack=[]
    for action,name in re.findall(r'(?<!\\)\\(begin|end)\{(itemize|enumerate|description)\}',text):
        if action=='begin':stack.append(name)
        elif not stack or stack.pop()!=name:return None
    return 'inside' if stack else 'outside'

def state(row,text):
    return {'fenced_code':fenced,'latex_list':latex_list}[row](text)
