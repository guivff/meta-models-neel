"""Frozen deterministic §79 prefix features; no suffix, model, API or NLP downloads.

Indicators are operational scripts, not human linguistic annotations. In particular
lexicon features say that a listed word occurred, not that a semantic classifier
found a topic, sentiment, language or tense. Inapplicable measurements are None.
Character positions refer to Unicode codepoints; token positions are supplied only
by the separately frozen corpus builder. Delimiter state is tolerant prefix syntax,
not a complete Python/CommonMark/TeX parser (f-string replacements are not parsed).
"""
from __future__ import annotations
from dataclasses import asdict,dataclass
import math,re

DOMAINS=('prose','python','latex','markdown')
CLASSES=('count-like','state-like','semantic')
ASKED_TEMPLATE='The current text prefix satisfies this statement: {statement}.'

@dataclass(frozen=True)
class Feature:
 id:str
 kind:str
 family:str
 definition:str
 positive:str
 negative:str
 domains:tuple[str,...]=DOMAINS
 threshold:float|None=None
 w1_overlap:tuple[str,...]=()
 @property
 def phrasing_pair(self):return (ASKED_TEMPLATE.format(statement=self.positive),ASKED_TEMPLATE.format(statement=self.negative))
 def record(self):return dict(asdict(self),class_label=self.kind,phrasing_pair=list(self.phrasing_pair))

