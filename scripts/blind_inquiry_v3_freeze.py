"""Prospectively bind retrieval, collection rules and an optional private target manifest."""
from babalon.inquiry import _index
from scripts import blind_inquiry as baseline
from scripts import blind_inquiry_coverage as coverage
from scripts import blind_inquiry_v2 as custody


PROFILE = 'babalon.blind-inquiry.v3'
ENGINES = {'baseline': baseline, 'coverage': coverage}
CODE = ('scripts/blind_inquiry_v3.py', 'scripts/blind_inquiry_v3_freeze.py',
        'scripts/blind_inquiry_targets.py', 'docs/BLIND_INQUIRY_V3.md')


def _engine(readers):
    if not isinstance(readers, str) or readers not in ENGINES:
        raise ValueError('expected baseline or coverage readers')
    return ENGINES[readers]


def _implementation(readers):
    files = (*CODE, *coverage.EXTRA_CODE) if readers == 'coverage' else CODE
    hashes = custody.implementation()
    for name in files:
        hashes[name] = baseline.digest_bytes((baseline.ROOT / name).read_bytes())
    return hashes


def _corpus_refs(directory, retrieval):
    indexed, documents = _index(directory)
    control = retrieval.get('control_freeze', retrieval)
    if documents != control['documents']:
        raise ValueError('source bytes differ from the retrieval freeze')
    return sorted(indexed)


def freeze(packet, directory, rubric_hash, readers='baseline', targets_sha256=None):
    engine = _engine(readers)
    if targets_sha256 is not None:
        custody.require_digest(targets_sha256)
    retrieval = engine.freeze(packet, directory, rubric_hash)
    return {
        'profile': PROFILE, 'readers': readers, 'arms': list(engine.ARMS),
        'retrieval_freeze': retrieval, 'implementation': _implementation(readers),
        'rubric_sha256': rubric_hash, 'targets_sha256': targets_sha256,
        'corpus_refs': _corpus_refs(directory, retrieval) if targets_sha256 is not None else [],
        'promotion_eligible': False,
    }


def check_freeze(frozen, published_hash):
    custody.require_digest(published_hash)
    if baseline.digest(frozen) != published_hash:
        raise ValueError('freeze differs from the externally retained commitment')
    baseline.exact(frozen, 'profile readers arms retrieval_freeze implementation rubric_sha256 '
                           'targets_sha256 corpus_refs promotion_eligible')
    engine = _engine(frozen['readers'])
    retrieval = frozen['retrieval_freeze']
    if (frozen['profile'] != PROFILE or frozen['promotion_eligible'] is not False
            or frozen['arms'] != list(engine.ARMS) or not isinstance(retrieval, dict)
            or retrieval.get('profile') != engine.PROFILE
            or frozen['rubric_sha256'] != retrieval.get('rubric_sha256')
            or frozen['implementation'] != _implementation(frozen['readers'])):
        raise ValueError('collection profile or implementation changed')
    custody.require_digest(frozen['rubric_sha256'])
    refs = frozen['corpus_refs']
    if frozen['targets_sha256'] is None:
        if refs != []:
            raise ValueError('unexpected target reference inventory')
    else:
        custody.require_digest(frozen['targets_sha256'])
        if (not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs)
                or refs != sorted(set(refs))):
            raise ValueError('invalid target reference inventory')


def trial(packet, directory, frozen, published_hash, secret):
    check_freeze(frozen, published_hash)
    retrieval = frozen['retrieval_freeze']
    if frozen['targets_sha256'] is not None and _corpus_refs(directory, retrieval) != frozen['corpus_refs']:
        raise ValueError('passage inventory differs from the freeze')
    engine = _engine(frozen['readers'])
    sheet, key = engine.trial(packet, directory, retrieval, baseline.digest(retrieval), secret)
    # The original engine checks the retrieval inputs. Bind its unchanged rows to
    # the combined freeze before any worksheet, answers or method key is sealed.
    sheet = {**sheet, 'commitment': published_hash}
    key = {**key, 'commitment': published_hash, 'worksheet_digest': baseline.digest(sheet)}
    return sheet, key
