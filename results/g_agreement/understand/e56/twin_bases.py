"""Implicit E56 bases, before any asked-span transformation."""
import re
from common56 import *
SPECS={
 'tense_implicit':RowSpec('tense_implicit',('past','present'),'semantic_state','gate'),
 'linewrap_implicit':RowSpec('linewrap_implicit',('short','long'),'semantic_state','notes'),
 'language_continuation':RowSpec('language_continuation',('French','German'),'semantic_state','')}
TENSE=(
 ('The keeper walked along the path and checked the lock.','The keeper walks along the path and checks the lock.'),
 ('The guard crossed the yard and watched the entrance.','The guard crosses the yard and watches the entrance.'),
 ('The porter inspected the latch and carried the key.','The porter inspects the latch and carries the key.'),
 ('The visitor entered the courtyard and greeted the guard.','The visitor enters the courtyard and greets the guard.'),
 ('The caretaker opened the door and examined the hinge.','The caretaker opens the door and examines the hinge.'),
 ('The warden approached the doorway and tested the bell.','The warden approaches the doorway and tests the bell.'),
 ('The worker cleaned the handle and polished the brass.','The worker cleans the handle and polishes the brass.'),
 ('The messenger reached the entrance and rang the bell.','The messenger reaches the entrance and rings the bell.'),
 ('The inspector observed the passage and noted the time.','The inspector observes the passage and notes the time.'),
 ('The gardener passed the hedge and closed the latch.','The gardener passes the hedge and closes the latch.'),
 ('The steward left the hall and visited the lodge.','The steward leaves the hall and visits the lodge.'),
 ('The watchman followed the path and checked the sign.','The watchman follows the path and checks the sign.'))
LINES=(
 'The clerk reviewed the dated forms and carefully transcribed the notes',
 'The visitor inspected the written record and then copied all the notes',
 'The editor examined the recent entries and carefully checked the notes',
 'The assistant sorted the printed pages and then transcribed the notes',
 'The archivist opened the old register and carefully copied the notes',
 'The manager reviewed the signed document and then checked all the notes',
 'The reader compared the two printed copies and transcribed the notes',
 'The curator studied the archived letters and carefully checked the notes',
 'The secretary examined the original forms and then copied the notes',
 'The reporter reviewed the official account and transcribed the notes',
 'The researcher inspected the complete record and then copied the notes',
 'The auditor checked the dated ledger and carefully transcribed the notes')
LANGUAGE=(
 ('Le visiteur regarde la porte du café','Der Besucher betrachtet die Tür des Cafés'),
 ('La voyageuse attend près du café','Die Reisende wartet neben dem Café'),
 ('Le facteur marche devant le café','Der Briefträger geht vor dem Café'),
 ('La voisine parle au serveur du café','Die Nachbarin spricht mit dem Kellner des Cafés'),
 ('Le musicien cherche une table au café','Der Musiker sucht einen Tisch im Café'),
 ('La lectrice pose son livre dans le café','Die Leserin legt ihr Buch in das Café'),
 ('Le touriste examine la carte du café','Der Tourist betrachtet die Karte des Cafés'),
 ('La cliente choisit une chaise au café','Die Kundin wählt einen Stuhl im Café'),
 ('Le jardinier apporte des fleurs au café','Der Gärtner bringt Blumen zum Café'),
 ('La journaliste rencontre le patron du café','Die Journalistin trifft den Besitzer des Cafés'),
 ('Le professeur retrouve ses amis au café','Der Lehrer trifft seine Freunde im Café'),
 ('La dessinatrice observe les fenêtres du café','Die Zeichnerin betrachtet die Fenster des Cafés'))
CAFES=('Atlas','Orion','Solis','Luna','Nova','Vega','Delta')

def render(row,t,f,v):
 c=context(t,f)
 if row=='tense_implicit':
  pair=[x+' The attendant beside the gate' for x in TENSE[t]]
  return c+'Archived passage:\n'+pair[1-v]+'.\nEnd of archived passage.\nCurrent passage:\n'+pair[v]
 if row=='linewrap_implicit':
  words=LINES[t].split(' ');prefix=c+'The document continues beyond this record'
  return prefix+(' '+' '.join(words[:-1])+' \n '+words[-1] if v==0 else ' \n '+' '.join(words))
 if row=='language_continuation':
  pair=[x+' '+CAFES[f] for x in LANGUAGE[t]]
  return c+'Archived passage:\n'+pair[1-v]+'.\nEnd of archived passage.\nCurrent passage:\n'+pair[v]
 raise ValueError(row)

def generate(row):return [Item(row,t,f,v,render(row,t,f,v),SPECS[row].values[v]) for t in range(12) for f in range(7) for v in range(2)]

def check_label(row,text):
 if row=='linewrap_implicit':
  if not text.endswith('notes'):raise ValueError('wrong read token')
  n=len(text.rsplit('\n',1)[-1])
  if n<=15:return 'short'
  if n>=55:return 'long'
  raise ValueError('line length outside bins')
 tail=text.rsplit('Current passage:\n',1)
 if len(tail)!=2:raise ValueError('missing current passage')
 if row=='tense_implicit':
  for pair in TENSE:
   for v,s in enumerate(pair):
    if tail[1]==s+' The attendant beside the gate':return SPECS[row].values[v]
 elif row=='language_continuation':
  for pair in LANGUAGE:
   for v,s in enumerate(pair):
    if any(tail[1]==s+' '+name for name in CAFES):return SPECS[row].values[v]
 raise ValueError('unsupported current passage')
