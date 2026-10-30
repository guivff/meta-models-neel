**Frozen prediction (§88, original terminology):** Structural rows were predicted to have high fidelity for the arm originally called “enactment” and near-zero description fidelity; semantic rows were predicted high in both arms. The NLA decoder should show the same pattern, more weakly.

**Input-span caveat (2026-10-24; before interpretation):** The arm labelled **“AR on the prefix”** here fed the AR each W1 item's **prefix through and including the read-position token**, not text after that position. All 2,100 sealed inputs equal the W1 item text token-for-token, with `read_position == len(ids) - 1`; the worker passed those strings unchanged to the block-44 AR without truncation. The native-42 decoder received the same prefix strings. The AR is trained on continuation → preceding activation, so this prefix input mismatches that temporal training relation. Low AR fidelity here therefore does not establish that an appropriately aligned continuation cannot reconstruct the read-position activation. E1b is the planned, separately registered continuation-arm follow-up on the E12 pod; it is not part of these sealed E1 results.

**Assessment: the main AR prediction did not hold for the prefix arm actually tested.** AR on the prefix did not rescue structural fidelity: AR median prefix fidelity was 0.0084 for count-like and 0.0243 for state-like rows. AR semantic fidelity was also low in both arms. The native-42 NLA decoder showed a partial directional pattern: prefix fidelity exceeded description on 14/16 structural rows, but structural prefix medians were only 0.0966 and 0.1028. Its semantic prefix median was 0.2544. With the AR input-span caveat above, this does not establish the proposed strong describe-versus-enact dissociation or settle the continuation-arm prediction.

EXPLORATORY. All 25 rows and both decoders are reported; no pass/fail threshold or sign flip was introduced. The registered signed ratios, fixed real class-mean gaps and 2,000-resample CIs are unchanged. AR description reuses sealed S2 outputs; its registered W2/S2 analyses were not invoked.

| Decoder/site | Class | Rows | Median description fidelity | Median prefix fidelity | Prefix > description |
|---|---|---:|---:|---:|---:|
| ar / 44 | count-like | 9 | 0.026496 | 0.008372 | 3/9 |
| ar / 44 | state-like | 7 | 0.008464 | 0.024301 | 5/7 |
| ar / 44 | semantic | 9 | 0.051160 | 0.022380 | 3/9 |
| nla / 42 | count-like | 9 | 0.011099 | 0.096595 | 8/9 |
| nla / 42 | state-like | 7 | 0.003607 | 0.102824 | 6/7 |
| nla / 42 | semantic | 9 | 0.041616 | 0.254354 | 8/9 |

Class medians and ordering counts above are descriptive summaries, without new group-level tests. The per-row table below retains all original CIs. Each prefix cell uses 84 W1 test items; each description cell uses 40 frozen S2 texts.

**DESCRIPTIVE — added after seeing E1 results (2026-10-24).** AUROC of the fixed native probe projection, value A positive, with ties counted as one half. No gap denominator, sign flip or probe refit. Both decoders and both frozen arms are included. These are point estimates; no new AUROC CIs were requested or computed. The original fidelity estimates and assessment are unchanged. High AUROC with low fidelity would indicate preserved ordering with a small projection contrast relative to the real-activation gap; AUROC alone does not validate reconstruction magnitude.

