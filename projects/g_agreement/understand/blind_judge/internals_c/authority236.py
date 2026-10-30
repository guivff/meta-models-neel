"""Prospective paid-time extension for frozen existing work; no live source edits."""
import time
from contextlib import contextmanager
from . import transport
from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require

EXTENDED_EXPIRY=1793372400  # Fri30Oct2026 15:00UTC /16:00CET


def validate(authority,bank,existing_source_sha256,now):
    require(authority['authority']=='direct Guiv paid-judging extension' and
            authority['paid_until_epoch']==EXTENDED_EXPIRY and authority['no_new_runs'] is True and
            authority['bank_caps_unchanged'] is True and authority['missing_stays_missing'] is True,'exact human time-only extension')
    require(authority['route']==dict(model='google/gemini-3.1-flash-lite',provider='google-vertex/global',gateway='OpenRouter',zdr=True,data_collection='deny',fallbacks=False),'unchanged sole approved route')
    require(existing_source_sha256 in authority['existing_source_sha256'].get(bank,[]),'only frozen pre-existing run scope, no new run')
    require(now<EXTENDED_EXPIRY,'standing authorization expired Fri16CET')


@contextmanager
def existing_work(bank,existing_source_sha256):
    p=transport.HERE/'PAID_AUTHORITY_EXTENSION236.json'
    source=read(transport.HERE/'PAID_AUTHORITY_EXTENSION236_SOURCE_SEAL.json')
    for n,h in source['files'].items():require(sha(transport.ROOT/n)==h,'published prospective authority source')
    validate(read(p),bank,existing_source_sha256,time.time())
    old=transport.EXPIRY
    require(old in (1793336400,EXTENDED_EXPIRY),'known original/extended cutoff only')
    transport.EXPIRY=EXTENDED_EXPIRY
    try:yield
    finally:transport.EXPIRY=old
