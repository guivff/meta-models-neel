"""CPU lexical state trackers over public transcript data. Never execute commands/code."""
import json,posixpath,re,shlex
from collections import Counter
STATES=('last_test_passed','file_being_edited','failed_attempts')
TEST=re.compile(r'(?:^|&&|\|\||;|\n)\s*(?:(?:[A-Za-z_]\w*=\S+|timeout\s+\S+|env)\s+)*(?:(?:python(?:\d+(?:\.\d+)?)?)\s+(?:-m\s+(?:pytest|unittest)|\S*(?:runtests|manage)\.py(?:\s+test)?)|(?:\S*/)?(?:pytest|nosetests|tox|nox|runtests\.py)\b|(?:poetry|uv|pipenv)\s+run\s+(?:pytest|python\s+-m\s+(?:pytest|unittest))|(?:npm|pnpm|yarn|go|cargo|mvn|gradle|dotnet)\s+test\b|(?:bundle\s+exec\s+)?rspec\b|make\s+test\b)',re.I)
READ_COMMAND=re.compile(r'^\s*(?:cat\s+[^>]*$|grep\b|rg\b|find\b|head\b|tail\b|ls\b|sed\s+-n\b)',re.S)
WRITE_HINT=re.compile(r'(?<![<>=!])(?:>>?)(?![=&])\s*(?!/dev/null\b)[\w/.$\'\"]|\btee\s+|\bsed\s+[^\n]*?\s-i\b|\b(?:apply_patch|touch|mv|cp|rm)\s|\.write_(?:text|bytes)\s*\(|\bopen\([^\n]*?,\s*[\'\"][wa]',re.I)
EDIT_FAIL=re.compile(r'(?im)^\s*(?:ERROR\b|Error:)|No replacement was performed|old_str.*(?:does not appear|not found)|Invalid command|does not exist')
EDIT_OK=re.compile(r'has been (?:edited|created)|created successfully|successfully (?:edited|created|replaced|inserted)|undone successfully|File created',re.I)
VALUE_WORDS=re.compile(r'\b(?:pass(?:ed)?|fail(?:ed|ure|ures|ing)?|success(?:ful(?:ly)?)?|unsuccessful|pytest|unittest)\b',re.I)
COUNT_WORDS=re.compile(r'\b(?:attempts?|retries|retry|failure_count|failed_attempts)\b|\b(?:once|twice|thrice)\b',re.I)


def readonly_shell(command):
 """Read-only command subset, with quote-aware shell tokenization (never executed)."""
 if any(x in command for x in ('$(', '`', '<<')):return False
 try:
  lex=shlex.shlex(command,posix=True,punctuation_chars=';&|<>\n');lex.whitespace_split=True;lex.whitespace=' \t\r';lex.commenters=''
  tokens=list(lex)
 except ValueError:return False
 segments=[];current=[];i=0
 while i<len(tokens):
  word=tokens[i]
  if word in ('>','>>','>&'):
   if i+1>=len(tokens) or tokens[i+1] not in ('/dev/null','1','2'):return False
   if word in ('>','>>') and tokens[i+1]!='/dev/null':return False
   if current and current[-1] in ('1','2'):current.pop()
   i+=2;continue
  if word=='<':
   if i+1>=len(tokens):return False
   i+=2;continue
  if word in ('&&','||','|',';','&','|&') or not word.strip('\n'):
   if current:segments.append(current);current=[]
  else:
   if re.fullmatch(r'[<>;&|\n]+',word):return False
   current.append(word)
  i+=1
 if current:segments.append(current)
 def safe(words):
  if not words:return True
  head=posixpath.basename(words[0]);args=words[1:]
  if head in ('cd','pwd','ls','grep','rg','cat','head','tail','wc','cut','du','stat','which','whereis','uname','echo','printf','true','false','readlink','dirname','basename','tree'):
   return not(head=='rg' and any(a.startswith('--pre') for a in args))
  if head=='sort':return not any(a=='-o' or a.startswith('--output') or a.startswith('-o') for a in args)
  if head=='uniq':return sum(not a.startswith('-') for a in args)<=1
  if head=='find':return not any(a in ('-exec','-execdir','-delete','-ok','-okdir','-fprint','-fprint0','-fprintf','-fls') for a in args)
  if head=='git':return bool(args) and args[0] in ('diff','status','log','show','grep','ls-files','rev-parse') and not any(a.startswith(('--output','--ext-diff','--textconv','--open-files-in-pager')) for a in args)
  if head=='sed':return len(args)>=2 and args[0]=='-n' and not any(a.startswith('-i') for a in args) and bool(re.fullmatch(r'[0-9,$~+ -]+p',args[1].strip("\"'")))
  if head=='awk':return bool(args) and not args[0].startswith('-') and not any(x in args[0] for x in ('>','|','system','getline'))
  if head=='xargs':
   j=0
   while j<len(args) and args[j].startswith('-'):
    option=args[j]
    if option in ('-0','-r','--null','--no-run-if-empty','-t'):j+=1
    elif option in ('-n','-P','-I','-d'):j+=2
    elif re.fullmatch(r'-(?:n|P)\d+|-I.+',option):j+=1
    else:return False
   return j<len(args) and safe(args[j:])
  return False
 return bool(segments) and all(safe(words) for words in segments)


