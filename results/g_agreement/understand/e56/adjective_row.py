"""§172 clarification 1: coordinated adjectives/nouns at identical read token and.
Content vocabulary is separated by label within split and held out across splits.
"""
import re
from common56 import *
SPEC=RowSpec('adjective_implicit',('adjective','noun'),'semantic_state','and')
SUBJECT_A=(('room','hall','office','house','garden','kitchen','station'),('cabin','shed','cellar','tower','attic','studio','porch'))
SUBJECT_B=(('boy','girl','man','woman','chef','guard','clerk'),('sailor','farmer','baker','pilot','nurse','doctor','artist'))
VERB_A=('seems','looks','feels','stays','remains','appears','was','is','became','grew','turned','proved')
VERB_B=('bought','carried','packed','ordered','found','selected','brought','painted','stored','moved','shipped','borrowed')
ADJECTIVES=('quiet','bright','empty','warm','clean','calm','cold','dark','large','small','safe','dry')
OBJECTS=(('bread','rice','milk','fruit','coffee','tea','water'),('wood','steel','glass','paper','cloth','leather','stone'))

def render(t,f,v):
 s=int(t>=6)
 if v==0:return 'The '+SUBJECT_A[s][f]+' '+VERB_A[t]+' '+ADJECTIVES[t]+' and'
 return 'The '+SUBJECT_B[s][f]+' '+VERB_B[t]+' '+OBJECTS[s][f]+' and'
def generate():return [Item(SPEC.row_id,t,f,v,render(t,f,v),SPEC.values[v]) for t in range(12) for f in range(7) for v in range(2)]
def check_label(text):
 m=re.fullmatch(r'The (\w+) (\w+) (\w+) and',text)
 if not m:raise ValueError('unexpected coordination prefix')
 subject,verb,predicate=m.groups()
 if subject in sum(SUBJECT_A,()) and verb in VERB_A and predicate in ADJECTIVES:return 'adjective'
 if subject in sum(SUBJECT_B,()) and verb in VERB_B and predicate in sum(OBJECTS,()):return 'noun'
 raise ValueError('unsupported syntactic frame')
def content_words(text):return set(re.findall(r'[A-Za-z]+',text.lower()))-{'the','and'}
