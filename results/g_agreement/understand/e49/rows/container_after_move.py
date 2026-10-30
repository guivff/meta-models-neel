"""E49 row 3: order-sensitive location tracking, no outcome-dependent generation."""
import re
from rows.interface import RowSpec, Item, length_match

SPEC = RowSpec('container_after_move', ('cup', 'bowl'), 'semantic_state', ' the')
PHRASINGS = (('- in the cup', '- in the bowl'),
             ('- The tracked object is in the cup.', '- The tracked object is in the bowl.'))
CONTINUATIONS = ((' cup', ' bowl'), (' cup now.', ' bowl now.'))
FILLERS = (('coin', 'bead'), ('key', 'ring'), ('token', 'button'),
           ('marble', 'coin'), ('ring', 'token'), ('button', 'key'), ('bead', 'marble'))
CONTEXTS = (
    'A sorting session is taking place beside the window.',
    'A packing exercise is underway at the kitchen counter.',
    'A small display is being arranged for the afternoon.',
    'A storage check is taking place on a wooden bench.',
    'A desk is being cleared before the next activity.',
    'A set of props is being prepared for a demonstration.',
    'A collection is being organized in the meeting room.',
    'A practical lesson is underway at the work table.',
    'A shelf inventory is being completed before lunch.',
    'A workspace is being tidied after the morning session.',
    'A tray of small objects is being arranged for inspection.',
    'A simple placement task is underway near the doorway.',
)
EVENT_FORMS = (
    '{actor} puts the {object} in the {place}.',
    '{actor} places the {object} inside the {place}.',
    '{actor} sets the {object} in the {place}.',
    '{actor} positions the {object} inside the {place}.',
    '{actor} puts the {object} into the {place}.',
    '{actor} places the {object} in the {place}.',
    'The {object} is put in the {place} by {actor}.',
    '{actor} leaves the {object} inside the {place}.',
    'The {object} is placed inside the {place} by {actor}.',
    '{actor} sets the {object} inside the {place}.',
    'The {object} is set in the {place} by {actor}.',
    '{actor} positions the {object} in the {place}.',
)
ACTORS = ('Sam', 'Lee', 'Drew')
CLOSING = 'The light remains steady throughout the activity.'


def generate():
    items = []
    for t, context in enumerate(CONTEXTS):
        for f, (obj, other) in enumerate(FILLERS):
            for v, value in enumerate(SPEC.values):
                # Both variants contain exactly the same two placement sentences.
                # Putting an object where it already is is a valid non-moving edit.
                locations = ('bowl', 'cup') if value == 'cup' else ('cup', 'bowl')
                actor = ACTORS[t % 3]
                events = ' '.join(EVENT_FORMS[t].format(actor=actor, object=obj, place=place) for place in locations)
                text = (f'{context} The {obj} is the tracked object. '
                        f'The {obj} starts in the cup, and the {other} starts in the bowl. '
                        f'{events} {CLOSING} Now the {obj} is in the')
                items.append(Item(SPEC.row_id, t, f, v, text, value))
    return items


def check_label(text):
    """Parse the complete raw story and execute placements; never read metadata."""
    contexts = '|'.join(re.escape(c) for c in CONTEXTS)
    match = re.fullmatch(
        rf'(?:{contexts}) The (?P<object>[a-z]+) is the tracked object\. '
        r'The (?P=object) starts in the cup, and the (?P<other>[a-z]+) starts in the bowl\. '
        r'(?P<events>.+) ' + re.escape(CLOSING) + r' Now the (?P=object) is in the', text)
    if match is None or match['object'] == match['other']:
        raise ValueError('invalid or ambiguous container story')
    sentences = match['events'].split('. ')
    sentences = [sentence + '.' if not sentence.endswith('.') else sentence for sentence in sentences]
    if len(sentences) != 2 or ' '.join(sentences) != match['events']:
        raise ValueError('exactly two explicit placements required')
    state = {match['object']: 'cup', match['other']: 'bowl'}
    for sentence in sentences:
        parsed = []
        for form in EVENT_FORMS:
            pattern = re.escape(form)
            pattern = pattern.replace(re.escape('{actor}'), '(?P<actor>Sam|Lee|Drew)')
            pattern = pattern.replace(re.escape('{object}'), '(?P<object>[a-z]+)')
            pattern = pattern.replace(re.escape('{place}'), '(?P<place>cup|bowl)')
            event = re.fullmatch(pattern, sentence)
            if event is not None:
                parsed.append(event)
        if len(parsed) != 1:
            raise ValueError('unrecognized or ambiguous placement')
        obj, location = parsed[0]['object'], parsed[0]['place']
        if obj not in state:
            raise ValueError('placement of an undeclared object')
        state[obj] = location
    return state[match['object']]
