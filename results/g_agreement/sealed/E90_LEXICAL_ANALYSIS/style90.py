"""Frozen, outcome-blind E90 lexical rule. No learned judge or classifier."""
import re
# Explicit metatext predicates, or noun phrases that describe the passage's form.
DESCRIPTIVE = re.compile(
 r'\b(?:this|the)\s+(?:text|passage|sentence|paragraph|excerpt|code|prompt|story|narrative|document|instruction|question)\b'
 r'|\b(?:describes?|depicts?|discuss(?:es)?|mentions?|narrates?|portrays?|explains?|illustrates?|summariz(?:es?|ing)|focus(?:es)? on|cent(?:ers?|res?) on|refers? to|is about|are about)\b'
 r'|\b(?:a|an)\s+(?:description|discussion|narrative|story|account|explanation|instruction|question|dialogue|conversation|list|table|function|loop|conditional|code snippet)\b'
 r'|\b(?:past|present|future) tense\b|\b(?:first|second|third)[ -]person\b'
 r'|\b(?:declarative|interrogative|imperative|conditional) (?:sentence|statement|clause)\b'
 r'|\b(?:positive|negative|neutral) (?:tone|sentiment)\b', re.I)
BULLET = re.compile(r'^\s*(?:[-*•]|\d+[.)])\s+(.+)$')
STOPWORDS=frozenset('a an the and or but if then than as at by for from in into of on onto to up with without is am are was were be been being do does did have has had it its this that these those he she they them his her their we us our you your i me my not no so very can could may might will would shall should'.split())
def classify(text):
    bullets=[]
    for line in text.splitlines():
        m=BULLET.match(line)
        if m:bullets.append(m.group(1))
        elif line.strip() and bullets:bullets[-1]+=' '+line.strip()
    if not bullets:return {'evaluable':False,'reason':'no bullet entries','bullets':0,'fragments':0,'continuation_style':None}
    fragment=sum(not DESCRIPTIVE.search(b) for b in bullets)
    return {'evaluable':True,'bullets':len(bullets),'fragments':fragment,'continuation_style':2*fragment>=len(bullets)}
def words(text):return {w for w in re.findall(r"[^\W_]+(?:'[^\W_]+)?",text.casefold()) if w not in STOPWORDS}
def jaccard(a,b):
    x,y=words(a),words(b)
    return len(x&y)/len(x|y) if x|y else 0.0