COUNTERS={
 'paren_depth':(2,3,4),'square_depth':(2,3),'brace_depth':(2,3,4),'bracket_depth':(2,3,4,6),
 'line_index':(2,4,8,16,32),'column_chars':(8,16,32,64,96),'indent_spaces':(2,4,8,12,16),
 'line_words':(3,6,12,24),'sentence_words':(3,6,12,24,40),'paragraph_sentences':(2,3,5,8),
 'table_column':(2,3,4,5),'list_items':(2,3,5,10),'list_depth':(2,3),
 'number_magnitude':(1,10,100,1000,10000),'number_digits':(2,3,4),
 'line_commas':(1,2,3,5),'latex_sections':(1,2,3),'latex_items':(1,2,3),
}
DESCRIPTIONS={
 'paren_depth':'unclosed parenthesis depth outside quoted spans/comments',
 'square_depth':'unclosed square-bracket depth outside quoted spans/comments',
 'brace_depth':'unclosed brace depth outside quoted spans/comments',
 'bracket_depth':'total unclosed bracket depth outside quoted spans/comments',
 'line_index':'one-based current line index','column_chars':'Unicode characters since the last newline',
 'indent_spaces':'leading spaces of the current line (a tab counts as four spaces)',
 'line_words':'word tokens observed on the current line','sentence_words':'word tokens after the last observed . ! or ?',
 'paragraph_sentences':'one plus completed sentence terminators in the current blank-line-delimited paragraph',
 'table_column':'one-based current Markdown pipe-delimited cell (escaped pipes and inline-code pipes ignored)',
 'list_items':'Markdown bullet/ordered item starts observed in the prefix','list_depth':'current Markdown item depth (two spaces per level)',
 'number_magnitude':'absolute value of a numeric lexeme ending at the current character',
 'number_digits':'digit characters in that numeric lexeme (including exponent digits)',
 'line_commas':'commas observed on the current line','latex_sections':'completed section/subsection commands observed outside TeX comments',
 'latex_items':'completed item commands observed outside TeX comments',
}
OVERLAPS={
 'paren_depth':('prose_paren','python_depth'), 'square_depth':('python_depth',),
 'brace_depth':('python_depth','latex_brace','json_depth'),'bracket_depth':('python_depth','latex_brace','json_depth'),
 'line_index':('python_line',),'column_chars':('prose_column',),'indent_spaces':('python_indent',),
 'line_words':('list_words',),'sentence_words':('prose_words',),'paragraph_sentences':('prose_sentence',),
 'table_column':('table_column',),'list_items':('list_index',),'list_depth':('list_depth',),
 'latex_sections':('latex_section',),'latex_items':('latex_item',),
}
# Topic/grammar labels explicitly refer to exact frozen lexical evidence only.
LEXICONS={
 'math': 'theorem lemma proof equation algebra geometry matrix polynomial integral vector',
 'computing':'code function python algorithm software program computer database server variable',
 'science':'experiment scientific research physics chemistry molecule laboratory hypothesis',
 'medicine':'patient disease medical treatment doctor clinical health cancer medicine',
 'politics':'government election president minister parliament political vote democracy',
 'economics':'market price economy trade bank inflation revenue finance investment',
 'sport':'game match team player league football baseball tennis championship',
 'arts':'music painting artist film novel theatre theater poem sculpture',
 'nature':'forest river ocean animal species plant wildlife mountain tree',
 'law':'court legal law judge lawyer statute regulation rights contract',
 'education':'student school university teacher education class college lesson',
 'food':'food recipe cooking bread rice meal restaurant kitchen',
 'travel':'travel hotel airport train journey tourist flight destination',
 'history':'century ancient medieval historical empire dynasty war king',
 'positive':'good great excellent wonderful happy joy love beautiful success',
 'negative':'bad poor terrible awful sad hate failure painful damage',
 'negation':'no not never neither nobody nothing without',
 'uncertainty':'might may perhaps possibly maybe uncertain probably',
 'obligation':'must should required shall obligatory necessary',
 'first_person':'i me my mine we us our ours',
 'second_person':'you your yours yourself yourselves',
 'third_person':'he him his she her hers they them their theirs',
 'past_auxiliary':'was were had did',
 'present_auxiliary':'am is are has have does',
 'future_auxiliary':'will shall',
 'conditional':'if unless otherwise provided assuming',
 'causal':'because therefore hence thus consequently since',
 'comparison':'than more less better worse higher lower',
 'question_word':'who what where when why how which whom',
 'politeness':'please thanks thank welcome kindly',
 'formal_register':'therefore furthermore moreover pursuant hereby respectively',
 'informal_register':'yeah yep nope gonna wanna lol cool dude',
 'french_function':'le la les une des est sont avec pour dans mais',
 'spanish_function':'el los las una unos es son para pero con del',
 'german_function':'der die das ein eine und ist sind mit nicht auf',
}
LEXICONS={k:frozenset(v.split()) for k,v in LEXICONS.items()}
CLOSED_CLASSES={
 'pronoun':'i me we us you he him she her it they them who whom',
 'determiner':'a an the this that these those each every some any',
 'preposition':'in on at by for from to with without under over between',
 'conjunction':'and or but nor yet so although because while unless',
 'auxiliary':'am is are was were be been being have has had do does did can could will would shall should may might must',
}
CLOSED_CLASSES={k:frozenset(v.split()) for k,v in CLOSED_CLASSES.items()}
WORD=re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*",re.UNICODE)
STATES={
 'inside_paren':'inside an unclosed parenthesis outside strings/comments',
 'inside_square':'inside an unclosed square bracket outside strings/comments',
 'inside_brace':'inside an unclosed brace outside strings/comments',
 'inside_string':'inside a quoted span (Python triple strings supported)',
 'inside_single_quote':'inside a single-quoted span',
 'inside_double_quote':'inside a double-quoted span',
 'inside_triple_quote':'inside a Python triple-quoted string',
 'inside_comment':'inside a Python # comment or TeX % comment on the current line',
 'inside_fence':'inside an unclosed Markdown backtick/tilde code fence',
 'inside_inline_code':'inside an unclosed Markdown inline backtick span',
 'inside_math':'inside a TeX dollar/bracket/math-environment span',
 'inside_display_math':'inside a TeX display-dollar/bracket/math environment',
 'inside_latex_environment':'inside any unclosed complete TeX begin/end environment',
 'inside_latex_table':'inside a TeX tabular, tabular* or array environment',
 'inside_latex_itemize':'inside a TeX itemize or enumerate environment',
 'line_blank':'on a line containing only whitespace so far',
 'line_heading':'on a Markdown ATX heading whose marker and following space have appeared',
 'line_bullet':'on a Markdown bullet-list line',
 'line_ordered':'on a Markdown ordered-list line',
 'line_task':'on a Markdown task-list line',
 'line_task_checked':'on a checked Markdown task-list line',
 'line_table':'on a line with an observed Markdown table separator pipe',
 'word_allcaps':'the current word has at least two letters and is uppercase',
 'word_titlecase':'the current word has at least two letters and is title case',
 'word_lowercase':'the current word has letters and is lowercase',
 'word_nonascii':'the current word includes a non-ASCII letter',
 'current_number':'a complete numeric lexeme ends at the current character',
 'current_question':'the last observed non-space character is a question mark',
 'current_colon':'the last observed non-space character is a colon',
 'unmatched_close':'an unmatched closing bracket has occurred outside strings/comments',
}


