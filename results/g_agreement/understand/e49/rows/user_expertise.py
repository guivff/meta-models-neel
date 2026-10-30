"""E49 row 12: authored expert/novice register, exactly matched topic phrases."""
import re
from rows.interface import RowSpec, Item, length_match

SPEC = RowSpec('user_expertise', ('expert', 'novice'), 'descriptor', '.')
PHRASINGS = (('- an expert user', '- a novice user'),
             ('- The user writes with expert familiarity.', '- The user writes with novice familiarity.'))
CONTINUATIONS = None
TOPICS = ('database backups', 'camera exposure', 'garden irrigation', 'audio recording',
          'network routing', 'bread fermentation', 'spreadsheet formulas')
# The claimed construct is linguistic register, not independently verified skill.
# Both alternatives address exactly the same topic; only experience/help framing differs.
REGISTERS = (
    ('I routinely handle this work and want to examine the less obvious trade-offs.',
     'I recently began this work and need to understand the most basic first steps.'),
    ('I have extensive practical experience and can evaluate the finer points without introductory guidance.',
     'I have very little practical experience and need a basic explanation with introductory guidance.'),
    ('I already understand the standard approach and want to discuss the unusual edge cases.',
     'I do not understand the standard approach and want to learn the usual first steps.'),
    ('I regularly advise others on this work and can follow a detailed technical discussion.',
     'I regularly ask others about this work and need a simple introductory explanation first.'),
    ('I can assess the standard methods independently and would like a discussion of subtle limitations.',
     'I cannot use the standard methods independently and would like an explanation of basic concepts.'),
    ('I have used these techniques for years and want to compare their less familiar limitations.',
     'I have used these techniques very little and want to understand their most basic purpose.'),
    ('I am comfortable reviewing advanced choices and would appreciate a precise discussion of the trade-offs.',
     'I am unfamiliar with even basic choices and would appreciate a clear explanation of the essentials.'),
    ('I usually solve these problems independently and now want to examine the difficult boundary cases.',
     'I usually need help with these problems and now want to learn the simplest starting procedure.'),
    ('I have substantial hands-on experience and am looking for a rigorous comparison of alternative methods.',
     'I have minimal hands-on experience and am looking for a straightforward introduction to ordinary methods.'),
    ('I can explain the underlying principles and want to investigate the subtler practical constraints.',
     'I cannot explain the underlying principles and want to understand the basic practical instructions.'),
    ('I routinely review detailed work in this area and want to challenge the standard assumptions.',
     'I am still learning about this area and want to understand the most elementary assumptions.'),
    ('I know how to apply the established methods and want to analyze their exceptional failure modes.',
     'I need help applying the established methods and want to learn their ordinary uses step by step.'),
)
CLOSING = 'I would like to discuss this topic.'


def generate():
    items = []
    for t, pair in enumerate(REGISTERS):
        for f, topic in enumerate(TOPICS):
            for v, register in enumerate(pair):
                text = f'My question concerns {topic}. {register} {CLOSING}'
                items.append(Item(SPEC.row_id, t, f, v, text, SPEC.values[v]))
    return items


def check_label(text):
    """Recognize one unambiguous authored register assertion in the raw text.

    This checks the stated language register; it does not certify a real user's skill.
    It consumes no Item metadata, expected label, family number or split.
    """
    topics = '|'.join(re.escape(topic) for topic in TOPICS)
    m = re.fullmatch(rf'My question concerns (?:{topics})\. (?P<register>.+) ' + re.escape(CLOSING), text)
    if m is None:
        raise ValueError('unknown topic or malformed first-person message')
    expert = {pair[0] for pair in REGISTERS}
    novice = {pair[1] for pair in REGISTERS}
    if expert & novice:
        raise ValueError('ambiguous authored register grammar')
    if m['register'] in expert:
        return 'expert'
    if m['register'] in novice:
        return 'novice'
    raise ValueError('unknown or contradictory register assertion')
