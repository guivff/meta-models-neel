"""§171 clarification 1: cat/dog bridge, identical answer digit 4 in every family."""
import re
from common54 import Item,RowSpec,length_match
SPEC=RowSpec('reasoning_bridge',('cat','dog'),'semantic_state',':')
QUESTIONS=(
 'How many legs does a typical adult household pet that {cue} have?',
 'What is the number of legs on a typical adult domestic pet known for {sound}?',
 'For a typical adult household animal that {cue}, how many legs are there?',
 'Count the legs of a typical adult domestic pet whose characteristic sound is {sound}. What number is the count?',
 'A familiar household pet is identified by {sound}. How many legs does a typical adult of that animal have?',
 'Which number gives the leg count of a typical adult household pet that {cue}?',
 'Consider the domestic pet associated with {sound}. What is its typical adult leg count?',
 'Identify the familiar household animal that {cue}. How many legs does a typical adult have?',
 'For the domestic animal recognized by {sound}, what number of legs does a typical adult possess?',
 'Start with the familiar household pet that {cue}. What is the number of legs on a typical adult?',
 'The characteristic sound of a household pet is {sound}. What number describes its typical adult leg count?',
 'Take the familiar domestic pet known for {sound}. How many legs would a typical adult have?')
CUES=(dict(cue='purrs',sound='purring'),dict(cue='barks',sound='barking'))
FILLERS=('courtyard','library','station','workshop','garden','museum','kitchen')
FAMILY_BRIDGES=[{'template_index':t,'A':'cat','B':'dog','answer_digit_A':'4','answer_digit_B':'4'} for t in range(12)]
PHRASINGS=(("- The intermediate animal is a cat.","- The intermediate animal is a dog."),
           ("- The current question requires reasoning through a cat.","- The current question requires reasoning through a dog."))
CONTINUATIONS=None
CONTINUATION_REASON='NOT APPLICABLE by §171 clarification 1: A cat and B dog both give answer digit 4; only bridge identity differs.'
MENTION_PATTERNS={'cat':r'\bcat(?:s)?\b','dog':r'\bdog(?:s)?\b'}

def generate():
 out=[]
 for t,form in enumerate(QUESTIONS):
  pair=[form.format(**cue) for cue in CUES]
  for f,place in enumerate(FILLERS):
   for v in range(2):
    text=f'This exercise was recorded in the {place}. Only answer the current question with a single digit. The archived question is not the current task.\nArchived question:\n{pair[1-v]}\nEnd of archived question.\nCurrent question:\n{pair[v]}\nAnswer:'
    out.append(Item(SPEC.row_id,t,f,v,text,SPEC.values[v]))
 return out

def check_label(text):
 matches=re.findall(r'^Current question:\n([^\n]+)\nAnswer:$',text,re.M)
 if len(matches)!=1:raise ValueError('ambiguous current question or wrong read position')
 lookup={form.format(**cue):value for form in QUESTIONS for cue,value in zip(CUES,SPEC.values)}
 if matches[0] not in lookup:raise ValueError('unknown two-hop question')
 archived=re.findall(r'^Archived question:\n([^\n]+)\nEnd of archived question\.$',text,re.M)
 if len(archived)!=1 or archived[0] not in lookup or lookup[archived[0]]==lookup[matches[0]]:raise ValueError('require the other bridge in the archived question')
 return lookup[matches[0]]