| Row | Class | AR description | AR on the prefix | NLA decoder description | NLA decoder on the prefix |
|---|---|---:|---:|---:|---:|
| json_status | semantic | 0.982500 | 0.996032 | 0.977500 | 1.000000 |
| json_type | state-like | 0.537500 | 0.653628 | 0.550000 | 0.993197 |
| latex_environment | state-like | 0.402500 | 0.849773 | 0.765000 | 0.792517 |
| latex_role | semantic | 0.670000 | 0.888889 | 1.000000 | 1.000000 |
| latex_section | count-like | 0.527500 | 0.003401 | 0.592500 | 1.000000 |
| latex_subject | semantic | 0.362500 | 0.897959 | 0.920000 | 1.000000 |
| list_depth | count-like | 0.565000 | 0.097506 | 0.557500 | 0.833333 |
| list_index | count-like | 0.732500 | 0.505102 | 0.430000 | 0.261905 |
| list_priority | semantic | 0.732500 | 0.484127 | 0.802500 | 1.000000 |
| list_topic | semantic | 0.787500 | 0.986395 | 1.000000 | 1.000000 |
| prose_paren | state-like | 0.247500 | 0.611111 | 0.492500 | 0.717687 |
| prose_quote | state-like | 0.515000 | 0.566893 | 0.507500 | 0.812358 |
| prose_sentence | count-like | 0.485000 | 0.984127 | 0.695000 | 0.566327 |
| prose_sentiment | semantic | 0.960000 | 0.984694 | 1.000000 | 1.000000 |
| prose_topic | semantic | 0.770000 | 0.849206 | 1.000000 | 1.000000 |
| python_argument | count-like | 0.727500 | 0.718254 | 0.812500 | 0.918934 |
| python_comment | state-like | 0.425000 | 0.824830 | 0.975000 | 0.637755 |
| python_depth | count-like | 0.680000 | 0.870748 | 0.445000 | 0.998299 |
| python_error | semantic | 0.762500 | 0.589002 | 0.935000 | 1.000000 |
| python_indent | count-like | 0.680000 | 0.506803 | 0.635000 | 0.967687 |
| python_string | state-like | 0.590000 | 0.872449 | 0.730000 | 0.998299 |
| table_column | count-like | 0.612500 | 0.544218 | 0.787500 | 1.000000 |
| table_role | state-like | 0.595000 | 0.989229 | 0.562500 | 1.000000 |
| table_row | count-like | 0.475000 | 0.792517 | 0.782500 | 1.000000 |
| table_status | semantic | 0.950000 | 0.788549 | 0.997500 | 0.996599 |

Per row: description n = 40 (20 A / 20 B); prefix n = 84 (42 A / 42 B). Full precision, source seals and counts: `projection_auroc/metrics.json`.

The original sealed figure below retains its historical “enactment” legend; that legend denotes prefix input, labelled “AR on the prefix” in this report. The underlying metrics retain the frozen `enactment` key. Neither is a continuation arm.

![Original sealed per-row fidelity figure; enactment legend means prefix](fidelity.png)

