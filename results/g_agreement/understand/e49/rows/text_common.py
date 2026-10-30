"""New E49 W-text generators; no existing banks, outcomes or filler imports."""
import itertools,re
from .interface import Item,RowSpec,length_match,relabel_twin
FRAGMENTS=('the clerk checked the record.','the visitor reviewed the notes.','the assistant kept the pages.','the editor confirmed the date.')
ORDERS=list(itertools.permutations(range(4)))[:12]
OBJECTS=('coin','key','badge','token','ring','stamp','card')
NAMES=(('Mara','Nora'),('Lina','Rosa'),('Anna','Sara'),('Maya','Nina'),('Clara','Diana'),('Julia','Maria'),('Tara','Lara'))
VERBS=('handed','passed','gave','lent','offered','delivered','handed','passed','gave','lent','offered','delivered')
TOPICS=('optics','acoustics','botany','geology','robotics','astronomy','chemistry')

def context(t,f):
 return 'A written record follows. '+ ' '.join(FRAGMENTS[i] for i in ORDERS[t])+' Record subject: '+OBJECTS[f]+'. '

SPECS={
 'pronoun_referent':RowSpec('pronoun_referent',('giver','receiver'),'semantic_state','she'),
 'chased_role':RowSpec('chased_role',('thief','policeman'),'semantic_state','the'),
 'asserted_vs_hypothetical':RowSpec('asserted_vs_hypothetical',('asserted','hypothetical'),'semantic_state','system'),
 'negation_scope':RowSpec('negation_scope',('negated','unnegated'),'semantic_state','disabled'),
 'topic_twin':RowSpec('topic_twin',('engineering','gardening'),'descriptor','system','asserted_vs_hypothetical'),
 'next_paragraph_language':RowSpec('next_paragraph_language',('French','English'),'descriptor','\n\n'),
 'unit_system':RowSpec('unit_system',('metric','imperial'),'descriptor','3')}

def render(row,t,f,side):
 c=context(t,f);obj=OBJECTS[f]
 if row=='pronoun_referent':
  a,b=NAMES[f];giver,receiver=(a,b) if side==0 else (b,a)
  return c+f'At the meeting, {giver} {VERBS[t]} {receiver} the {obj}. The discussion then turned to {a}; speaking only about {a}, she'
 if row=='chased_role':
  a,b=('thief','policeman') if side==0 else ('policeman','thief')
  locations=('courtyard','market','station','garden','harbor','square','bridge')
  return c+f'In the {locations[f]}, the {a} chased the {b}. The observer followed the movement carefully. The one running away was the'
 if row=='asserted_vs_hypothetical':
  first,last=('Suppose, counterfactually, that','It is the case that') if side==0 else ('It is the case that','Suppose, counterfactually, that')
  claim=('the engineer inspected the safety interlock and adjusted the protection system' if t%2==0 else 'the gardener inspected the flower beds and adjusted the irrigation system')
  return c+first+' the visitor completed the ordinary inspection. That passage ends here. '+last+' after the clerk reviewed the dated notes and checked every entry in the report, '+claim
 if row=='negation_scope':
  first,last=('It is clear that','It is false that') if side==0 else ('It is false that','It is clear that')
  return c+first+' the visitor finished the routine report. That claim ends here. '+last+' after the staff checked the equipment and recorded the date in the maintenance ledger, the safety interlock was disabled'
 if row=='next_paragraph_language':
  en=f'The clerk checked the {obj} and recorded the date. The visitor read the note carefully.'
  fr='Le greffier a vérifié le dossier et noté la date. Le visiteur a lu la note avec attention.'
  paragraphs=[en,fr,en] if side==0 else [fr,en,fr]
  return c+'The following paragraphs alternate between English and French.\n\n'+'\n\n'.join(paragraphs)+'\n\n'
 if row=='unit_system':
  units=('metric','litres','grams','metres') if side==0 else ('imperial','quarts','ounces','feet')
  comma='Format note: use a comma between the integer and fractional digits.'
  point='Format note: use a point between the integer and fractional digits.'
  first,last=(point,comma) if t%2==0 else (comma,point)
  return c+f'This guide uses {units[0]} units. Earlier quantities were 2 {units[1]}, 4 {units[2]}, and 6 {units[3]}. '+first+' '+last+' The final format note overrides the earlier note. The next measurement is a length of 3'
 raise ValueError(row)

def check(row,text):
 if row=='pronoun_referent':
  m=re.search(r'At the meeting, (\w+) (?:handed|passed|gave|lent|offered|delivered) (\w+) the \w+\.',text)
  who=re.search(r'speaking only about (\w+), she$',text)
  if not m or not who or who[1] not in m.groups():raise ValueError('ambiguous pronoun binding')
  return 'giver' if who[1]==m[1] else 'receiver'
 if row=='chased_role':
  m=re.search(r'the (thief|policeman) chased the (thief|policeman)\.',text)
  if not m or m[1]==m[2]:raise ValueError('invalid chase')
  return m[1]
 if row=='asserted_vs_hypothetical':
  tail=text.split('That passage ends here. ')[-1]
  if tail.startswith('It is the case that '):return 'asserted'
  if tail.startswith('Suppose, counterfactually, that '):return 'hypothetical'
  raise ValueError('missing open scope')
 if row=='negation_scope':
  tail=text.split('That claim ends here. ')[-1]
  if tail.startswith('It is false that '):return 'negated'
  if tail.startswith('It is clear that '):return 'unnegated'
  raise ValueError('missing negation scope')
 if row=='topic_twin':
  tail=text.split('That passage ends here. ')[-1]
  a='the engineer inspected the safety interlock' in tail;b='the gardener inspected the flower beds' in tail
  if a==b:raise ValueError('ambiguous topic')
  return 'engineering' if a else 'gardening'
 if row=='next_paragraph_language':
  tail=text.rstrip().split('\n\n')[-1]
  if tail.startswith('The clerk '):return 'French'
  if tail.startswith('Le greffier '):return 'English'
  raise ValueError('unrecognized last paragraph')
 if row=='unit_system':
  m=re.search(r'This guide uses (metric|imperial) units\.',text)
  if not m:raise ValueError('missing unit convention')
  return m[1]
 raise ValueError(row)

def generate(row,source=None):
 spec=SPECS[row]
 if spec.twin_of:return relabel_twin(source,spec,lambda text:check(row,text))
 return [Item(row,t,f,side,render(row,t,f,side),spec.values[side]) for t in range(12) for f in range(7) for side in range(2)]
