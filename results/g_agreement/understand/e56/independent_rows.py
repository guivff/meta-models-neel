"""E56 fresh no-twin and positive-control generators; no prior outcome imports."""
import re
from common56 import *
SPECS={
 'anomaly_state':RowSpec('anomaly_state',('foreign_sentence','no_foreign_sentence'),'semantic_state','folder'),
 'fact_recall':RowSpec('fact_recall',('Paris','Lima'),'semantic_state','is'),
 'rhyme_plan':RowSpec('rhyme_plan',('fight','light'),'semantic_state','the'),
 'instructed_focus':RowSpec('instructed_focus',('citrus_fruits','birds'),'semantic_state','window')}
NEUTRAL=('The clerk put the papers on the desk.','The visitor checked the date on the form.','The assistant placed the record in the drawer.','The editor looked at the clock on the wall.')
VERSE=('The boxer readied for the','The soldier braced for the','The rivals trained for the','The champion prepared for the','The fighter rested before the','The challenger waited for the','The contenders gathered for the','The warrior steeled himself for the','The wrestler warmed up for the','The duellist made ready for the','The combatants lined up for the','The opponent practised for the')
LIGHT=('The lantern filled the room with the','The candle filled the hall with the','The lamp filled the porch with the','The torch filled the cave with the','The beacon filled the bay with the','The flashlight filled the path with the','The streetlamp filled the road with the','The chandelier filled the room with the','The floodlight filled the yard with the','The bulb filled the room with the','The headlamp filled the tunnel with the','The candlelight filled the chamber with the')
FIRST_LINES=('The crowd fell silent in the night','The moon above was clear and bright','The distant stars came into sight','The clouds were pale and almost white','The hills were dark against the night','The moonlit path was shining bright','The quiet town lay out of sight','The falling snow was soft and white','The weary crowd stayed through the night','The rising moon was silver bright','The empty road stretched out of sight','The drifting mist was ghostly white')

def render(row,t,f,v):
 c=context(t,f)
 if row=='anomaly_state':
  glossary='[ The ] [ moon ] [ is ] [ bright ]' if v==0 else '[ La ] [ lune ] [ est ] [ claire ]'
  sentence='La lune est claire.' if v==0 else 'The moon is bright.'
  return c+'Vocabulary entries: '+glossary+'. '+sentence+' '+' '.join(NEUTRAL[:2+t%3])+' The reader reached for the folder'
 if row=='fact_recall':
  values=('France','Peru')
  return c+'Only complete the current question.\nArchived question: The capital of '+values[1-v]+' is\nEnd of archived question.\nCurrent question: The capital of '+values[v]+' is'
 if row=='rhyme_plan':
  return c+'Complete the couplet with one word that rhymes with the end of the first line.\n'+FIRST_LINES[t]+'\n'+(VERSE[t] if v==0 else LIGHT[t])
 if row=='instructed_focus':
  focus=('citrus fruits','birds')
  return c+'Archived instruction: Concentrate on '+focus[1-v]+'. This instruction is no longer active.\nCurrent instruction: Concentrate on '+focus[v]+'. While keeping that focus, copy the unrelated sentence exactly.\nSentence to copy: The clerk carried the folder past the window and into the hall.\nCopy: The clerk carried the folder past the window'
 raise ValueError(row)

def generate(row):return [Item(row,t,f,v,render(row,t,f,v),SPECS[row].values[v]) for t in range(12) for f in range(7) for v in range(2)]

def check_label(row,text):
 if not text.endswith(SPECS[row].read_token_rule):raise ValueError('wrong read position')
 if row=='anomaly_state':
  m=re.search(r'Vocabulary entries: (.*?)\. (La lune est claire\.|The moon is bright\.) ',text)
  if not m:raise ValueError('missing controlled sentence')
  expected='[ The ] [ moon ] [ is ] [ bright ]' if m[2]=='La lune est claire.' else '[ La ] [ lune ] [ est ] [ claire ]'
  if m[1]!=expected:raise ValueError('glossary control mismatch')
  n=sum(x in text for x in NEUTRAL)
  if n not in (2,3,4):raise ValueError('anomaly lag outside 2–4')
  return 'foreign_sentence' if m[2]=='La lune est claire.' else 'no_foreign_sentence'
 if row=='fact_recall':
  m=re.search(r'Current question: The capital of (France|Peru) is$',text)
  if not m:raise ValueError('ambiguous current recall')
  return 'Paris' if m[1]=='France' else 'Lima'
 if row=='rhyme_plan':
  line=text.rsplit('\n',1)[-1]
  if line in VERSE:return 'fight'
  if line in LIGHT:return 'light'
  raise ValueError('unknown planned rhyme context')
 if row=='instructed_focus':
  m=re.findall(r'^Current instruction: Concentrate on (citrus fruits|birds)\.',text,re.M)
  if len(m)!=1:raise ValueError('ambiguous active focus')
  return 'citrus_fruits' if m[0]=='citrus fruits' else 'birds'
 raise ValueError(row)
