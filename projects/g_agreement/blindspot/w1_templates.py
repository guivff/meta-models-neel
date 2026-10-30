"""Twelve authored template families per W1 row; never imported from pilot code.

A family changes the feature-bearing sentence/program/table, not merely an archive
header or a sampled noun. Siblings of one family are always held out together.
"""
from __future__ import annotations
import hashlib
import json

TEMPLATE_COUNT = 12

# Distinct grammatical constructions, shared only within a held-out family.
PROSE = (
    'Before dawn the {word} caretaker checked each door and then carried the small wooden box through the courtyard while the delivery crew waited near the gate for instructions about the next journey across the hills beyond the town and the railway station',
    'Although the route beside the {word} was unfamiliar to the visitors they followed the signs until a patient guide explained how the old path connected several farms with the market and why the bridge remained open throughout the long winter season every year',
    'At the {word} workshop a ledger recorded the arrival of each parcel along with its weight and destination so that anyone collecting an order could verify the details before leaving the building and returning to the narrow road that ran behind the bakery',
    'Nobody in the {word} district remembered who had planted the trees but the residents still gathered beneath their branches whenever the annual festival brought musicians and neighbours together to exchange stories about the changing weather and the ordinary events of the previous year',
    'The inspection of the {word} reservoir began after lunch when two technicians lowered their instruments into the water and recorded a sequence of readings that would later be compared with measurements from the earlier survey conducted during the spring before the heavy rains',
    'What the {word} librarian noticed first was a faded inscription on the cover of a notebook which had been left among several maps and which seemed to describe a journey through villages that no longer appeared on the modern road atlas kept upstairs',
    'Having repaired the {word} fence the gardener packed the remaining tools into a canvas bag and paused to watch a pair of birds settle on the roof of the shed where spare boards and several unused pots had remained since the previous summer',
    'There were three reasons for postponing the {word} excursion and the organiser explained each of them carefully before suggesting a different date on which the group could visit the museum and take a short walk through the nearby park without rushing home afterwards',
    'If the {word} shuttle arrived before noon the passengers would have enough time to leave their luggage at the hotel and find the exhibition hall where a volunteer was preparing a display of photographs taken during the reconstruction of the old harbour district',
    'Beyond the {word} station stood a modest cafe whose owner had kept the same opening hours for many years and whose handwritten menu usually included soup bread and a simple dessert made with whatever fruit the neighbouring orchard supplied during that particular week',
    'Rather than replace the {word} clock the mechanic took its movement apart and arranged the pieces across a clean sheet of paper so that the apprentice could see how each small wheel helped transfer motion from the spring to the hands above the dial',
    'Whether the {word} archive should open on Sundays was discussed at a meeting where several residents described their work schedules and a teacher proposed a trial period during which the staff could record visitor numbers and compare them with attendance on ordinary weekdays',
)
PARENS = (
    ('The conservator recorded the {word} pigment ', 'a mixture prepared in the northern studio', 'before checking the second catalogue entry'),
    ('A courier reached the {word} depot ', 'which reopened after the winter repairs', 'while the loading crew reviewed the schedule'),
    ('Our survey includes the {word} footpath ', 'the route marked with blue ceramic tiles', 'near the abandoned station and its platform'),
    ('The committee retained the {word} proposal ', 'submitted jointly by two neighbouring villages', 'pending a review of the estimated expenditure'),
    ('An observer photographed the {word} instrument ', 'borrowed from the university teaching collection', 'beside the calibration chart on the desk'),
    ('Several volunteers restored the {word} sign ', 'originally carved from a single oak plank', 'using materials supplied by the local workshop'),
    ('Records identify the {word} crossing ', 'where merchants once paid a small toll', 'as the entrance to the older settlement'),
    ('The guide described the {word} chamber ', 'accessible only through the eastern passage', 'during the final part of the tour'),
    ('We measured the {word} specimen ', 'collected during the autumn field expedition', 'against the reference scale in the laboratory'),
    ('The editor annotated the {word} manuscript ', 'whose first pages had suffered water damage', 'with observations about the sequence of events'),
    ('A technician replaced the {word} fitting ', 'recommended in the revised maintenance handbook', 'after inspecting the connections along the wall'),
    ('The programme lists the {word} recital ', 'rescheduled following the closure of the hall', 'among the events planned for the coming month'),
)
CODE = (
    ('def collect_{word}(values):\n', 'total = sum(values)', 'return total'),
    ('def examine_{word}(record, default=None):\n', 'result = record.get("entry", default)', 'return result'),
    ('def prepare_{word}(*values):\n', 'ordered = sorted(values)', 'return ordered'),
    ('def render_{word}(value: str) -> str:\n', 'result = value.strip()', 'return result'),
    ('def tally_{word}(values, *, offset=0):\n', 'count = len(values) + offset', 'return count'),
    ('async def receive_{word}(queue):\n', 'item = await queue.get()', 'return item'),
    ('def double_{word}(value=1):\n', 'scaled = value * 2', 'yield scaled'),
    ('def compare_{word}(left, right, /):\n', 'same = left == right', 'return same'),
    ('def merge_{word}(mapping, **entries):\n', 'result = dict(mapping, **entries)', 'return result'),
    ('def inspect_{word}(values):\n', 'first, *rest = values', 'return first'),
    ('def divide_{word}(value, divisor):\n', 'quotient, remainder = divmod(value, divisor)', 'return remainder'),
    ('def label_{word}(value):\n', 'match = value is not None', 'return match'),
)
EXPRESSIONS = (
    'payload = {expr}', 'return_value: object = {expr}', 'def package():\n    return {expr}',
    'if ready:\n    candidate = {expr}', 'for record in records:\n    candidate = {expr}',
    'def stream():\n    yield {expr}', 'try:\n    candidate = {expr}',
    'with resource:\n    candidate = {expr}', 'while pending:\n    candidate = {expr}',
    'class Container:\n    payload = {expr}', 'async def package():\n    return {expr}',
    'match mode:\n    case "active":\n        candidate = {expr}',
)
JSON_PREFIXES = (
    '', '[', '[null, ', '[true, false, ', '[[], ', '[{"archive": 0}, ',
    '["record", ', '[0, 1, ', '[[', '[{}, [], ', '[{"closed": [1, 2]}, ', '[[null], ',
)
TABLES = (
    ('Specimen Batch Assay Vessel Rack Shelf Cabinet Facility', 'amber basalt cedar dune elm fern granite hazel'),
    ('Episode Season Scene Take Reel Camera Studio Archive', 'intro spring forest alpha bronze river cedar ledger'),
    ('Parcel Route Segment Depot Carrier Container Seal Dispatch', 'crate coast north annex wagon timber ribbon morning'),
    ('Instrument Range Scale Unit Sensor Circuit Panel Enclosure', 'meter narrow linear volt probe bridge dial shell'),
    ('Recipe Ingredient Measure Stage Utensil Oven Setting Course', 'stew lentil spoon simmer pan hearth gentle supper'),
    ('Score Movement Bar Motif Voice Clef Tempo Dynamics', 'suite overture ninth echo alto treble lento soft'),
    ('Exhibit Medium Period Origin Acquisition Gallery Case Label', 'bowl ceramic early hill gift atrium glass ochre'),
    ('Trial Protocol Dose Interval Cohort Sample Outcome Review', 'pilot standard mild weekly amber plasma stable interim'),
    ('Plant Genus Variety Plot Soil Water Light Harvest', 'fern pteris silver west loam mist shade autumn'),
    ('Cargo Berth Draft Tonnage Hold Crate Customs Arrival', 'grain quay shallow small aft oak cleared dawn'),
    ('Book Volume Chapter Passage Edition Printer Binding Folio', 'atlas second rivers north revised press cloth twelve'),
    ('Fabric Weave Fibre Dye Pattern Width Finish Roll', 'linen plain flax indigo stripe narrow smooth spool'),
)
# Explicit semantic alternatives: each pair is an independently authored sentence.
SEMANTIC = {
 'prose_topic': (
  ('Seeds were pressed into moist compost before the seedlings were transplanted','The tide exposed a coral shelf beneath the anchored research vessel'),
  ('Pruning the fruit trees encouraged new shoots in the orchard','Waves rocked the buoy beyond the channel entrance'),
  ('A layer of mulch kept the vegetable beds from drying out','The crew charted the currents around the offshore reef'),
  ('The gardener tied the climbing beans to tall bamboo canes','Divers followed a school of fish into the deep blue water'),
  ('We divided the perennial roots and replanted them beside the greenhouse','Salt spray reached the deck as the ship crossed the strait'),
  ('The rose bushes needed watering after several days of warm weather','The trawler returned from the fishing grounds before the storm'),
  ('Rows of lettuce grew beneath the protective mesh in the allotment','The sonar revealed a ridge on the seabed below the vessel'),
  ('A trowel loosened the soil around each newly planted bulb','Low tide left shallow pools among the coastal rocks'),
  ('Bees visited the flowering herbs beside the raised garden beds','A marine survey mapped the distribution of kelp along the coast'),
  ('The compost heap supplied nutrients for the autumn planting','The ferry travelled across rough water between the islands'),
  ('Cuttings developed roots in small pots along the greenhouse bench','Ocean swells lifted the rescue boat near the harbour wall'),
  ('The hedge was trimmed before the annual display of summer flowers','The research team measured salinity in the open sea'),
 ),
 'prose_sentiment': (
  ('The discovery filled us with joy and renewed confidence','The discovery left us deeply disappointed and worried'),
  ('Everyone welcomed the wonderful result with warm applause','Everyone deplored the dreadful result with bitter complaints'),
  ('I am delighted that this thoughtful plan succeeded','I am dismayed that this careless plan failed'),
  ('What a pleasant surprise and a truly lovely afternoon','What an awful surprise and a thoroughly miserable afternoon'),
  ('Their kindness made the visit enjoyable and reassuring','Their hostility made the visit unpleasant and distressing'),
  ('The performance was excellent and we admired every moment','The performance was terrible and we regretted every moment'),
  ('She spoke fondly of a rewarding and cheerful experience','She spoke bitterly of a frustrating and painful experience'),
  ('We felt grateful for the generous help and encouraging news','We felt resentful about the unfair treatment and discouraging news'),
  ('It was a beautiful occasion that brought genuine happiness','It was a bleak occasion that brought profound sadness'),
  ('This improvement is promising and gives me real hope','This deterioration is alarming and leaves me in despair'),
  ('I loved the delightful atmosphere and friendly reception','I hated the oppressive atmosphere and hostile reception'),
  ('Their remarkable achievement deserves enthusiastic praise','Their appalling mistake deserves severe criticism'),
 ),
 'latex_subject': (
  ('Let $G$ be a group with a normal subgroup $N$','Let $ABC$ be a triangle with a perpendicular bisector'),
  ('Every ideal of the ring $R$ is generated by one element','Every chord of the circle meets the tangent at an angle'),
  ('The homomorphism preserves the group operation','The rotation preserves the distance between two points'),
  ('We compute the kernel of the linear transformation','We compute the area enclosed by the quadrilateral'),
  ('The polynomial factors into irreducible elements','The polygon decomposes into congruent triangles'),
  ('Consider a basis for the vector space over the field','Consider the altitude of the isosceles triangle'),
  ('The quotient ring inherits multiplication from its representatives','The inscribed angle subtends the same arc as the central angle'),
  ('A module homomorphism induces a map on the quotient','A reflection maps the line onto a parallel line'),
  ('The determinant vanishes when the matrix is singular','The volume vanishes when the tetrahedron is coplanar'),
  ('Associativity holds for this binary operation','Parallelism holds for these two opposite sides'),
  ('The automorphism fixes every element of the centre','The symmetry fixes every point on the axis'),
  ('A finite field has a cyclic multiplicative group','A regular hexagon has six equal interior angles'),
 ),
 'list_priority': (
  ('Immediately isolate the leaking gas supply','Eventually review the office stationery catalogue'),
  ('Critical: restore power to the emergency equipment now','Routine: update the list of meeting rooms'),
  ('Urgently repair the burst pipe before the room floods','When convenient tidy the shared bookshelf'),
  ('Act at once to secure the unstable scaffolding','At the next review reorganise the reference notes'),
  ('Emergency: contact the fire crew without delay','Low priority: choose a colour for the noticeboard'),
  ('Time critical: deliver the missing medicine immediately','Standard task: archive the monthly newsletters'),
  ('Resolve the production outage before any other task','Complete the annual desk inventory when time permits'),
  ('Highest priority: stop the active water leak','Optional housekeeping: sort the spare folders'),
  ('Respond now to the alarm in the server room','Review the lunch menu during the next planning cycle'),
  ('Safety deadline: replace the damaged cable today','No deadline: refresh the old training examples'),
  ('Escalate the severe equipment fault immediately','Schedule a routine check of the decorative lighting'),
  ('Urgent action required to prevent further damage','Ordinary maintenance can wait until next month'),
 ),
 'list_topic': (
  ('Reserve seats on the overnight train','Revise the chapter on differential equations'),
  ('Compare hotels near the arrival terminal','Complete the exercises from the lecture notes'),
  ('Pack a suitcase for the island journey','Summarise the assigned textbook reading'),
  ('Check the ferry timetable and boarding gate','Practise the vocabulary for the language examination'),
  ('Book a guided walk through the old city','Prepare flashcards covering the key definitions'),
  ('Renew the passport before buying flight tickets','Review the proof of the central theorem'),
  ('Arrange transport from the airport to the accommodation','Solve the practice problems before the tutorial'),
  ('Choose a route through the mountain villages','Outline the argument for the course essay'),
  ('Confirm the baggage allowance for the connecting flight','Organise the sources for the literature review'),
  ('Download a map of the destination and its railway network','Attend the revision session before the final assessment'),
  ('Purchase travel insurance for the overseas trip','Memorise the formulae used in the laboratory course'),
  ('Plan the itinerary around the museum opening hours','Read the recommended paper and annotate its methods'),
 ),
}


