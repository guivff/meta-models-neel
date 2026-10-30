"""§210 clarification 2: exact current-citation digit; never infer it from A/B alone."""
import json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent

def render_dev(item):
    if item.get('split')!='dev' or item.get('feature')!='page_range_digit':
        raise ValueError('Only frozen page_range_digit dev items may supply training targets')
    match=re.search(r'Current citation: pp\. ([1-9])[0-9]{2}–$',item['text'])
    if not match:raise ValueError('Expected frozen current-citation read boundary')
    d=int(match[1]);family='A' if d in (1,2,3,4) else 'B' if d in (6,7,8,9) else None
    if family is None or item.get('value')!=family:raise ValueError('Actual hundreds digit disagrees with frozen family')
    templates=json.loads((HERE/'PAGE_RANGE_TEMPLATES.json').read_text())['templates_by_family'][family]
    return [s.format(d=d) for s in templates]
