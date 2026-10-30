# E29 registered analysis

§149 RUN-BY-INTEGRATOR; owner review pending.

```json
{
  "R3_descriptive_Spearman_D_NLA": 0.3714285714285715,
  "bootstrap": {
    "CI": "95% finite-draw percentile",
    "draws": 2000,
    "seed": 20261025,
    "unit": "paired IID item within row"
  },
  "comparison": "single prospective W12 reader comparison",
  "experiment": "E29",
  "freeze": "2833a20091db5e1e3b5548bf8d0e581b1fe23718989dc9e6e698da6eb767109f",
  "note": "R1 point prediction and registered stronger falsification condition are reported separately. Mechanical per-row predictions remain unchanged. D/P and non-blind companion are already complete and never rerun.",
  "predictions_seal": "ca76c12ce6f1c9ffdf95097b7ac3ce3f62c0cfa9f7519941857bd467ed80f2ba",
  "registered_rules": {
    "R1": {
      "all_structure_Oracle_le065": false,
      "falsifying_rows": [
        "sentence_type",
        "paragraph_index"
      ],
      "registered_falsified": true
    },
    "R2": {
      "high_D_rows": [
        "sentence_type",
        "paragraph_index",
        "clause_embedding"
      ],
      "required": 2,
      "satisfying_rows": [
        "clause_embedding"
      ],
      "status": "NOT_MET"
    }
  },
  "rows": [
    {
      "D": 0.608843537414966,
      "D_minus_Oracle": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          -0.1488778409090909,
          0.20059692221044254
        ],
        "difference": 0.030612244897959218,
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "NLA": 0.7080498866213152,
      "NLA_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.5857917718855219,
          0.8148677854055425
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "Oracle": 0.5782312925170068,
      "Oracle_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.4444444444444444,
          0.7025183359737135
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "P": -4.526408791542053,
      "feature": "syntax_role",
      "mechanical_prediction_checks": {
        "oracle_asked_AUROC_max": true
      }
    },
    {
      "D": 0.9812925170068028,
      "D_minus_Oracle": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          -0.02609300069612746,
          0.02530592427533913
        ],
        "difference": -0.0011337868480725266,
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "NLA": 0.9982993197278912,
      "NLA_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.9928496031011796,
          1.0
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "Oracle": 0.9824263038548753,
      "Oracle_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.9548597206331045,
          1.0
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "P": -5.369820237159729,
      "feature": "sentence_type",
      "mechanical_prediction_checks": {
        "D_minus_oracle_asked_AUROC_min": false,
        "oracle_asked_AUROC_max": false
      }
    },
    {
      "D": 0.00963718820861678,
      "D_minus_Oracle": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          -0.9211602605550769,
          -0.7392002152939653
        ],
        "difference": -0.8373015873015873,
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "NLA": 0.42403628117913833,
      "NLA_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.3010162654805512,
          0.5429530409633664
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "Oracle": 0.8469387755102041,
      "Oracle_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.7482917718855219,
          0.929642441891262
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "P": -4.750970125198364,
      "feature": "sentence_position",
      "mechanical_prediction_checks": {
        "oracle_asked_AUROC_max": false
      }
    },
    {
      "D": 0.7063492063492064,
      "D_minus_Oracle": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          -0.28551186704218734,
          0.055131806850556804
        ],
        "difference": -0.115079365079365,
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "NLA": 0.17857142857142858,
      "NLA_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.09027015019547519,
          0.2772774079467443
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "Oracle": 0.8214285714285714,
      "Oracle_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.7216604036000375,
          0.901044034090909
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "P": -4.9210206270217896,
      "feature": "paragraph_index",
      "mechanical_prediction_checks": {
        "D_minus_oracle_asked_AUROC_min": false,
        "oracle_asked_AUROC_max": false
      }
    },
    {
      "D": 0.6077097505668935,
      "D_minus_Oracle": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          -0.2534740440064284,
          0.05349146747085568
        ],
        "difference": -0.10034013605442171,
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "NLA": 0.2613378684807256,
      "NLA_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.15418083900226756,
          0.379295579787979
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "Oracle": 0.7080498866213152,
      "Oracle_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.5886476692949908,
          0.8159645944571573
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "P": -4.420607507228851,
      "feature": "paragraph_start",
      "mechanical_prediction_checks": {
        "oracle_asked_AUROC_max": false
      }
    },
    {
      "D": 0.7001133786848073,
      "D_minus_Oracle": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.3237095264389147,
          0.6139979663926689
        ],
        "difference": 0.4761904761904762,
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "NLA": 0.8010204081632653,
      "NLA_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.7019832598556003,
          0.8919003234658367
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "Oracle": 0.22392290249433106,
      "Oracle_CI": {
        "attempted_bootstrap_draws": 2000,
        "ci95": [
          0.13295454545454546,
          0.3290130459444128
        ],
        "finite_bootstrap_draws": 2000,
        "undefined_bootstrap_draws": 0
      },
      "P": -5.2358468770980835,
      "feature": "clause_embedding",
      "mechanical_prediction_checks": {
        "D_minus_oracle_asked_AUROC_min": true,
        "oracle_asked_AUROC_max": true
      }
    }
  ],
  "values_seal": "ecac8379a09d429ae42013b2980a0fb927043309f51a84f730b3283430238bf7"
}
```
