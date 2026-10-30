# W12 §100 reader analysis

§149 RUN-BY-INTEGRATOR. Gates and estimators are the unchanged W1 implementation.

| Row | Reader | Layer | True AUROC | Mismatch AUROC | Status |
|---|---|---:|---:|---:|---|
| clause_embedding | probe | 42 | 1.000000 | 0.000000 | DECODABLE |
| clause_embedding | probe | 44 | 1.000000 | 0.000000 | DECODABLE |
| clause_embedding | olens | 44 | 0.223923 | 0.776077 | NOT EVALUABLE |
| clause_embedding | nla | 42 | 0.801020 | 0.198980 | EVALUABLE |
| clause_embedding | jlens | 44 | 0.522676 | 0.477324 | EVALUABLE |
| clause_embedding | logit | 44 | 0.522676 | 0.477324 | EVALUABLE |
| paragraph_index | probe | 42 | 1.000000 | 0.000000 | DECODABLE |
| paragraph_index | probe | 44 | 1.000000 | 0.000000 | DECODABLE |
| paragraph_index | olens | 44 | 0.821429 | 0.178571 | EVALUABLE |
| paragraph_index | nla | 42 | 0.178571 | 0.821429 | NOT EVALUABLE |
| paragraph_index | jlens | 44 | 0.924603 | 0.075397 | EVALUABLE |
| paragraph_index | logit | 44 | 0.926304 | 0.073696 | EVALUABLE |
| paragraph_start | probe | 42 | 1.000000 | 0.000000 | DECODABLE |
| paragraph_start | probe | 44 | 1.000000 | 0.000000 | DECODABLE |
| paragraph_start | olens | 44 | 0.708050 | 0.291950 | EVALUABLE |
| paragraph_start | nla | 42 | 0.261338 | 0.738662 | NOT EVALUABLE |
| paragraph_start | jlens | 44 | 0.896825 | 0.103175 | EVALUABLE |
| paragraph_start | logit | 44 | 0.873016 | 0.126984 | EVALUABLE |
| sentence_position | probe | 42 | 1.000000 | 0.000000 | DECODABLE |
| sentence_position | probe | 44 | 1.000000 | 0.000000 | DECODABLE |
| sentence_position | olens | 44 | 0.846939 | 0.153061 | EVALUABLE |
| sentence_position | nla | 42 | 0.424036 | 0.575964 | EVALUABLE |
| sentence_position | jlens | 44 | 0.763039 | 0.236961 | EVALUABLE |
| sentence_position | logit | 44 | 0.809524 | 0.190476 | EVALUABLE |
| sentence_type | probe | 42 | 1.000000 | 0.000000 | DECODABLE |
| sentence_type | probe | 44 | 1.000000 | 0.000000 | DECODABLE |
| sentence_type | olens | 44 | 0.982426 | 0.017574 | EVALUABLE |
| sentence_type | nla | 42 | 0.998299 | 0.001701 | EVALUABLE |
| sentence_type | jlens | 44 | NA | NA | NOT EVALUABLE |
| sentence_type | logit | 44 | NA | NA | NOT EVALUABLE |
| syntax_role | probe | 42 | 1.000000 | 0.000000 | DECODABLE |
| syntax_role | probe | 44 | 1.000000 | 0.000000 | DECODABLE |
| syntax_role | olens | 44 | 0.578231 | 0.421769 | EVALUABLE |
| syntax_role | nla | 42 | 0.708050 | 0.291950 | EVALUABLE |
| syntax_role | jlens | 44 | 0.446145 | 0.553855 | EVALUABLE |
| syntax_role | logit | 44 | 0.629252 | 0.370748 | EVALUABLE |
