"""Deterministic mention linking: one spelling per thing, and short names stay flagged."""
from catalyst_platform.understand_models import _TextUnit
from catalyst_platform.wiki_mentions import (
    EntityEntry,
    EntityIndex,
    normalize_surface,
    normalize_with_map,
    scan_units,
)


def unit(locator: str, quote: str) -> _TextUnit:
    return _TextUnit('source', 'relative.md', 'revision', 'revision', locator, quote)


def index(*pairs: tuple[str, str]) -> EntityIndex:
    return EntityIndex.from_entries(
        EntityEntry(surface=surface, canonical_key=key, canonical_id='canonical:' + key, kind='entity')
        for surface, key in pairs
    )


def test_a_name_is_normalized_past_quotes_spacing_and_width():
    assert normalize_surface('「客 户」') == '客户'
    assert normalize_surface('ＭＡＲＫＥＴＩＮＧ  Center') == 'marketingcenter'


def test_offsets_point_back_into_the_original_text():
    normalized, offsets = normalize_with_map('A 客户 B')
    assert normalized == 'a客户b'
    assert offsets == [0, 2, 3, 5]
    found = index(('客户', 'kehu')).match('A 客户 B')
    assert found.mentions[0].offset == 2


def test_the_longer_name_wins_over_the_shorter_one_inside_it():
    found = index(('市场', 'market'), ('市场营销中心', 'center')).match('市场营销中心负责预算')
    assert [item.canonical_key for item in found.mentions] == ['center']


def test_a_latin_name_is_not_matched_inside_a_longer_word():
    found = index(('marketing center', 'center')).match('premarketingcenter and marketing center')
    assert [item.offset for item in found.mentions] == [23]


def test_short_and_generic_surfaces_are_flagged_not_identified():
    found = index(('总部', 'zongbu'), ('市场营销中心', 'center')).match('总部与分子公司的关系')
    assert len(found.mentions) == 1
    assert found.mentions[0].ambiguous is True
    assert found.ambiguous_surfaces == ('总部',)


def test_the_index_is_built_only_from_an_accepted_version():
    assert len(EntityIndex.from_semantic_state({'candidates': {}})) == 0

    state = {
        'active_version_id': 'v1',
        'accepted_versions': {
            'v1': {
                'meanings': {
                    'm1': {'kind': 'entity', 'canonical_id': 'c1', 'canonical_key': 'center',
                           'meaning': '市场营销中心', 'business_type': 'Organization'},
                    'm2': {'kind': 'alias', 'canonical_id': 'c1', 'meaning': '营销中心'},
                    'm3': {'kind': 'relation', 'canonical_id': None, 'meaning': 'A 隶属 B'},
                }
            }
        },
    }
    built = EntityIndex.from_semantic_state(state)
    assert len(built) == 2
    found = built.match('营销中心与市场营销中心')
    assert {item.canonical_key for item in found.mentions} == {'center'}


def test_scan_counts_confident_mentions_apart_from_ambiguous_ones():
    built = index(('总部', 'zongbu'), ('市场营销中心', 'center'))
    scan = scan_units(built, [
        unit('line:1', '市场营销中心负责预算'),
        unit('line:2', '总部与分子公司的关系'),
        unit('line:3', '与本体内实体无关的一行'),
    ])
    assert scan['mention_count'] == 2
    assert scan['confident_mention_count'] == 1
    assert scan['ambiguous_count'] == 1
    assert scan['distinct_confident'] == 1
    assert scan['units_with_mentions'] == 2
