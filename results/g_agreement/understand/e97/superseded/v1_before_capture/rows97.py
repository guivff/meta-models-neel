"""E97 authored properties; source-only definitions, never fitted to reader outcomes."""
import math
import re

# All examples are independent. Only the CURRENT example supplies the target.
TRACKED = {
 'door_lock': ('locked','unlocked','Door starts unlocked. lock; unlock; lock.','Door starts locked. unlock; lock; unlock.'),
 'lamp_power': ('on','off','Lamp starts off. on; off; on.','Lamp starts on. off; on; off.'),
 'account_access': ('granted','revoked','Access starts revoked. grant; revoke; grant.','Access starts granted. revoke; grant; revoke.'),
 'subscription_status': ('active','cancelled','Subscription starts cancelled. activate; cancel; activate.','Subscription starts active. cancel; activate; cancel.'),
 'document_saved': ('saved','unsaved','Document starts saved. edit; save; edit; save.','Document starts unsaved. save; edit; save; edit.'),
 'inventory_empty': ('empty','nonempty','Inventory starts with one coin. remove coin; add coin; remove coin.','Inventory starts with no coin. add coin; remove coin; add coin.'),
 'queue_front': ('red','blue','FIFO queue starts empty. enqueue red; enqueue blue; dequeue; enqueue red; dequeue.','FIFO queue starts empty. enqueue blue; enqueue red; dequeue; enqueue blue; dequeue.'),
 'stack_top': ('red','blue','LIFO stack starts empty. push red; push blue; pop; push red; pop.','LIFO stack starts empty. push blue; push red; pop; push blue; pop.'),
 'temperature_trend': ('warming','cooling','Temperature readings in order: 18, 16, 20.','Temperature readings in order: 20, 22, 18.'),
 'appointment_day': ('Monday','Friday','Appointment starts on Monday. move to Friday; move to Monday.','Appointment starts on Friday. move to Monday; move to Friday.'),
}
BOOK = {
 'json_key_phase': ('key','value','{"code','{"name": "code'),
 'xml_tag_direction': ('opening','closing','<entry','</entry'),
 'markdown_heading_level': ('level two','level four','## Review','#### Review'),
 'url_query_index': ('first parameter','third parameter','https://example.org/?flag','https://example.org/?x=1&y=2&flag'),
 'ipv4_octet': ('second octet','fourth octet','192.7','192.168.1.7'),
 'escape_parity': ('odd','even','\\code','\\\\code'),
 'digit_radix': ('binary','hexadecimal','0b101','0x101'),
 'css_selector_kind': ('ID selector','class selector','#panel ','.panel '),
 'path_absolute': ('absolute','relative','/root/report','./root/report'),
 'number_sign': ('positive','negative','+37','-37'),
}
PLANS = {
 'register_plan': ('formal','casual','Use a formal register.','Use a casual register.'),
 'citation_plan': ('numeric','author-year','Cite references using numbered brackets.','Cite references using author-year parentheses.'),
 'date_layout_plan': ('year-first','day-first','Write dates in year-month-day order.','Write dates in day-month-year order.'),
 'sort_order_plan': ('ascending','descending','Sort names in ascending alphabetical order.','Sort names in descending alphabetical order.'),
 'name_privacy_plan': ('anonymize','retain names','Replace personal names with anonymous identifiers.','Retain personal names with original identifiers.'),
 'spelling_plan': ('American','British','Use American English spelling conventions.','Use British English spelling conventions.'),
 'rounding_plan': ('floor','ceiling','Round each fractional number down toward negative infinity.','Round each fractional number up toward positive infinity.'),
 'voice_plan': ('active','passive','Rewrite the sentence in active voice.','Rewrite the sentence in passive voice.'),
 'translation_style_plan': ('literal','idiomatic','Translate the sentence literally, preserving individual words.','Translate the sentence idiomatically, preserving natural meaning.'),
 'exposition_plan': ('example first','definition first','Present the example before the definition.','Present the definition before the example.'),
}
DECISIONS = {
 'palindrome_decision': ('palindrome','nonpalindrome','the current word reads identically forwards and backwards'),
 'vowel_initial_decision': ('vowel initial','consonant initial','the current word starts with a vowel'),
 'divisibility_decision': ('multiple of three','not a multiple of three','the current integer is divisible by three'),
 'date_leap_decision': ('leap year','common year','the current year is a Gregorian leap year'),
 'word_isogram_decision': ('distinct letters','repeated letters','the current word has no repeated letters'),
 'set_overlap_decision': ('intersecting','disjoint','the two current sets share at least one element'),
 'triangle_type_decision': ('equilateral','scalene','the current triangle has three equal sides'),
 'fraction_reduced_decision': ('reduced','reducible','the current fraction is already in lowest terms'),
 'bit_parity_decision': ('even parity','odd parity','the current bit string contains an even number of ones'),
 'calendar_order_decision': ('chronological','reverse chronological','the two current dates are in chronological order'),
}
CONTEXTS = ['Study note','Practice record','Training example','Reference card','Workshop note','Exercise record',
            'Review sheet','Sample record','Practice card','Lesson note','Tutorial record','Example sheet']