def test_results(command,output):
 """None=not a recognized test action; []=test action with unknown result/count."""
 count=len(TEST.findall(command))
 if not count and READ_COMMAND.match(command):return None
 if count and '<<' in command:return []
 if not count:
  if re.search(r'pytest\.main\s*\(|unittest\.main\s*\(',command):count=1
  elif re.search(r'\bpython\S*\s+\S*(?:test[_\w-]*|runtests|repro\w*)\.py\b',command):count=1
  else:return None
 if count!=1:return []
 found=[]
 for line in output.splitlines():
  s=line.strip(' =\t')
  nums=re.findall(r'(\d+)\s+(passed|failed|errors?|xfailed|xpassed|skipped|deselected)\b',s,re.I)
  if nums and (re.match(r'\d+\s+',s) or s.startswith(('Test Suites:','Tests:','test result:'))):
   failures=sum(int(n) for n,k in nums if k.lower() in ('failed','error','errors'))
   passes=sum(int(n) for n,k in nums if k.lower()=='passed')
   if failures or passes:found.append(int(failures==0))
 if found:return [found[-1]]
 if re.search(r'(?m)^Ran [1-9]\d* tests? in ',output):
  outcomes=list(re.finditer(r'(?m)^\s*(OK(?: \([^\n]*\))?|FAILED\s*\([^\n]*\))\s*$',output))
  if outcomes:return [int(outcomes[-1][1].startswith('OK'))]
 if re.search(r'(?m)^test result:\s*(?:ok|FAILED)\.',output):return [int(not re.search(r'(?m)^test result:\s*FAILED\.',output))]
 if re.search(r'(?m)^FAIL(?:\s|$)',output):return [0]
 if re.search(r'(?m)^ok\s+\S+',output):return [1]
 if re.search(r'(?im)^\s*(?:All tests passed(?: successfully)?|Tests? passed)[.!]?\s*$',output):return [1]
 if re.search(r'(?im)^\s*(?:All tests failed|Tests? failed)[.!]?\s*$',output):return [0]
 return []


def edit_result(name,args,output):
 if name!='str_replace_editor':return None
 cmd=args.get('command')
 if cmd=='view':return None
 if cmd not in ('create','str_replace','insert','undo_edit'):return ('',None)
 path=args.get('path')
 if not isinstance(path,str) or not path.startswith('/') or '\x00' in path:return ('',None)
 path=posixpath.normpath(path)
 header=next((line.strip() for line in output.splitlines() if line.strip()),'')
 if EDIT_FAIL.search(header):return (path,False)
 if EDIT_OK.search(header):return (path,True)
 return (path,None)


def scan(messages):
 """Snapshots BEFORE each original assistant message, using only earlier tool results."""
 last=None;failed=0;unknown_tests=0;files=[];last_file=None;uncertain_file=False;pending=[];stats=Counter();last_test_message=None;edit_proof=[]
 for i,m in enumerate(messages):
  role=m.get('role');text=m.get('content') or ''
  if role=='assistant':
   if not pending:
    labels={}
    if last is not None:labels['last_test_passed']=int(last)
    if failed>=3:labels['failed_attempts']=1
    elif failed==1 and unknown_tests==0:labels['failed_attempts']=0
    if not uncertain_file and len(files)==2 and last_file in files:labels['file_being_edited']=files.index(last_file)
    yield dict(next_assistant_index=i,labels=labels,files=list(files),last_file=last_file,known_failed=failed,unknown_tests=unknown_tests,last_test_message=last_test_message,edit_proof=list(edit_proof),stats=dict(stats))
   else:stats['unmatched_pending_calls']+=1;last=None;unknown_tests+=1;uncertain_file=True
   pending=[]
   for c in m.get('tool_calls') or []:
    try:
     f=c['function'];args=f.get('arguments') or '{}';args=json.loads(args) if isinstance(args,str) else args
     if not isinstance(args,dict):raise ValueError('arguments')
     pending.append((f['name'],args))
    except (ValueError,KeyError,TypeError):pending.append(('UNKNOWN',{}));stats['malformed_tool_arguments']+=1
  elif role=='tool':
   if not pending:stats['unpaired_tool_output']+=1;last=None;unknown_tests+=1;uncertain_file=True;continue
   name,args=pending.pop(0)
   if name=='UNKNOWN':last=None;unknown_tests+=1;uncertain_file=True;continue
   if name=='execute_bash':
    command=args.get('command','')
    if not isinstance(command,str):last=None;unknown_tests+=1;uncertain_file=True;continue
    results=test_results(command,text)
    if results is not None:
     stats['test_tool_calls']+=1;last_test_message=i
     if results:last=results[-1];failed+=sum(x==0 for x in results);stats['clear_test_results']+=1
     else:last=None;unknown_tests+=1;stats['ambiguous_test_results']+=1
    if not readonly_shell(command):uncertain_file=True;stats['unmodelled_or_mutating_shell_action']+=1
   edit=edit_result(name,args,text)
   if edit is not None:
    path,ok=edit
    if ok is True:
     if path not in files:files.append(path)
     last_file=path;edit_proof.append(i);stats['clear_editor_writes']+=1
    elif ok is None:uncertain_file=True;stats['ambiguous_editor_write']+=1
    else:stats['failed_editor_write']+=1


def hidden(state,tail,files):
 """Conservative literal absence; token window is computed by the pinned tokenizer."""
 if state in ('last_test_passed','failed_attempts') and VALUE_WORDS.search(tail):return False
 if state=='failed_attempts' and COUNT_WORDS.search(tail):return False
 if state=='file_being_edited':
  low=tail.casefold()
  for p in files:
   for alias in {p,p.lstrip('/'),posixpath.basename(p),'/'.join(p.split('/')[-2:])}:
    if alias and alias.casefold() in low:return False
  if re.search(r'\b(?:first|second|former|latter|previous|original)\s+file\b',tail,re.I):return False
 return True