| Row | Class | Reader | Arm | Fidelity | 95% CI |
|---|---|---|---|---:|---|
| json_status | semantic | ar | description | 0.05520388243790299 | [0.04438590258895088, 0.06490529963628973] |
| json_status | semantic | ar | AR on the prefix | 0.015570924729034341 | [0.013589734158464328, 0.01754004060331011] |
| json_status | semantic | nla | description | 0.023565042487640207 | [0.01841851531272974, 0.028675881335741882] |
| json_status | semantic | nla | NLA decoder on the prefix | 0.06527049865628688 | [0.06303506846885672, 0.06745576332617709] |
| json_type | state-like | ar | description | 0.008464311730748374 | [-0.03153513615318176, 0.047709832685340514] |
| json_type | state-like | ar | AR on the prefix | 0.005597787600595812 | [0.0008735179880971925, 0.010298514988127571] |
| json_type | state-like | nla | description | 0.0036067658479623974 | [-0.004199130527589155, 0.011685383493690757] |
| json_type | state-like | nla | NLA decoder on the prefix | 0.050721615746181864 | [0.0435620444166326, 0.057888279347496484] |
| latex_environment | state-like | ar | description | -0.1392108361802017 | [-0.3475697927146388, 0.053233378934790125] |
| latex_environment | state-like | ar | AR on the prefix | 0.1598103560612243 | [0.11424014200205483, 0.20524720495148113] |
| latex_environment | state-like | nla | description | 0.07370109533681854 | [0.03259804608830589, 0.11654712425733381] |
| latex_environment | state-like | nla | NLA decoder on the prefix | 0.18745045055143267 | [0.12360486523952455, 0.2535730086513195] |
| latex_role | semantic | ar | description | 0.04783702598822612 | [0.02376551850385001, 0.07451285214351644] |
| latex_role | semantic | ar | AR on the prefix | 0.08263118540249922 | [0.062124746085535414, 0.10165179509329803] |
| latex_role | semantic | nla | description | 0.16703454455299444 | [0.14867041763401573, 0.1849916711275348] |
| latex_role | semantic | nla | NLA decoder on the prefix | 0.34311878395225265 | [0.327222577696346, 0.3582482401439618] |
| latex_section | count-like | ar | description | 0.0032507180580544697 | [-0.07247431012522212, 0.0770695950161178] |
| latex_section | count-like | ar | AR on the prefix | -0.07581950214935713 | [-0.0845989238152945, -0.06683396490588163] |
| latex_section | count-like | nla | description | 0.012610118252292378 | [-0.0061917205730277255, 0.031195802858761126] |
| latex_section | count-like | nla | NLA decoder on the prefix | 0.17143665371090439 | [0.1587305535641855, 0.18372880420184076] |
| latex_subject | semantic | ar | description | -0.04775321157846723 | [-0.0898789322168275, -0.005175056949718094] |
| latex_subject | semantic | ar | AR on the prefix | 0.05964742109691938 | [0.045191063002116956, 0.075142735689203] |
| latex_subject | semantic | nla | description | 0.041616113968434516 | [0.030379495637076568, 0.052970200625796486] |
| latex_subject | semantic | nla | NLA decoder on the prefix | 0.254949814053733 | [0.23575154565693252, 0.2742017843564846] |
| list_depth | count-like | ar | description | 0.041671733525089336 | [-0.013548890052227923, 0.09594911482803302] |
| list_depth | count-like | ar | AR on the prefix | -0.0769596516478158 | [-0.09252845423294112, -0.062006965833894284] |
| list_depth | count-like | nla | description | 0.003575383856218987 | [-0.01351662558117865, 0.020622405367050983] |
| list_depth | count-like | nla | NLA decoder on the prefix | 0.06968970356374965 | [0.047468185382603355, 0.09338876239878698] |
| list_index | count-like | ar | description | 0.07942796951876178 | [0.03580138427994483, 0.12403882702962585] |
| list_index | count-like | ar | AR on the prefix | 0.011654028297521104 | [-0.00896615218593473, 0.034233033138413534] |
| list_index | count-like | nla | description | -0.011368050036190184 | [-0.028417703327034152, 0.005830792076003327] |
| list_index | count-like | nla | NLA decoder on the prefix | -0.03702972814840105 | [-0.05302614233542745, -0.02093272158599204] |
| list_priority | semantic | ar | description | 0.05115996631448752 | [0.01746460371078282, 0.08118110560449274] |
| list_priority | semantic | ar | AR on the prefix | 0.0031270235840354997 | [-0.008978569631802649, 0.01472990981934397] |
| list_priority | semantic | nla | description | 0.025572533221812882 | [0.013787109914063667, 0.03794975473622499] |
| list_priority | semantic | nla | NLA decoder on the prefix | 0.0965486537366905 | [0.08884403635887086, 0.10447143862484946] |
| list_topic | semantic | ar | description | 0.11562629545791205 | [0.05379071163399426, 0.17301172652103317] |
| list_topic | semantic | ar | AR on the prefix | 0.15292551831346274 | [0.12467144477491991, 0.1814081272175026] |
| list_topic | semantic | nla | description | 0.20118241826525443 | [0.1752339699085982, 0.22637566547567756] |
| list_topic | semantic | nla | NLA decoder on the prefix | 0.3666854350310336 | [0.3330311108679542, 0.40339306744068437] |
| prose_paren | state-like | ar | description | -0.12249567237193387 | [-0.2039894962473792, -0.04502879037510197] |
| prose_paren | state-like | ar | AR on the prefix | 0.02201907848661124 | [-0.00396489287475927, 0.04777091350418288] |
| prose_paren | state-like | nla | description | -0.00353773419130129 | [-0.047767884665507826, 0.04003607690788647] |
| prose_paren | state-like | nla | NLA decoder on the prefix | 0.10282384543248801 | [0.053107504019385784, 0.15477845214078453] |
| prose_quote | state-like | ar | description | 0.012765753169687068 | [-0.07945520384192224, 0.10676320504060131] |
| prose_quote | state-like | ar | AR on the prefix | 0.007638357576636395 | [-0.006318485664167476, 0.020664514420459763] |
| prose_quote | state-like | nla | description | -0.0005764345752291259 | [-0.032197335586376157, 0.032267074981077365] |
| prose_quote | state-like | nla | NLA decoder on the prefix | 0.1608287095210487 | [0.10756188569127255, 0.21343035658743098] |
| prose_sentence | count-like | ar | description | -0.00491865046086723 | [-0.04061391584980623, 0.029812612226927368] |
| prose_sentence | count-like | ar | AR on the prefix | 0.17553431510759343 | [0.15025834629321774, 0.20172097492053434] |
| prose_sentence | count-like | nla | description | 0.011098857340885209 | [-0.00029505882860692164, 0.02261832828996218] |
| prose_sentence | count-like | nla | NLA decoder on the prefix | 0.014075864398079025 | [-0.0027785809582167756, 0.03221018885445625] |
| prose_sentiment | semantic | ar | description | 0.24848636929422463 | [0.19771007256526224, 0.29929779183662114] |
| prose_sentiment | semantic | ar | AR on the prefix | 0.08268584027500832 | [0.07077189185916778, 0.09452468625763558] |
| prose_sentiment | semantic | nla | description | 0.25508221329698744 | [0.23066775795273442, 0.27873025412944274] |
| prose_sentiment | semantic | nla | NLA decoder on the prefix | 0.3338140983936711 | [0.30894603644113505, 0.3568209808897427] |
| prose_topic | semantic | ar | description | 0.04042905253796342 | [0.014474503905342493, 0.06563592949261354] |
| prose_topic | semantic | ar | AR on the prefix | 0.022379520479632684 | [0.01631423643690919, 0.028585955641238222] |
| prose_topic | semantic | nla | description | 0.0802267251114562 | [0.06961159222999605, 0.0906213113822681] |
| prose_topic | semantic | nla | NLA decoder on the prefix | 0.25435358009133796 | [0.2376730442399993, 0.2702196375874284] |
| python_argument | count-like | ar | description | 0.014725133930878376 | [0.0053093678931045605, 0.024160849526129586] |
| python_argument | count-like | ar | AR on the prefix | 0.008372107454688216 | [0.003835369258467488, 0.012836417500723346] |
| python_argument | count-like | nla | description | 0.008301082385923666 | [0.005203876762286329, 0.011275600744018267] |
| python_argument | count-like | nla | NLA decoder on the prefix | 0.035629573052247406 | [0.028810025791190887, 0.04267102513240752] |
| python_comment | state-like | ar | description | -0.011327857694288063 | [-0.03960446705541319, 0.018248691209545642] |
| python_comment | state-like | ar | AR on the prefix | 0.02430108416120385 | [0.017165342221227856, 0.03202047208602939] |
| python_comment | state-like | nla | description | 0.030255171877971766 | [0.023398170495574213, 0.036909168950875475] |
| python_comment | state-like | nla | NLA decoder on the prefix | 0.01257555544324369 | [0.00019767382468243865, 0.02490912340468157] |
| python_depth | count-like | ar | description | 0.052143296393404384 | [0.0077149591429213635, 0.09550437166122609] |
| python_depth | count-like | ar | AR on the prefix | 0.06626622769619123 | [0.04964745566947151, 0.08258012200933089] |
| python_depth | count-like | nla | description | -0.0029439637564355483 | [-0.010390405626954391, 0.005030791890258267] |
| python_depth | count-like | nla | NLA decoder on the prefix | 0.09659494688224475 | [0.08390164774245787, 0.11048878492419802] |
| python_error | semantic | ar | description | 0.021260332446426177 | [0.008774401602435165, 0.03325115142864449] |
| python_error | semantic | ar | AR on the prefix | 0.0019358919321315541 | [-0.0006584979039683789, 0.00445036445354684] |
| python_error | semantic | nla | description | 0.021694228022961243 | [0.017343792131229527, 0.02615276566057538] |
| python_error | semantic | nla | NLA decoder on the prefix | 0.10720838182424565 | [0.09703002311172942, 0.11749372638431306] |
| python_indent | count-like | ar | description | 0.03769496259739142 | [0.0035770486748538887, 0.07355200403212724] |
| python_indent | count-like | ar | AR on the prefix | 0.0003432290411672348 | [-0.004888304876828502, 0.005552395283202899] |
| python_indent | count-like | nla | description | 0.011937946666880838 | [-0.004821085380141838, 0.027674436777970487] |
| python_indent | count-like | nla | NLA decoder on the prefix | 0.1657468565431155 | [0.1340823107466529, 0.1980789539971668] |
| python_string | state-like | ar | description | 0.011168253692800672 | [-0.0104662312874411, 0.03397253150683939] |
| python_string | state-like | ar | AR on the prefix | 0.025974802306185846 | [0.019057965700699033, 0.033573252956057995] |
| python_string | state-like | nla | description | 0.010505165702068699 | [0.004770954469867275, 0.016284754200198592] |
| python_string | state-like | nla | NLA decoder on the prefix | 0.04381641136079694 | [0.03801315605916323, 0.04933394374646056] |
| table_column | count-like | ar | description | 0.026495855911501127 | [-0.01732050484377928, 0.06838383680841725] |
| table_column | count-like | ar | AR on the prefix | 5.6231213604679054e-05 | [-0.006595435663762525, 0.0070693254324419] |
| table_column | count-like | nla | description | 0.01897337347241469 | [0.009368951224039376, 0.02857070917917609] |
| table_column | count-like | nla | NLA decoder on the prefix | 0.18448568962956718 | [0.1630966301330808, 0.2078916221778643] |
| table_role | state-like | ar | description | 0.012606357482898305 | [-0.027520507421125034, 0.04997803558179733] |
| table_role | state-like | ar | AR on the prefix | 0.03672910933134745 | [0.03179037944250166, 0.04145391536625842] |
| table_role | state-like | nla | description | 0.0015158704191162887 | [-0.004127043875680009, 0.007325210845539293] |
| table_role | state-like | nla | NLA decoder on the prefix | 0.17816866418841557 | [0.1672163173786448, 0.18978370057606658] |
| table_row | count-like | ar | description | -0.0020844456399499167 | [-0.02530126960982847, 0.024217538756297338] |
| table_row | count-like | ar | AR on the prefix | 0.015079230225391775 | [0.009686791360714089, 0.02042143509620848] |
| table_row | count-like | nla | description | 0.012609879502006665 | [0.007086084353895329, 0.018004437258261154] |
| table_row | count-like | nla | NLA decoder on the prefix | 0.13209479081709496 | [0.12283960107408182, 0.14145351350446714] |
| table_status | semantic | ar | description | 0.05834600071867513 | [0.045391939231803805, 0.07064284684275585] |
| table_status | semantic | ar | AR on the prefix | 0.008376007886821725 | [0.005153273194723244, 0.011472490043945767] |
| table_status | semantic | nla | description | 0.028497668405011178 | [0.02380103892097281, 0.03352487564111542] |
| table_status | semantic | nla | NLA decoder on the prefix | 0.02577368977297329 | [0.02254858555120226, 0.029199566236395948] |