FILLERS = ['amber','cedar','linen','maple','pearl','slate','willow']

def decision_examples(row, i):
    words = {
      'palindrome_decision': (['level','radar','civic','refer','rotor','madam','kayak'],['lever','radio','cider','rebel','rover','maple','karma']),
      'vowel_initial_decision': (['apple','eagle','ivory','olive','uncle','ember','apron'],['maple','cedar','linen','pearl','slate','brick','plant']),
      'word_isogram_decision': (['brick','plant','ghost','crane','flame','sword','quick'],['belle','level','radar','civic','refer','rotor','madam']),
    }
    if row in words: return tuple(x[i % 7] for x in words[row])
    if row == 'divisibility_decision': return str(300+3*i), str(301+3*i)
    if row == 'date_leap_decision': return str(2000+4*i), str(2001+4*i)
    if row == 'set_overlap_decision': return f'{{{i}, {i+1}}} and {{{i+1}, {i+2}}}', f'{{{i}, {i+1}}} and {{{i+2}, {i+3}}}'
    if row == 'triangle_type_decision': return f'{i+5}, {i+5}, {i+5}', f'{i+4}, {i+5}, {i+6}'
    if row == 'fraction_reduced_decision': return f'{2*i+1}/{2*i+2}', f'{4*i+2}/{4*i+4}'
    if row == 'bit_parity_decision': return '0'*i+'1100', '0'*i+'1110'
    if row == 'calendar_order_decision':
        y=2020+i
        return f'{y}-01-12 then {y}-09-12', f'{y}-09-12 then {y}-01-12'
    raise KeyError(row)