def _eligible(family):
 if family.startswith('latex_') or family in {'inside_math','inside_display_math','inside_latex_environment','inside_latex_table','inside_latex_itemize'}:return ('latex',)
 if family in {'table_column','list_items','list_depth','inside_fence','inside_inline_code','line_heading','line_bullet','line_ordered','line_task','line_task_checked','line_table'}:return ('markdown',)
 if family=='inside_triple_quote':return ('python',)
 if family=='inside_comment':return ('python','latex')
 return DOMAINS


def _registry():
 result=[]
 for family,thresholds in COUNTERS.items():
  for threshold in thresholds:
   desc=DESCRIPTIONS[family];result.append(Feature(f'{family}_ge_{threshold}','count-like',family,f'{desc} ≥ {threshold}',f'{desc} is at least {threshold}',f'{desc} is less than {threshold}',_eligible(family),threshold,OVERLAPS.get(family,())))
 for family,definition in STATES.items():
  overlap=OVERLAPS.get({'inside_paren':'paren_depth','inside_square':'square_depth','inside_brace':'brace_depth','line_table':'table_column'}.get(family,''),())
  overlap=overlap+({'inside_string':('prose_quote','python_string','json_type'),'inside_single_quote':('prose_quote','python_string'),'inside_double_quote':('prose_quote','python_string','json_type'),'inside_math':('latex_math',),'inside_display_math':('latex_math',),'line_bullet':('list_ordered',),'line_ordered':('list_ordered',),'line_task':('list_task',),'line_task_checked':('list_task',)}.get(family,()))
  result.append(Feature(family,'state-like',family,definition,definition,'it is not the case that '+definition,_eligible(family),None,overlap))
 for family,words in LEXICONS.items():
  definition=f'the current paragraph contains a word from the frozen {family} lexicon (case-insensitive)';overlap=('prose_topic','latex_subject','list_topic') if family in {'math','computing','nature','travel','education','science'} else ('prose_sentiment',) if family in {'positive','negative'} else ()
  result.append(Feature('lexicon_'+family,'semantic','lexicon_'+family,definition,definition,'it is not the case that '+definition,DOMAINS,None,overlap))
 for family in CLOSED_CLASSES:
  desc=f'the current word belongs to the frozen {family} word list (lexical membership, not contextual POS)';result.append(Feature('wordlist_'+family,'semantic','wordlist_'+family,desc,desc,'it is not the case that '+desc))
 return tuple(result)
FEATURES=_registry()
BY_ID={f.id:f for f in FEATURES}
assert len(FEATURES)>=100 and len(BY_ID)==len(FEATURES)