# Abstract mathematical statements versus actual worked calculations. Both sides
# use the same neutral LaTeX wrapper: the row is semantic, not an environment tag.
ROLE_PAIRS = (
    (r'If $G$ is abelian, every subgroup $H$ of $G$ is normal because $gH=Hg$ for each $g\in G$.',
     r'In $\mathbb Z/6\mathbb Z$, take $H=\{0,3\}$. Then $1+H=\{1,4\}=H+1$, by adding $1$ to each member.'),
    (r'For integers $a,b$, the sum of the ideals $(a)$ and $(b)$ is the principal ideal generated by $\gcd(a,b)$.',
     r'For $(6)+(10)$, Euclidean division gives $10=6+4$ and $6=4+2$. Thus $\gcd(6,10)=2$ and $(6)+(10)=(2)$.'),
    (r'The kernel of a linear map between vector spaces is a vector subspace of its domain.',
     r'For $T(x,y)=(x,0)$, solving $T(x,y)=(0,0)$ gives $x=0$. Hence $\ker T=\{(0,y):y\in\mathbb R\}$.'),
    (r'The determinant of a two by two matrix with rows $(a,b)$ and $(c,d)$ equals $ad-bc$.',
     r'For the matrix with rows $(2,1)$ and $(3,4)$, the determinant is $2\cdot4-1\cdot3=8-3=5$.'),
    (r'In a commutative ring, the difference of squares factors as $a^2-b^2=(a-b)(a+b)$.',
     r'To factor $9x^2-16$, set $a=3x$ and $b=4$. Substitution gives $9x^2-16=(3x-4)(3x+4)$.'),
    (r'Every vector in a finite dimensional vector space has a unique coordinate expansion in any fixed basis.',
     r'Using $e_1=(1,0)$ and $e_2=(0,1)$, the vector $(3,2)$ equals $3e_1+2e_2=3(1,0)+2(0,1)$.'),
    (r'Addition in the quotient group $\mathbb Z/n\mathbb Z$ is given by $[a]+[b]=[a+b]$.',
     r'In $\mathbb Z/7\mathbb Z$, compute $[5]+[4]=[9]=[2]$, since $9=7+2$.'),
    (r'The order of an element of a finite group divides the number of elements in that group.',
     r'In the additive group $\mathbb Z/12\mathbb Z$, $4+4=8$ and $4+4+4=12=0$. Therefore $4$ has order $3$.'),
    (r'A square matrix over a field is singular if and only if its determinant is zero.',
     r'For the matrix with rows $(1,2)$ and $(2,4)$, the determinant is $1\cdot4-2\cdot2=4-4=0$, so it is singular.'),
    (r'Addition modulo a positive integer is associative, so $([a]+[b])+[c]=[a]+([b]+[c])$.',
     r'Modulo $7$, $(2+4)+5=11=4$, while $2+(4+5)=2+2=4$. Both groupings yield the residue $4$.'),
    (r'Every group automorphism fixes the identity element of the group.',
     r'For the automorphism $f(x)=-x$ of $\mathbb Z/5\mathbb Z$, $f(0)=-0=0$ and $f(2)=-2=3$ modulo $5$.'),
    (r'If $p$ is prime and $a$ is not divisible by $p$, then $a^{p-1}$ is congruent to $1$ modulo $p$.',
     r'With $p=5$ and $a=2$, calculate $2^{5-1}=2^4=16=3\cdot5+1$, giving residue $1$ modulo $5$.'),
)