def check(row, text):
    """Independent parser of the CURRENT fragment; returns A or B, not its stored label."""
    s=text.split('CURRENT example:\n',1)[1].split('\nRecord complete.',1)[0].split('\nReply:',1)[0].split('\nTask:',1)[0]
    if row in TRACKED:
        if row == 'door_lock': a = s.rstrip('.').split('; ')[-1] == 'lock'
        elif row == 'lamp_power': a = s.rstrip('.').split('; ')[-1] == 'on'
        elif row == 'account_access': a = s.rstrip('.').split('; ')[-1] == 'grant'
        elif row == 'subscription_status': a = s.rstrip('.').split('; ')[-1] == 'activate'
        elif row == 'document_saved': a = s.rstrip('.').split('; ')[-1] == 'save'
        elif row == 'inventory_empty':
            n=1 if 'one coin' in s else 0
            for act in s.split('. ',1)[1].rstrip('.').split('; '): n += 1 if act=='add coin' else -1
            assert n in (0,1); a=n==0
        elif row in ('queue_front','stack_top'):
            state=[]
            for act in s.split('. ',1)[1].rstrip('.').split('; '):
                if act.startswith(('enqueue ', 'push ')): state.append(act.split()[-1])
                elif act=='dequeue': state.pop(0)
                else: state.pop()
            a=state[0 if row=='queue_front' else -1]=='red'
        elif row == 'temperature_trend':
            nums=list(map(int,re.findall(r'\d+',s))); a=nums[-1]>nums[-2]
        else: a=s.endswith('Monday.')
    elif row in BOOK:
        if row=='json_key_phase': a=':' not in s
        elif row=='xml_tag_direction': a=not s.startswith('</')
        elif row=='markdown_heading_level': a=len(s.split()[0])==2
        elif row=='url_query_index': a=s.count('&')==0
        elif row=='ipv4_octet': a=s.count('.')==1
        elif row=='escape_parity': a=(len(s)-len(s.lstrip('\\')))%2==1
        elif row=='digit_radix': a=s.startswith('0b')
        elif row=='css_selector_kind': a=s.startswith('#')
        elif row=='path_absolute': a=s.startswith('/')
        else: a=s.startswith('+')
    elif row in PLANS:
        # Exact instruction parser; this is a construction check, not a reader scorer.
        assert s in PLANS[row][2:]; a=s==PLANS[row][2]
    else:
        if row=='palindrome_decision': a=s==s[::-1]
        elif row=='vowel_initial_decision': a=s[0] in 'aeiou'
        elif row=='word_isogram_decision': a=len(set(s))==len(s)
        elif row=='divisibility_decision': a=int(s)%3==0
        elif row=='date_leap_decision':
            y=int(s); a=y%4==0 and (y%100!=0 or y%400==0)
        elif row=='set_overlap_decision':
            left,right=s.split(' and '); a=bool(set(re.findall(r'\d+',left)) & set(re.findall(r'\d+',right)))
        elif row=='triangle_type_decision': a=len(set(s.split(', ')))==1
        elif row=='fraction_reduced_decision': a=math.gcd(*map(int,s.split('/')))==1
        elif row=='bit_parity_decision': a=s.count('1')%2==0
        else:
            l,r=s.split(' then '); a=l<r
    return 'A' if a else 'B'

def specifications():
    result=[]
    for family,bank in [('tracked_state',TRACKED),('bookkeeping',BOOK),('plan',PLANS),('decision_ladder',DECISIONS)]:
        for row,v in bank.items():
            result.append(dict(row=row,family=family,values={'A':v[0],'B':v[1]},
                definition=f'{row}: {v[0]} versus {v[1]} in the CURRENT independent example.',
                value_regex={label:r'(?i)(?<!\w)'+re.escape(value)+r'(?!\w)' for label,value in zip('AB',v[:2])},
                read_rule='Final prefix token; the CURRENT example alone determines the target.',
                decision_condition=v[2] if family=='decision_ladder' else None))
    for spec in result:
        if spec['row']=='lamp_power':
            spec['value_regex']={label:r'(?i)\blamp\b[^.!?\n]{0,40}\b'+value+r'\b' for label,value in spec['values'].items()}
        if spec['row']=='json_key_phase':
            spec['value_regex']={label:r'(?i)\b(?:json\s+'+value+'|'+value+r'\s+(?:string|position|field|slot))\b' for label,value in spec['values'].items()}
    return result

def render(row,t,f,label):
    family=next(s['family'] for s in specifications() if s['row']==row)
    bank=next(b for b in (TRACKED,BOOK,PLANS,DECISIONS) if row in b)
    pair=decision_examples(row,f) if family=='decision_ladder' else bank[row][2:]
    current,earlier=pair if label=='A' else pair[::-1]
    head=f'{CONTEXTS[t]} {FILLERS[f]}. The examples are independent; use only the CURRENT example.\n'
    if family=='decision_ladder':
        head=f"If {bank[row][2]}, reply 'alpha'; otherwise reply 'beta'.\n"+head
    text=head+'EARLIER example:\n'+earlier+'\nCURRENT example:\n'+current
    if family=='tracked_state': text+='\nRecord complete.'
    if family=='plan': text+='\nTask: Explain the sample record, following the current instruction.\nAnswer:'
    if family=='decision_ladder': text+='\nReply:'
    assert check(row,text)==label
    return text