def _syntax(text,domain):
 stack=[];quote='';comment=False;fence='';inline=0;math_mode='';env=[];unmatched=False;sections=items=0;i=0
 while i<len(text):
  c=text[i]
  if comment:
   if c=='\n':comment=False
   i+=1;continue
  # Fences are recognized at line start, with at most three leading spaces.
  line_start=i==0 or text[i-1]=='\n'
  if domain=='markdown' and line_start:
   m=re.match(r' {0,3}(`{3,}|~{3,})',text[i:])
   if m:
    run=m.group(1)
    if not fence:fence=run
    elif run[0]==fence[0] and len(run)>=len(fence):fence=''
    i+=m.end();continue
  if fence:i+=1;continue
  if quote:
   if c=='\\':i+=2;continue
   if text.startswith(quote,i):i+=len(quote);quote='';continue
   i+=1;continue
  if domain=='markdown' and c=='`':
   run=len(text[i:])-len(text[i:].lstrip('`'))
   if not inline:inline=run
   elif inline==run:inline=0
   i+=run;continue
  if inline:i+=1;continue
  if (domain=='python' and c=='#') or (domain=='latex' and c=='%'):comment=True;i+=1;continue
  if domain=='latex' and c=='\\':
   m=re.match(r'\\(begin|end)\{([^{}]+)\}',text[i:])
   if m:
    kind,name=m.groups()
    if kind=='begin':env.append(name)
    elif env and env[-1]==name:env.pop()
    i+=m.end();continue
   m=re.match(r'\\(subsection|section|item)\b',text[i:])
   if m:
    if m.group(1)=='item':items+=1
    else:sections+=1
    i+=m.end();continue
   pair=text[i:i+2]
   if pair in ('\\(','\\['):math_mode=pair;i+=2;continue
   if pair in ('\\)','\\]'):
    if math_mode=={'\\)':'\\(','\\]':'\\['}[pair]:math_mode=''
    i+=2;continue
   if len(pair)==2 and pair[1] in '{}$%[]()\\':i+=2;continue
   i+=1;continue
  if domain=='latex' and c=='$':
   run='$$' if text.startswith('$$',i) else '$'
   if not math_mode:math_mode=run
   elif math_mode==run:math_mode=''
   i+=len(run);continue
  if c=='\\' and domain!='latex':i+=2;continue
  if c in ('"',"'",'“','‘'):
   # An internal apostrophe is a word character, not a quotation opener.
   if domain!='python' and c=="'" and i>0 and text[i-1].isalnum():i+=1;continue
   quote={'“':'”','‘':'’'}.get(c,c)
   if domain=='python' and text.startswith(c*3,i):quote=c*3
   i+=len(quote);continue
  if c in '([{':stack.append(c)
  elif c in ')]}':
   if stack and stack[-1]=={')':'(',']':'[','}':'{'}[c]:stack.pop()
   else:unmatched=True
  i+=1
 mathenv={'math','displaymath','equation','equation*','align','align*','eqnarray','eqnarray*','gather','gather*','multline','multline*','split','cases','matrix','pmatrix','bmatrix'}
 return {'stack':stack,'quote':quote,'comment':comment,'fence':fence,'inline':inline,'math_mode':math_mode,'env':env,'mathenv':bool(set(env)&mathenv),'unmatched':unmatched,'sections':sections,'items':items}


def _pipes(line):
 # This view only needs pipe/backtick/escape syntax, not the bracket scanner.
 count=0;inline=0;i=0
 while i<len(line):
  if line[i]=='\\':i+=2;continue
  if line[i]=='`':
   n=len(line[i:])-len(line[i:].lstrip('`'));inline=0 if inline==n else n if not inline else inline;i+=n;continue
  if line[i]=='|' and not inline:count+=1
  i+=1
 return count


