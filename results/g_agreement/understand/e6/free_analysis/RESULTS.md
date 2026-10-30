# E6(a) exploratory enacted-structure script check

Prediction: enactment may carry structure that descriptions do not state.

{'feature': 'prose_paren', 'reader': 'olens', 'status': 'EXPLORATORY', 'n': 84, 'auroc': {'auroc': 0.45663265306122447, 'lo': 0.33644416099773244, 'hi': 0.5850340136054422, 'n': 84, 'n_clusters': 6}, 'format_markers': {'NO_SCRIPTED_REFUSAL_MARKER': 168}, 'aggregation': 'average existing samples within item, then AUROC/cluster CI; missing markers neutral0.5'}
{'feature': 'prose_paren', 'reader': 'nla', 'status': 'NO_SEALED_FREE_READOUTS', 'n': 0}
{'feature': 'python_string', 'reader': 'olens', 'status': 'NO_SEALED_FREE_READOUTS', 'n': 0}
{'feature': 'python_string', 'reader': 'nla', 'status': 'NO_SEALED_FREE_READOUTS', 'n': 0}
{'feature': 'python_indent', 'reader': 'olens', 'status': 'NO_SEALED_FREE_READOUTS', 'n': 0}
{'feature': 'python_indent', 'reader': 'nla', 'status': 'NO_SEALED_FREE_READOUTS', 'n': 0}
{'feature': 'list_depth', 'reader': 'olens', 'status': 'NO_SEALED_FREE_READOUTS', 'n': 0}
{'feature': 'list_depth', 'reader': 'nla', 'status': 'NO_SEALED_FREE_READOUTS', 'n': 0}
{'feature': 'table_column', 'reader': 'olens', 'status': 'EXPLORATORY', 'n': 84, 'auroc': {'auroc': 0.4671201814058957, 'lo': 0.3673469387755102, 'hi': 0.5859056122448979, 'n': 84, 'n_clusters': 6}, 'format_markers': {'NO_SCRIPTED_REFUSAL_MARKER': 168}, 'aggregation': 'average existing samples within item, then AUROC/cluster CI; missing markers neutral0.5'}
{'feature': 'table_column', 'reader': 'nla', 'status': 'NO_SEALED_FREE_READOUTS', 'n': 0}

Only sealed priority readouts are used; missing rows are reported. These are surface proxies, not proof of valid continuation.
