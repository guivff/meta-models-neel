"""E57 semantic rows; value-bearing vocabulary held out between dev and test."""
import re
from common57 import *
SPECS={
 'multi_token_entity':RowSpec('multi_token_entity',('A','B'),'content','is'),
 'antonym_crosslingual':RowSpec('antonym_crosslingual',('big','long'),'content','是'),
 'two_hop_answer':RowSpec('two_hop_answer',('eight','six'),'content','is')}
PAIRS=(('New York','New Orleans'),('San Francisco','San Diego'),('Leonardo da Vinci','Leonardo DiCaprio'),('Michael Jordan','Michael Jackson'),('South Africa','South Korea'),('North America','North Korea'))
CLUES=(
 ("Liberty Island's location","Bourbon Street's home"),
 ("Golden Gate's metropolis","Balboa Park's city"),
 ("Mona Lisa's painter","Titanic's leading actor"),
 ("The Chicago Bulls basketball legend","Thriller's singer"),
 ("Mandela's presidential country","Seoul's republic"),
 ("Canada's continent","Pyongyang's nation"),
 ("Brooklyn's address","Louisiana's jazz capital"),
 ("Alcatraz's neighbour","Petco's host"),
 ("Vitruvian Man's creator","Inception's headliner"),
 ("Air Jordan's namesake","Billie Jean's vocalist"),
 ("Johannesburg's homeland","Busan's state"),
 ("Mesoamerica's landmass","Juche's territory"))
CROSS_FORMS=('{}的反义词是','词语「{}」的反义词是','与「{}」意思相反的词是','「{}」的相反词是','形容词「{}」对应的反义词是','「{}」的反义表达是')
HOP_FORMS=('The number of legs on the animal that {} is','The leg count of the creature that {} is','For the animal that {}, the number of legs is','For a typical adult creature that {}, its leg count is','The number of legs belonging to an animal that {} is','For the creature that {}, the usual number of legs is')

def render(row,t,f,v):
 if row=='multi_token_entity':
  return f'Entry {f+11}. This entry belongs to a reference exercise. Read the description and supply its full answer. Treat the text as an ordinary completion task. The numbering identifies the entry and carries no information about the answer. '+CLUES[t][v]+' is'
 if row=='antonym_crosslingual':
  word=(('小','短') if t<6 else ('微小','短暂'))[v]
  return f'请阅读下面的词语并给出对应答案。（{f+11}）'+CROSS_FORMS[t%6].format(' '+word+' ')
 if row=='two_hop_answer':
  clues=('spins webs','builds anthills') if t<6 else ('weaves silk traps','maintains underground insect colonies')
  return f'Entry {f+11}. Give the numerical answer only. '+HOP_FORMS[t%6].format(clues[v])
 raise ValueError(row)
def generate(row):return [Item(row,t,f,v,render(row,t,f,v),SPECS[row].values[v]) for t in range(12) for f in range(7) for v in range(2)]
def check_label(row,text):
 if not text.endswith(SPECS[row].read_token_rule):raise ValueError('wrong read point')
 if row=='multi_token_entity':
  matches=[v for pair in CLUES for v,clue in enumerate(pair) if text.endswith(clue+' is')]
  if len(matches)!=1:raise ValueError('ambiguous named entity')
  return ('A','B')[matches[0]]
 if row=='antonym_crosslingual':
  has_big=any(w in text for w in ['小','微小']);has_long=any(w in text for w in ['短','短暂'])
  if has_big==has_long:raise ValueError('ambiguous adjective')
  return 'big' if has_big else 'long'
 if row=='two_hop_answer':
  a=any(x in text for x in ['spins webs','weaves silk traps']);b=any(x in text for x in ['builds anthills','maintains underground insect colonies'])
  if a==b:raise ValueError('ambiguous animal bridge')
  return 'eight' if a else 'six'
 raise ValueError(row)
def annotations(row,item):
 if row=='multi_token_entity':
  pair=PAIRS[item.template_index%6]
  return {'answer_pair':pair,'expected_answer':pair[item.variant],'distinguishing_value_words':[x.split(' ',1)[1] for x in pair],'pair_family':item.template_index%6}
 if row=='two_hop_answer':return {'answer_pair':['8','6'],'expected_answer':('8','6')[item.variant],'bridge_type':('spider-type','ant-type insect')[item.variant]}
 return {'value_words':[['big','large'],['long']],'expected_value_words':(['big','large'],['long'])[item.variant]}
