"""Real offline product acceptance, distinct from synthetic grader controls."""
import json,hashlib
import pytest
from catalyst_platform.evaluation_demo import main
from catalyst_platform.evaluation_entries import ontology_entry
from catalyst_platform.evaluation_profiles import ontology_grader
from catalyst_platform._vendor.wikiskill.score_rules import finite


def test_shared_two_domain_campaign_actual_end_states_and_gates(tmp_path):
    root=tmp_path/'campaign';main(root)
    file=json.loads((root/'SECOND_SKILL_RESULTS.json').read_text(encoding='utf-8'))
    assert file['gates']['better']['accept']
    assert not file['gates']['worse']['accept']
    assert file['gates']['higher_mean_critical_regression']['reason']=='CRITICAL_REGRESSION'
    ontology=json.loads((root/'ONTOLOGY_EVAL_RESULTS.json').read_text(encoding='utf-8'))
    assert all(r['task_success'] for r in ontology['real_rows'])
    assert len(ontology['frozen_controls'])==17
    assert all((root/name/'report.html').is_file() for name in ['ontology','file_title'])
    for name in ['candidate_json','candidate_sqlite']:
        obs=json.loads((root/'ontology/baseline/cases'/name/'observation.json').read_text(encoding='utf-8'))
        assert obs['cold_read_equal'] and obs['active_version_id'] is None
        assert obs['queries'][0]['result']['status']=='FOUND'
    manifest=json.loads((root/'RUN_MANIFEST.json').read_text(encoding='utf-8'))
    for name,pin in manifest.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pin


def test_candidate_query_key_label_difference_is_not_hidden(tmp_path):
    o=ontology_entry({'source_text':'Entity: team | Team\nEntity: task | Task\nRelation: team -> owns -> task\n','entity_queries':['team']},tmp_path)
    # Current product matches literal meaning labels; this is a reported limit,
    # never replaced with invented graph answers by the evaluation adapter.
    assert o['queries'][0]['result']['status']=='NO_RELATIONS'
    g={'basis':'INDEPENDENT_FORMAL_SYNTHETIC','source_sha256':o['evidence'][0]['source_sha256'],'entity_keys':['team','task'],'relations':[['team','owns','task']],'allowed_boundary_unknowns':['approval','binding'],'requires_query':True}
    grade=ontology_grader(o,g)
    assert grade['dimensions']['STRUCTURE_VALIDITY']['status']=='PASS'
    assert grade['dimensions']['COMPETENCY_COVERAGE']['status']=='FAIL'


@pytest.mark.parametrize('value',[None,True,False,'1',float('nan'),float('inf'),-float('inf')])
def test_unchanged_wikiskill_finite_refuses_invalid_values(value):
    with pytest.raises((TypeError,ValueError)):finite(value)


@pytest.mark.parametrize('value',[0,1,-1,0.25])
def test_unchanged_wikiskill_finite_retains_numeric_semantics(value):
    assert finite(value)==float(value)