def table_prefix(t, cols=8, rows=1, header_only=False):
    heads, cells = (s.split() for s in TABLES[t])
    # Twelve distinct schemas, alignment/spacing patterns and numbers of completed rows.
    sep = (' | ', '|', '  |  ')[t % 3]
    edge = '| ' if t % 2 == 0 else '|'
    end = ' |' if t % 2 == 0 else '|'
    def line(values): return edge + sep.join(values) + end
    if header_only: return edge + sep.join(heads[:cols])
    alignment = ('---', ':---', '---:', ':---:')[t % 4]
    text = line(heads[:cols]) + '\n' + line([alignment]*cols) + '\n'
    for k in range(rows):
        shifted = cells[k:] + cells[:k]
        text += line(shifted[:cols]) + '\n'
    return text, edge, sep, cells


def render_body(feature, side, template, variant, word, *, level=None):
    """Render at a raw-prefix final token. side 0 is the positive binary value."""
    t = template
    paragraph = PROSE[t].format(word=word)
    words = paragraph.split()
    head, step, tail = CODE[t]
    head = head.format(word=word)
    low_high = 1 + variant % 2 if side == 0 else 6 + variant % 3
    if feature in ('latex_item', 'list_index') and side == 0:
        low_high = 1  # These rows say FIRST, not early/one-or-two.
    meta = {'local_index': low_high, 'template_family': f'{feature}:t{t:02d}', 'template_index': t,
            'variant': variant, 'kind': 'ordinal' if level is not None else 'binary'}
    if feature == 'prose_sentence':
        b = (paragraph + '. ') * (low_high-1) + ' '.join(words[:9])
    elif feature == 'prose_words': b = word.capitalize()+' notes: '+' '.join(words[:5 if side == 0 else 24])
    elif feature == 'prose_budget':
        count = 18 if side == 0 else 37
        b = f'Write exactly 40 words in the following paragraph.\n\n' + ' '.join(words[:count])
        meta.update(word_limit=40, words_so_far=count, words_remaining=40-count)
    elif feature == 'prose_column': b = paragraph + '.\n' + word.capitalize()+' notes: '+' '.join(words[:5 if side == 0 else 24])
    elif feature == 'prose_paren':
        prefix, aside, suffix = PARENS[t]
        b = prefix.format(word=word) + '(' + aside + ('' if side == 0 else ')') + ' ' + suffix
    elif feature == 'prose_quote':
        prefix, aside, suffix = PARENS[t]
        b = prefix.format(word=word) + '"' + aside + ('' if side == 0 else '"') + ' ' + suffix
    elif feature in SEMANTIC:
        b = word.capitalize() + ' notes: ' + SEMANTIC[feature][t][side]
        if feature.startswith('list_'): b = ('- ', '* ', '+ ')[t % 3] + b
    elif feature == 'python_line': b = head + ('    '+step+'\n')*(low_high-1) + '    ' + tail
    elif feature == 'python_argument':
        call = ('assemble', 'format', 'combine', 'dispatch', 'register', 'zip', 'merge', 'report', 'select', 'package', 'record', 'publish')[t]
        args = '' if side == 0 else 'alpha, beta, gamma, delta, '
        b = EXPRESSIONS[t].format(expr=call+'('+args+word)
    elif feature in ('python_depth', 'python_depth_ordinal'):
        depth = level if level is not None else (1 if side == 0 else 3)
        b = EXPRESSIONS[t].format(expr='['*depth + word)
        meta['level'] = depth
    elif feature == 'python_indent':
        b = head + ('    ' if side == 0 else '    if ready:\n        for item in values:\n            ') + step
        meta['level'] = 1 if side == 0 else 3
    elif feature == 'python_string':
        b = EXPRESSIONS[t].format(expr='"'+word) if side == 0 else EXPRESSIONS[t].format(expr='"stored"')+'\n'+word
    elif feature == 'python_comment': b = ('# ' if side == 0 else '') + step + '  # '+word if side == 0 else step+'\n'+word
    elif feature == 'python_effect':
        mutation = ('values.append(item)', 'values.extend(extra)', 'values.insert(0, item)', 'values.remove(item)', 'values.pop()', 'values.sort()', 'values.reverse()', 'values.clear()', 'values.__iadd__(extra)', 'values.__setitem__(0, item)', 'values.__delitem__(0)', 'values *= 2')[t]
        copy = ('result = values + [item]', 'result = values + extra', 'result = [item] + values', 'result = [x for x in values if x != item]', 'result = values[:-1]', 'result = sorted(values)', 'result = list(reversed(values))', 'result = list()', 'result = list(values) + extra', 'result = [item] + values[1:]', 'result = values[1:]', 'result = values * 2')[t]
        b = head + '    ' + (mutation if side == 0 else copy) + '\n    # '+word
    elif feature == 'python_error':
        context = ('', 'if value is None:\n    ', 'if not ready:\n    ', 'try:\n    ', 'for item in values:\n    ', 'while pending:\n    ', 'with resource:\n    ', 'match value:\n    case None:\n        ', 'if value < 0:\n    ', 'if not values:\n    ', 'if failed:\n    ', 'if expired:\n    ')[t]
        statement = context + ('raise ValueError("'+word+'")' if side == 0 else 'return "'+word+'"')
        b = 'def validate_'+word+'(value):\n'+'\n'.join('    '+line for line in statement.splitlines())
    elif feature == 'latex_section':
        heading = ('Overview', 'Method', 'Setup', 'Motivation', 'Background', 'Construction', 'Definitions', 'Discussion', 'Examples', 'Notation', 'Analysis', 'Remarks')[t]
        b = ''.join('\\section{'+heading+f' {j}'+'}\n'+paragraph+'.\n' for j in range(1,low_high+1))+'Consider the '+word+' statement'
    elif feature == 'latex_item':
        b = '\\begin{enumerate}\n'+('\\item '+paragraph+'\n')*(low_high-1)+'\\item '+ ' '.join(words[:8])
    elif feature == 'latex_math':
        expression = ('x+y', 'a^2+b^2', '\\sum_i x_i', '\\alpha\\beta', '\\int_0^1 f(x)dx', 'u\\cdot v', 'n!', '\\sqrt{x}', 'p\\to q', 'A\\cup B', 'z\\in S', 'x\\leq y')[t]
        b = 'Consider $'+expression+' + '+str(variant+1)+('' if side == 0 else '$ and the '+word+' construction')
    elif feature == 'latex_brace':
        commands = ('textbf', 'emph', 'textit', 'underline', 'textrm', 'textsf', 'texttt', 'mbox', 'fbox', 'textnormal', 'textsc', 'textup')
        b = ''.join('\\'+commands[(t+j)%12]+'{' for j in range(1 if side==0 else 3))+' '.join(words[:8])
        meta['level'] = 1 if side == 0 else 3
    elif feature == 'latex_environment': b = '\\begin{'+('equation' if side==0 else 'quote')+'}\n'+' '.join(words[:10])
    elif feature == 'latex_fraction':
        forms = ('a+b', 'x^2', 'n!', '\\alpha', 'u+v+w', 'p-q', 'r^3', '2x', 'c_d', 'm/n', 'k+1', '\\pi')
        b = 'Let $\\frac{'+forms[t]+'+'+str(variant+1)+('' if side==0 else '}{'+forms[(t+1)%12]+'+'+str(variant+1))
    elif feature == 'latex_role': b = '\\noindent '+word.capitalize()+' case. '+ROLE_PAIRS[t][side]
    elif feature == 'json_field':
        previous = '' if side==0 else '"archive":null,"enabled":true,"batch":[],"version":1,'
        b = JSON_PREFIXES[t]+'{'+previous+'"'+word+'": "sample'
    elif feature == 'json_depth':
        depth = 1 if side==0 else 3
        b = JSON_PREFIXES[t]+''.join('{"'+('branch','record','payload')[(t+j)%3]+'":' for j in range(depth))+'"'+word
        meta['level'] = depth
    elif feature == 'json_type': b = JSON_PREFIXES[t]+'{"'+word+'": '+('"' if side==0 else '')+str(120+variant)
    elif feature == 'json_status': b = JSON_PREFIXES[t]+'{"'+word+'": {"decision": "'+('approved' if side==0 else 'rejected')
    elif feature in ('table_column','table_column_ordinal'):
        column = level if level is not None else (1 if side==0 else 5)
        b, edge, sep, cells = table_prefix(t,rows=t%3)
        b += edge+sep.join(cells[:column-1]+[word]);meta['level']=column
    elif feature == 'table_row':
        b, edge, sep, cells = table_prefix(t,rows=low_high-1)
        b += edge+word;meta['level']=low_high
    elif feature == 'table_role':
        if side == 0: b = table_prefix(t,header_only=True,cols=3)+' '+word
        else:
            b, edge, sep, cells=table_prefix(t,rows=0)
            b += edge+sep.join(cells[:3])+' '+word
    elif feature == 'table_status':
        b, edge, sep, cells=table_prefix(t,rows=t%3)
        # Rename the final schema column before adding the decisive current cell.
        first,rest=b.split('\n',1);heads,cells0=(s.split() for s in TABLES[t]);first=first.replace(heads[-1],'Decision')
        b=first+'\n'+rest+edge+sep.join([word]+cells[1:7]+['approved' if side==0 else 'rejected'])
    elif feature == 'list_index': b = (('- ', '* ', '+ ')[t%3]+' '.join(words[:8])+'\n')*(low_high-1)+('- ', '* ', '+ ')[t%3]+word+': '+' '.join(words[-8:])
    elif feature == 'list_depth':
        mark=('- ', '* ', '+ ')[t%3];depth=1 if side==0 else 3
        b=''.join('  '*j+mark+' '.join(words[j*4:j*4+4])+'\n' for j in range(depth-1))+'  '*(depth-1)+mark+' '.join(words[:10])
        meta['level']=depth
    elif feature == 'list_completed': b = ('- [x] '+' '.join(words[:8])+'\n')*low_high+'- [ ] '+' '.join(words[-8:])
    elif feature == 'list_words': b = ('- ', '* ', '+ ')[t%3]+word+': '+' '.join(words[:5 if side==0 else 24])
    elif feature == 'list_ordered': b = (('1. ' if t%2==0 else '1) ') if side==0 else ('- ', '* ', '+ ')[t%3])+' '.join(words[:10])
    elif feature == 'list_task': b = ('- ', '* ', '+ ')[t%3]+'['+('x' if side==0 else ' ')+'] '+' '.join(words[:10])
    else: raise KeyError(feature)
    return b,meta


def template_signature(feature, template):
    """Hash both literal templates with nuisance word/instance fixed; audit family diversity."""
    texts=[render_body(feature,s,template,0,'ANCHOR')[0] for s in (0,1)]
    return hashlib.sha256(json.dumps(texts,ensure_ascii=False).encode()).hexdigest()
