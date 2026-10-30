"""CPU-only E99 known-error diagnosis; no dispatch or terminal-file writes."""
from types import SimpleNamespace
from .transport217c2 import eligible
from .e99_accounting import classify_transport
from projects.g_agreement.readerbench.scoring import require

PROTOCOL = SimpleNamespace(PROVIDER_NAME='Google', MODEL='google/gemini-3.1-flash-lite')


def known_failure(call_id, saved):
    """Return the original FAILED code only for a known zero-cost finish error.

    An error object is not required by §217 clarification 2. The original E99
    classifier runs unchanged, before any family parser or partial text access.
    All other envelopes return None for the caller's original stop/402 policy.
    This helper neither chooses a retry nor authorizes a new physical send.
    """
    if not eligible(saved, PROTOCOL):
        return None
    choices = saved['response'].get('choices', [])
    if len(choices) != 1 or choices[0].get('finish_reason') != 'error':
        return None
    result = classify_transport(saved['http_status'], saved['response'])
    require(result == dict(status='FAILED', reason='INCOMPLETE_COMPLETION'), 'original E99 failure mapping')
    return dict(id=call_id, **result)
