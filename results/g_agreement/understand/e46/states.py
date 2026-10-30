"""§157 clarification 1: original-unit states; never move the read position.
A source-bound unfinished word/number ends at its first lexical boundary.
B ends at the next completed word or number in the extension. Partial units
at the end of the current decoded text are not deemed complete.
"""
import re
from check_long import state as long_state
OTHER='__ENDED__'

def state(item,full_text):
    if item['feature'] in ('fenced_code','latex_list'):
        return long_state(item['feature'],full_text)
    prefix=item['text']
    if not full_text.startswith(prefix):raise ValueError('decoded prefix changed')
    added=full_text[len(prefix):]
    if not added:return item['value']
    if item['label']=='A':
        allowed=r'[A-Za-z]' if item['feature']=='word_first_piece' else r'[0-9-]'
        ended=any(not re.fullmatch(allowed,c) for c in added)
    else:
        # A completed lexical word or number/date after the original read position.
        # The right delimiter must be observed; a partial unit carries state forward.
        ended=bool(re.search(r'(?:[A-Za-z]+|[0-9]+(?:-[0-9]+)*)(?=[^A-Za-z0-9-])',added))
    return OTHER if ended else item['value']
