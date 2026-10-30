"""Draft E20 fixed-A event parser. Not scientifically frozen until real dev validation."""
import re

def positive(feature,text):
    if feature=='prose_paren':
        depth=0
        for ch in text:
            if ch=='(':depth+=1
            elif ch==')':
                if depth==0:return True
                depth-=1
        return False
    if feature=='python_string':
        body=re.sub(r'^\s*-\s*','',text)
        # Discovery-style first-word quote OR an unmatched double quote.
        return bool(re.match(r'^\s*\w+"',body)) or text.count('"')%2==1
    if feature=='prose_sentiment_delayed':return bool(re.search(r'\bwonderful\b',text,re.I))
    if feature=='fact_once':return bool(re.search(r'(?<!\d)1234(?!\d)',text))
    raise ValueError(feature)

def positive_bullets(feature,bullets):
    if len(bullets)!=4:raise ValueError('exactly four native outputs required')
    return sum(positive(feature,x) for x in bullets)
