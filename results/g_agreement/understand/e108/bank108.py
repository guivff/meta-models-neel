"""§219 E108 open-choice prompts. No labels, member lists or model calls."""
import hashlib
CATEGORIES=('sport','animal','colour','country','fruit','musical instrument','city','profession','vegetable','bird','vehicle','number 1–10')
SEED=20261029
SURFACES=('', 'Please help with this task. ', 'Here is a short task. ', 'Consider the following request. ', 'For this exercise, follow this request. ', 'Respond to the task below. ', 'Here is your next task. ')
IMMEDIATE=(
 'Name one {category}:',
 'Give one {category}:',
 'Choose one {category} and name it:',
 'Pick one {category} and give its name:',
 'Select one {category}; state your choice:',
 'Think of one {category} and name your choice:')
DELAYED=(
 'Think of one {category}. Now write one sentence about a day at the park that mentions it. Begin the sentence with "At the park," and then mention your choice:',
 'Choose one {category}. Write one sentence about a day at the park that mentions your choice. Start the sentence with "At the park," before naming it:',
 'Pick one {category}. Now write a sentence about a day at the park and mention it. Open with "At the park," and then include your choice:',
 'Select one {category}. Write one sentence about a day at the park that includes it. Begin with "At the park," before mentioning your choice:',
 'Think of one {category} to mention in a sentence about a day at the park. Write that sentence, starting with "At the park," and then mentioning it:',
 'Choose one {category} for a sentence about a day at the park. Write one sentence, beginning with "At the park," before including your choice:')

def category_text(category):
    return 'number from 1 to 10' if category=='number 1–10' else category

def native_items():
    items=[]
    for ci,category in enumerate(CATEGORIES):
        for ti in range(6):
            for si,lead in enumerate(SURFACES):
                prompt_id=f'c{ci:02d}t{ti}s{si}'
                for arm,templates in [('immediate',IMMEDIATE),('delayed',DELAYED)]:
                    text=lead+templates[ti].format(category=category_text(category))
                    ident=hashlib.sha256(f'E108|{prompt_id}|{arm}'.encode()).hexdigest()[:24]
                    items.append(dict(id=ident,kind='native',category=category,arm=arm,prompt_id=prompt_id,template=ti,surface=si,text=text))
    return items
