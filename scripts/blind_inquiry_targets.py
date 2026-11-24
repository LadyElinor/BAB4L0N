"""Read the custodian's optional, byte-committed exact-reference targets."""
import json
from pathlib import Path

from scripts import blind_inquiry as v1
from scripts import blind_inquiry_v2 as custody


def _references(values, corpus_refs):
    if not isinstance(values, list):
        raise ValueError('expected a list of passage references')
    seen = set()
    for ref in values:
        if not isinstance(ref, str) or ref not in corpus_refs:
            raise ValueError('unknown passage reference in target manifest')
        if ref in seen:
            raise ValueError('duplicate passage reference in target manifest')
        seen.add(ref)
    return frozenset(seen)


def load_targets(path, expected_hash, sheet, corpus_refs):
    """Return designated references per question, including explicitly empty sets.

    corpus_refs is the complete passage inventory from the frozen source documents.
    The optional metric description and equivalent-evidence annotations from the
    Ofqual format do not contribute to the designated-reference sets.
    """
    custody.require_digest(expected_hash)
    data = Path(path).read_bytes()
    if v1.digest_bytes(data) != expected_hash:
        raise ValueError('target manifest differs from its frozen digest')
    manifest = json.loads(data, object_pairs_hook=custody.unique_pairs)
    if (not isinstance(manifest, dict) or set(manifest) - {'metric', 'questions'}
            or not isinstance(manifest.get('questions'), list)):
        raise ValueError('expected target manifest with questions')
    if 'metric' in manifest and not isinstance(manifest['metric'], str):
        raise ValueError('metric description must be text')

    corpus_refs = set(corpus_refs)
    expected = {row['id'] for row in sheet['rows']}
    result = {}
    for item in manifest['questions']:
        if (not isinstance(item, dict) or not {'id', 'targets'} <= set(item)
                or set(item) - {'id', 'targets', 'equivalents'}):
            raise ValueError('expected id and targets for each question')
        qid = item['id']
        if not isinstance(qid, str) or qid not in expected or qid in result:
            raise ValueError('unknown or duplicate question in target manifest')
        designated = _references(item['targets'], corpus_refs)
        equivalents = item.get('equivalents', {})
        if not isinstance(equivalents, dict) or not equivalents.keys() <= designated:
            raise ValueError('equivalents must be keyed by designated passage reference')
        for alternatives in equivalents.values():
            _references(alternatives, corpus_refs)
        result[qid] = designated
    if result.keys() != expected:
        raise ValueError('target manifest must cover every worksheet question')
    return result
