"""Physical-ledger snapshot + evidenced open bank caps; no programme allowances."""
import fcntl
import json
import subprocess
import time
from decimal import Decimal
from pathlib import Path

from .transport import ROOT, SHARED, CAPS
from projects.g_agreement.readerbench.io import read, write, sha
from projects.g_agreement.readerbench.scoring import require


def physical_rows(sources):
    physical={}
    source_proofs=[]
    seen=set()
    for path in sources:
        require(path.exists(),'previously registered ledger missing')
        inode=(path.stat().st_dev,path.stat().st_ino)
        if inode in seen:continue
        seen.add(inode)
        with path.open('rb') as f:
            fcntl.flock(f,fcntl.LOCK_SH)
            raw=f.read()
            fcntl.flock(f,fcntl.LOCK_UN)
        local={}
        settled=set()
        for row in [json.loads(l) for l in raw.splitlines() if l.strip()]:
            cost=Decimal(str(row['usd']))
            require(cost.is_finite() and cost>=0,'finite nonnegative ledger amount')
            rid=row['id']
            if row['event']=='reserve':
                require(rid not in local,'duplicate reserve')
                ident=(rid,str(row['at']))
                local[rid]=ident
                p=physical.setdefault(ident,dict(upper=cost,actual=None))
                require(p['upper']==cost,'mirrored reserve agrees')
            else:
                require(row['event']=='settle' and rid in local and rid not in settled,'unique known settlement')
                settled.add(rid)
                p=physical[local[rid]]
                require(p['actual'] in (None,cost),'mirrored charge agrees')
                p['actual']=cost
        source_proofs.append(dict(path=str(path.resolve()),sha256=sha(path)))
    actual=sum((p['actual'] for p in physical.values() if p['actual'] is not None),Decimal(0))
    unknown=sum((p['upper'] for p in physical.values() if p['actual'] is None),Decimal(0))
    return actual,unknown,source_proofs


def bank_actual(root):
    path=Path(root)/'ledger.jsonl'
    if not path.exists():return Decimal(0),Decimal(0)
    a,u,_=physical_rows([path])
    return a,u


def snapshot(new_banks=()):
    policy_path=ROOT/'results/g_agreement/compiler/JUDGING_CURRENT.json'
    policy=read(policy_path)
    require(policy['ceiling_usd']==1000 and policy['warning_usd']==800,'registered1000/800')
    base=ROOT.parent
    roots=[base/'wt-blindspot-internals/cache/g_agreement/understand/blind_judge',
           base/'wt-internals-b/cache/g_agreement/understand',base/'wt-i2/cache/g_agreement/i2',
           base/'wt-i4/cache/g_agreement/e96',base/'wt-i5/cache/g_agreement',
           ROOT/'cache/g_agreement',Path('/Users/guivff/repl/activation-readers-i5'),
           Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/understand'),
           Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops')]
    paths=[Path(x['path']) for x in policy['sources']]
    for root in roots:
        if not root.exists():continue
        p=subprocess.run(['rg','--files','--hidden','--no-ignore','--follow',str(root),'-g','ledger.jsonl','-g','LEDGER.jsonl'],capture_output=True,text=True)
        require(p.returncode in (0,1),'ledger inventory completed')
        paths.extend(Path(x) for x in p.stdout.splitlines())
    actual,unknown,proofs=physical_rows(paths)
    require(actual>=Decimal(policy['actual_physical_settled_usd']),'settled total did not disappear')
    open_banks={}
    # Compiler's evidenced live separate E96 allocation, released only by its
    # terminal seal; original retained E96 allocation is already completed.
    separate=base/'wt-i4/cache/g_agreement/e96/separate_slot1'
    if (separate/'judgments/START.json').exists() and not any((separate/'judgments'/n).exists() for n in ('JUDGMENT_SEAL.json','RESULT_SEAL.json')):
        a,u=bank_actual(separate/'ledger')
        open_banks['E96_separate']=dict(cap='50',settled_usd=str(a),open_usd=str(max(Decimal(0),Decimal(50)-a-u)))
    e86=base/'wt-i2/cache/g_agreement/i2/e86_judge_cpu_v1/judging'
    if (e86/'E86_judgments/START.json').exists() and not(e86/'E86_judgments/RESULT_SEAL.json').exists():
        a,u=bank_actual(e86)
        open_banks['E86']=dict(cap='4',settled_usd=str(a),open_usd=str(max(Decimal(0),Decimal(4)-a-u)))
    for bank in CAPS:
        allocation=SHARED/bank/'ALLOCATION_C.json'
        if bank not in new_banks and not allocation.exists():continue
        if allocation.exists() and read(allocation).get('status')=='RELEASED':continue
        a,u=bank_actual(SHARED/bank/'ledger')
        open_banks[bank]=dict(cap=str(CAPS[bank]),settled_usd=str(a),open_usd=str(max(Decimal(0),CAPS[bank]-a-u)))
    # Other owners' canonical parallel banks advertise a live status and cap.
    known={'E87':Decimal(70),'E100':Decimal(30),'E101':Decimal(5),'E103':Decimal(5),'E104':Decimal(5),'E97':Decimal(15),'E98':Decimal(10)}
    for bank,cap in known.items():
        root=SHARED/bank
        active=any(p.exists() and read(p).get('status')=='RUNNING' for p in (root/'STATUS.json',root/'PARALLEL_STATUS.json'))
        if active and not(root/'judgments/JUDGMENT_SEAL.json').exists():
            a,u=bank_actual(root/'ledger')
            open_banks[bank]=dict(cap=str(cap),settled_usd=str(a),open_usd=str(max(Decimal(0),cap-a-u)))
    open_total=sum((Decimal(x['open_usd']) for x in open_banks.values()),Decimal(0))
    exposure=actual+unknown+open_total
    require(exposure<=1000,'global admission ceiling')
    return dict(at_epoch=time.time(),actual_settled_usd=str(actual),unknown_physical_holds_usd=str(unknown),
                open_banks=open_banks,open_caps_remaining_usd=str(open_total),actual_plus_open_caps_usd=str(exposure),
                warning_triggered=exposure>=800,ceiling_usd=1000,policy_sha256=sha(policy_path),
                ledger_sources=proofs,unreported_account_liabilities='not inferred zero; same source coverage as current compiler physical-ledger inventory')
