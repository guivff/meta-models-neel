"""E49 row 4: simulate three to five valid handovers; identical paired bags."""
import re
from rows.interface import RowSpec, Item, length_match

SPEC = RowSpec('holder_after_handovers', ('Alex', 'Robin'), 'semantic_state', '.')
PHRASINGS = (('- Alex', '- Robin'),
             ('- Alex holds the tracked object.', '- Robin holds the tracked object.'))
# The registered read position is a neutral period, not an unfinished holder answer.
CONTINUATIONS = None
FILLERS = (('coin', 'key'), ('ring', 'bead'), ('token', 'button'),
           ('marble', 'ring'), ('key', 'token'), ('button', 'coin'), ('bead', 'marble'))
CONTEXTS = (
    'Alex and Robin are packing supplies for a short trip.',
    'Alex and Robin are sorting objects in a quiet room.',
    'Alex and Robin are preparing materials for a workshop.',
    'Alex and Robin are clearing a table after a meeting.',
    'Alex and Robin are checking equipment before a lesson.',
    'Alex and Robin are organizing a display beside a window.',
    'Alex and Robin are arranging props for a rehearsal.',
    'Alex and Robin are tidying a counter after lunch.',
    'Alex and Robin are inspecting a collection on a shelf.',
    'Alex and Robin are getting ready for a practical exercise.',
    'Alex and Robin are putting supplies away in a cabinet.',
    'Alex and Robin are completing a routine inventory together.',
)
EVENT_FORMS = (
    '{sender} hands the {object} to {receiver}.',
    '{sender} passes the {object} to {receiver}.',
    '{sender} gives the {object} to {receiver}.',
    '{receiver} takes the {object} from {sender}.',
    'The {object} goes from {sender} to {receiver}.',
    '{sender} hands over the {object} to {receiver}.',
    'The {object} is passed from {sender} to {receiver}.',
    '{receiver} receives the {object} from {sender}.',
    '{sender} transfers the {object} to {receiver}.',
    '{sender} gives {receiver} the {object}.',
    '{receiver} is handed the {object} by {sender}.',
    'The {object} changes hands from {sender} to {receiver}.',
)
# No holder or object mention in the last two sentences.
CLOSING = 'The room stays quiet for a moment. The clock ticks by the door.'


def generate():
    items = []
    for t, context in enumerate(CONTEXTS):
        for f, (obj, other) in enumerate(FILLERS):
            count = 3 + (t + f) % 3
            for v, value in enumerate(SPEC.values):
                # Reverse the starting possession when parity requires it.
                current = v ^ (count % 2)
                first, second = SPEC.values[current], SPEC.values[1 - current]
                events = []
                for _ in range(count):
                    sender, receiver = SPEC.values[current], SPEC.values[1 - current]
                    events.append(EVENT_FORMS[t].format(sender=sender, object=obj, receiver=receiver))
                    current = 1 - current
                text = (f'{context} The {obj} is the tracked object. '
                        f'{first} holds the {obj}, while {second} holds the {other}. '
                        + ' '.join(events) + ' ' + CLOSING)
                items.append(Item(SPEC.row_id, t, f, v, text, value))
    return items


def check_label(text):
    """Recover possession from the text and reject a transfer by a non-holder."""
    contexts = '|'.join(re.escape(c) for c in CONTEXTS)
    m = re.fullmatch(
        rf'(?:{contexts}) The (?P<object>[a-z]+) is the tracked object\. '
        r'(?P<first>Alex|Robin) holds the (?P=object), while (?P<second>Alex|Robin) holds the (?P<other>[a-z]+)\. '
        r'(?P<events>.+) ' + re.escape(CLOSING), text)
    if m is None or m['first'] == m['second'] or m['object'] == m['other']:
        raise ValueError('invalid initial possession')
    sentences = m['events'].split('. ')
    sentences = [sentence + '.' if not sentence.endswith('.') else sentence for sentence in sentences]
    if not 3 <= len(sentences) <= 5 or ' '.join(sentences) != m['events']:
        raise ValueError('three to five explicit handovers required')
    state = {m['object']: m['first'], m['other']: m['second']}
    for sentence in sentences:
        parsed = []
        for form in EVENT_FORMS:
            pattern = re.escape(form)
            pattern = pattern.replace(re.escape('{sender}'), '(?P<sender>Alex|Robin)')
            pattern = pattern.replace(re.escape('{receiver}'), '(?P<receiver>Alex|Robin)')
            pattern = pattern.replace(re.escape('{object}'), '(?P<object>[a-z]+)')
            event = re.fullmatch(pattern, sentence)
            if event is not None:
                parsed.append(event)
        if len(parsed) != 1:
            raise ValueError('unrecognized or ambiguous transfer')
        e = parsed[0]
        sender, obj, receiver = e['sender'], e['object'], e['receiver']
        if obj not in state or state[obj] != sender or sender == receiver:
            raise ValueError('handover must originate from the current holder')
        state[obj] = receiver
    return state[m['object']]