def measurements(prefix,domain):
 if not isinstance(prefix,str):raise TypeError('prefix must be text')
 if domain not in DOMAINS:raise ValueError('unknown domain '+str(domain))
 s=_syntax(prefix,domain);line=prefix.rsplit('\n',1)[-1];paragraph=re.split(r'\n\s*\n',prefix)[-1]
 words=WORD.findall(paragraph.casefold());wordset=set(words);last=WORD.search(prefix)
 last_word=None
 for m in WORD.finditer(prefix):
  if m.end()==len(prefix):last_word=m.group()
 numeric=re.search(r'(?<![\w.])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?$',prefix)
 number=numeric.group() if numeric else None
 try:magnitude=abs(float(number)) if number else None
 except ValueError:magnitude=None
 listmatch=re.match(r'([ \t]*)([-+*]|\d+[.)])\s+',line)
 pipes=0 if s['fence'] else _pipes(line);leading=bool(re.match(r'\s*\|',line));column=max(1,pipes if leading else pipes+1) if pipes else None
 v={'paren_depth':s['stack'].count('('),'square_depth':s['stack'].count('['),'brace_depth':s['stack'].count('{'),'bracket_depth':len(s['stack']),
 'line_index':prefix.count('\n')+1,'column_chars':len(line),'indent_spaces':len(line)-len(line.lstrip(' \t'))+3*len(re.match(r'[ \t]*',line).group().replace(' ','')),
 'line_words':len(WORD.findall(line)),'sentence_words':len(WORD.findall(re.split(r'[.!?]',paragraph)[-1])),
 'paragraph_sentences':1+len(re.findall(r'[.!?]+',paragraph)),
 'table_column':column,'list_items':len(re.findall(r'(?m)^[ \t]*(?:[-+*]|\d+[.)])\s+',prefix)),
 'list_depth':(len(listmatch.group(1).expandtabs(4))//2+1) if listmatch else None,
 'number_magnitude':magnitude,'number_digits':sum(c.isdigit() for c in number) if number else None,
 'line_commas':line.count(','),'latex_sections':s['sections'],'latex_items':s['items']}
 v.update(inside_paren='(' in s['stack'],inside_square='[' in s['stack'],inside_brace='{' in s['stack'],
 inside_string=bool(s['quote']),inside_single_quote=s['quote'] in ("'","'''"),inside_double_quote=s['quote'] in ('"','"""'),inside_triple_quote=len(s['quote'])==3,
 inside_comment=s['comment'],inside_fence=bool(s['fence']),inside_inline_code=bool(s['inline']),
 inside_math=bool(s['math_mode']) or s['mathenv'],inside_display_math=s['math_mode'] in ('$$','\\[') or s['mathenv'],
 inside_latex_environment=bool(s['env']),inside_latex_table=bool(set(s['env'])&{'tabular','tabular*','array'}),inside_latex_itemize=bool(set(s['env'])&{'itemize','enumerate'}),
 line_blank=not line.strip(),line_heading=bool(re.match(r' {0,3}#{1,6}\s',line)),line_bullet=bool(listmatch and listmatch.group(2) in '-+*'),line_ordered=bool(listmatch and listmatch.group(2)[0].isdigit()),
 line_task=bool(re.match(r'\s*[-+*]\s+\[[ xX]\]\s',line)),line_task_checked=bool(re.match(r'\s*[-+*]\s+\[[xX]\]\s',line)),line_table=pipes>0,
 word_allcaps=(len(last_word)>=2 and last_word.isupper()) if last_word else None,word_titlecase=(len(last_word)>=2 and last_word.istitle()) if last_word else None,
 word_lowercase=last_word.islower() if last_word else None,word_nonascii=any(ord(c)>127 for c in last_word) if last_word else None,
 current_number=number is not None,current_question=prefix.rstrip().endswith('?'),current_colon=prefix.rstrip().endswith(':'),unmatched_close=s['unmatched'])
 for family,lexicon in LEXICONS.items():v['lexicon_'+family]=bool(wordset&lexicon)
 for family,lexicon in CLOSED_CLASSES.items():v['wordlist_'+family]=(last_word.casefold() in lexicon) if last_word else None
 return v


def extract(prefix,domain):
 """Map every frozen feature ID to bool or None, using only this prefix."""
 m=measurements(prefix,domain);out={}
 for f in FEATURES:
  value=m[f.family] if domain in f.domains else None
  out[f.id]=None if value is None else bool(value>=f.threshold) if f.threshold is not None else bool(value)
 return out


def registry():return [f.record() for f in FEATURES]
