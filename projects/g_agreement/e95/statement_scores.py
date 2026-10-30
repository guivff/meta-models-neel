"""Keep unscorable E95 rows listed and outside S_max/H-M1 denominators."""


def annotate_map(rows, eligibility):
    by_key = {(x['bank'].lower(), x['row']): x for x in eligibility['rows']}
    if len(by_key) != len(eligibility['rows']):
        raise ValueError('duplicate eligibility entry')
    result = []
    for record in rows:
        key = (record['bank'].lower(), record['row'])
        if key not in by_key:
            raise ValueError('statement-score eligibility must be explicit')
        output = dict(record)
        entry = by_key[key]
        output['statement_score_registered'] = entry['statement_score_registered']
        if entry['statement_score_registered'] is False:
            output['map_status'] = 'NOT EVALUABLE (no statement score)'
            output['H_M1_include'] = False
            for field in ('S_layer', 'S_placebo', 'S_max', 'S_max_minus_placebo'):
                output[field] = None
        elif entry['statement_score_registered'] is True:
            output['H_M1_include'] = True
        else:
            raise ValueError('eligibility must be a boolean, never inferred')
        result.append(output)
    return result


def hm1_score_rows(annotated):
    return [x for x in annotated if x['H_M1_include']]
