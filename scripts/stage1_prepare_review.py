"""Offline review-copy helpers. No model, credential, or admission capability.

These checks establish declared-edit integrity, not privacy certification or
permission to transmit. A data owner must review every proposed outbound copy.
"""
import hashlib
import re
import secrets
import string


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def redact_text(text, *, aliases, mask_numbers, extra_spans=()):
    """Return a review copy and non-overlapping, hash-only edit audit.

    Years are retained heuristically; this cannot certify financial privacy.
    extra_spans are (start, end, replacement, reason) supplied by a reader.
    """
    proposed = list(extra_spans)
    for old, new in sorted(aliases.items(), key=lambda pair: -len(pair[0])):
        if not old:
            raise ValueError('empty alias')
        proposed.extend((m.start(), m.end(), new, 'alias')
                        for m in re.finditer(re.escape(old), text))
    for pattern in (r'(?<!\d)1[3-9]\d{9}(?!\d)',
                    r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
                    r'(?<!\d)\d{17}[\dXx](?!\d)'):
        proposed.extend((m.start(), m.end(), '[CONTACT_REMOVED]', 'contact')
                        for m in re.finditer(pattern, text))
    if mask_numbers:
        for match in re.finditer(r'\d+(?:[,.]\d+)*', text):
            if re.fullmatch(r'(?:19|20)\d{2}', match.group()):
                continue
            opaque = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(12))
            proposed.append((match.start(), match.end(), f'[VALUE_{opaque}]', 'financial_number'))
    selected = []
    for start, end, replacement, reason in proposed:
        if not (0 <= start < end <= len(text)):
            raise ValueError('invalid redaction span')
        if any(start < other[1] and end > other[0] for other in selected):
            continue
        selected.append((start, end, replacement, reason))
    edits = [dict(start=a, end=b, replacement=c, reason=d,
                  before_sha256=_sha(text[a:b])) for a, b, c, d in sorted(selected)]
    cursor, parts = 0, []
    for edit in edits:
        parts.extend((text[cursor:edit['start']], edit['replacement']))
        cursor = edit['end']
    parts.append(text[cursor:])
    return ''.join(parts), edits


def verify_redaction(original, redacted, edits):
    """Independently reconstruct the copy; reject undeclared edits or bad hashes."""
    cursor, parts, valid = 0, [], True
    try:
        for edit in edits:
            a, b = edit['start'], edit['end']
            if not (cursor <= a < b <= len(original)):
                valid = False
                break
            valid &= edit['before_sha256'] == _sha(original[a:b])
            parts.extend((original[cursor:a], edit['replacement']))
            cursor = b
        parts.append(original[cursor:])
        valid &= ''.join(parts) == redacted
    except (KeyError, TypeError, ValueError):
        valid = False
    return {'fidelity_pass': bool(valid),
            'numeric_quality': ('NOT_EQUIVALENT_EXACT_VALUES_MASKED'
                                if any(e.get('reason') == 'financial_number' for e in edits)
                                else 'UNCHANGED_OUTSIDE_DECLARED_REDACTIONS'),
            'privacy_certified': False, 'external_transmission': 'OWNER_APPROVAL_PENDING'}
