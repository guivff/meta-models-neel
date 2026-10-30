"""Fresh E46 authoring from §157 definitions only; no prior item/score imports.
The short-row source-bound labels remain provisional until the coordinator rules.
"""
TOPICS=('harbor','orchard','archive','workshop','meadow','observatory','courtyard')
WORDS=('microarchitecture','electrochemistry','bioluminescence','cartography','thermodynamics','photosynthesis','crystallography')
COMPLETE=('map','bell','lamp','book','road','gate','tree')
INTROS=(
 'A visitor wrote a short account of the {topic}. The following passage was copied into the report.',
 'The afternoon record concerns the {topic}. A clerk arranged the notes under a plain heading.',
 'During the survey of the {topic}, the team kept a written record. Here is the next portion of that record.',
 'A new guide describes the {topic}. The editor asked for a brief passage without abbreviations.',
 'The ledger for the {topic} contains several observations. This entry belongs to the latest inspection.',
 'A researcher visited the {topic} before lunch. These notes preserve a small part of the visit.',
 'The weekly bulletin includes an account of the {topic}. Its author supplied the passage below.',
 'An apprentice described the {topic} in a notebook. The supervisor retained the following entry.',
 'The committee received a report about the {topic}. A copy of one passage follows here.',
 'Several volunteers helped document the {topic}. They placed the next observation in their shared record.',
 'The morning journal mentions the {topic}. This passage appears near the middle of its account.',
 'A local historian recorded a visit to the {topic}. The following entry preserves the original order of events.')
BODIES=(
 'The observer paused beside a narrow path and checked the notes already written on the page. A distant bell marked the hour. There was still time to describe the scene',
 'Two visitors waited near the entrance while a third arranged the papers on a wooden table. The weather remained mild. Their discussion returned to the unfinished description',
 'The guide read a short paragraph aloud and then asked the group to inspect the surrounding area. Several people added quiet comments. The next observation concerned the scene',
 'At the end of the visit, the clerk sorted the pages and set aside a clean sheet for the final account. No one had yet left. The record continued with a description',
 'A small group met after breakfast to review the previous day. They compared their notes and corrected a heading. One participant began to describe the view',
 'Before the meeting, the assistant placed a notebook beside the window and opened it to a fresh page. The others gathered nearby. A new entry described the surroundings',
 'The archivist unfolded a sheet of paper and checked its date against the ledger. The entry appeared complete at first glance. A later paragraph described the scene',
 'Near sunset, the visitors returned to the starting point and discussed what they had observed. One person wrote down the main details. The final passage described the place',
 'The report began with a simple heading and a short statement of purpose. Its author then listed the events in order. The middle paragraph described the view',
 'A quiet conversation continued while the assistant gathered the loose pages. Each page carried a different observation from the visit. The next entry described the setting',
 'The editor checked the spelling of a name and moved the papers closer to the lamp. The account followed a clear sequence. Its next sentence described the surroundings',
 'After a short break, the group returned to the table and resumed the discussion. A volunteer read from the notebook. The following passage described the place')
TAIL=(' while another observer carefully recorded each detail in the notebook. '
      'The group remained nearby and spoke about the route they had followed during the morning. '
      'A second account added information about the weather, the light, and the order of the visit. '
      'Everyone waited until the clerk had finished writing the remaining observations on the page.')
SHORT_PROMPTS=(
 'The glossary entry gives the technical term', 'The subject index contains the term',
 'The lecturer wrote the specialized word', 'The research summary names the discipline',
 'The title on the reference card includes', 'The new vocabulary exercise presents',
 'The catalog uses the scientific expression', 'The chapter heading introduces',
 'The printed worksheet asks about', 'The seminar notice mentions',
 'The reference list is filed under', 'The editor retained the technical word')
NUMBER_PROMPTS=(
 'The register gives the count as', 'The invoice records the identifier as',
 'The label prints the quantity as', 'The notebook records the total as',
 'The schedule marks the year as', 'The receipt gives the reference as',
 'The log records the date as', 'The card lists the date as',
 'The header prints the date as', 'The ledger gives the date as',
 'The notice records the date as', 'The register lists the date as')

def long_pair(row,t,f):
    context=INTROS[t].format(topic=TOPICS[f])+'\n\n'
    body=BODIES[t]
    if row=='fenced_code':
        a=context+'```text\n'+body;b=context+'Passage:\n'+body
        return [(a,TAIL+'\n```\nEnd of entry.','inside'),(b,TAIL+'\nEnd of entry.','outside')]
    if row=='latex_list':
        a=context+'\\begin{itemize}\n\\item '+body;b=context+'\\section*{Notes}\n'+body
        return [(a,TAIL+'\n\\end{itemize}\nEnd of entry.','inside'),(b,TAIL+'\nEnd of entry.','outside')]
    raise ValueError(row)

def short_source_pair(row,t,f):
    context=INTROS[t].format(topic=TOPICS[f])+' '+BODIES[t]+'. '
    context+=BODIES[(t+3)%12]+'. The clerk kept the original ordering of the pages and checked the heading before recording the final entry. '
    if row=='word_first_piece':
        prefix=context+SHORT_PROMPTS[t]
        return [(prefix+' '+WORDS[f]+'. The entry ends here.',WORDS[f],'first_piece'),
                (prefix+' '+COMPLETE[f]+'. The entry ends here.',COMPLETE[f],'complete_word')]
    if row=='number_completion':
        value=str(2040+7*t+f) if t<6 else f'2031-{t:02d}-{11+f:02d}'
        prefix=context+NUMBER_PROMPTS[t]
        return [(prefix+' '+value+'. The entry ends here.',value,'next_completes'),
                (prefix+' '+value+'. The entry ends here.',value,'next_does_not_complete')]
    raise ValueError(row)
