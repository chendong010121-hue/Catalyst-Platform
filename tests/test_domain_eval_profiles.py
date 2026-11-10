"""Independent formal-fact controls, not natural-language LLM quality proof."""
import copy
import hashlib
import pytest
from catalyst_platform.evaluation_profiles import ontology_grader, file_title_grader
from catalyst_platform.evaluation_entries import ontology_entry

def sample():
    q='Relation: Team -> owns -> Task'
    e={'evidence_id':'e1','quote':q,'span_sha256':hashlib.sha256(q.encode()).hexdigest(),'source_sha256':'s','locator':'line:3'}
    rows=[{'kind':'entity','key':v,'meaning':v,'evidence_class':'SOURCE_DIRECT','evidence_refs':['e1']} for v in ['Team','Task']]
    rows.append({'kind':'relation','key':'r','subject':'Team','predicate':'owns','object':'Task','meaning':q,'evidence_class':'SOURCE_DIRECT','evidence_refs':['e1']})
    gold={'basis':'INDEPENDENT_FORMAL_SYNTHETIC','source_sha256':'s','entity_keys':['Team','Task'],'relations':[['Team','owns','Task']],'required_unknowns':[],'conditions':[],'exceptions':[],'conflicts':[],'allowed_boundary_unknowns':['approval','binding'],'unanswerable':False}
    return {'items':rows,'evidence':[e],'execution_kind':'UNIT_CONTROL','queries':[]},gold

def test_structure_pass_but_formal_fact_fail():
    o,g=sample();o['items'][-1].update(subject='Task',object='Team')
    grade=ontology_grader(o,g)
    assert grade['dimensions']['STRUCTURE_VALIDITY']['status']=='PASS'
    assert grade['dimensions']['FACTUAL_PRECISION']['status']=='FAIL'
    assert grade['task_success'] is False

def test_structure_pass_but_coverage_fail():
    o,g=sample();o['items']=o['items'][:2]
    grade=ontology_grader(o,g)
    assert grade['dimensions']['STRUCTURE_VALIDITY']['status']=='PASS'
    assert grade['dimensions']['COMPETENCY_COVERAGE']['status']=='FAIL'

def test_missing_entity_hard_rejected():
    o,g=sample();o['items'].pop(1)
    assert ontology_grader(o,g)['dimensions']['STRUCTURE_VALIDITY']['status']=='FAIL'

def test_datatype_not_an_entity_endpoint():
    o,g=sample();g['datatype_keys']=['Task']
    assert ontology_grader(o,g)['dimensions']['STRUCTURE_VALIDITY']['status']=='FAIL'

def test_known_supported_formal_relation_passes():
    o,g=sample();assert ontology_grader(o,g)['task_success'] is True

def test_correct_unknown_and_violation_are_distinct():
    o,g=sample();g.update(entity_keys=[],relations=[],required_unknowns=['status'],unanswerable=True)
    o['items']=[{'kind':'unknown','key':'status','meaning':'not supplied','uncertainty':'source does not establish status','evidence_class':'UNKNOWN','evidence_refs':[]}]
    assert ontology_grader(o,g)['task_success'] is True
    o['items'][0].pop('uncertainty')
    assert ontology_grader(o,g)['task_success'] is False

def test_all_unknown_cannot_game_answerable_case():
    o,g=sample();o['items']=[{'kind':'unknown','key':'anything','meaning':'unknown','uncertainty':'not read','evidence_class':'UNKNOWN','evidence_refs':[]}]
    assert ontology_grader(o,g)['task_success'] is False

def test_wrong_source_existing_id_does_not_prove_support():
    o,g=sample();o['evidence'][0]['source_sha256']='wrong'
    assert ontology_grader(o,g)['dimensions']['SOURCE_SUPPORT']['status']=='FAIL'

def test_exception_must_survive():
    o,g=sample();g['exceptions']=['out_of_scope']
    assert ontology_grader(o,g)['task_success'] is False

def test_grader_without_truth_is_measurement_error():
    o,g=sample();g.pop('basis')
    with pytest.raises(ValueError):ontology_grader(o,g)

def test_actual_understand_and_candidate_query(tmp_path):
    o=ontology_entry({'source_text':'Entity: Team | Team\nEntity: Task | Task\nRelation: Team -> owns -> Task\n','entity_queries':['Team'],'backend':'json'},tmp_path)
    assert o['execution_kind']=='PRODUCT_UNDERSTAND'
    assert o['queries'][0]['result']['status']=='FOUND'
    assert o['active_version_id'] is None


def test_same_context_key_opposite_literal_is_not_support():
    o,g=sample();g.update(exceptions=['limit'],context_values={'limit':'excluded when closed'})
    o['items'].append(dict(kind='exception',key='limit',meaning='included when closed',evidence_class='SOURCE_DIRECT',evidence_refs=['e1']))
    assert ontology_grader(o,g)['dimensions']['FACTUAL_PRECISION']['status']=='FAIL'

def test_query_failure_reduces_coverage_fraction():
    o,g=sample();g['requires_query']=True
    grade=ontology_grader(o,g)
    assert grade['dimensions']['COMPETENCY_COVERAGE']['value']<1

def test_unrelated_existing_quote_cannot_support_correct_triple():
    o,g=sample();g['fact_evidence']={'r':['independently frozen supporting line']}
    assert ontology_grader(o,g)['dimensions']['SOURCE_SUPPORT']['status']=='FAIL'


def test_declared_domain_range_and_relation_type_are_checked():
    o,g=sample();g.update(entity_types={'Team':'Department','Task':'WorkItem'},relation_constraints={'owns':{'domain':['Department'],'range':['WorkItem']}})
    o['items'][0]['entity_type']='WorkItem';o['items'][1]['entity_type']='Department'
    assert ontology_grader(o,g)['dimensions']['STRUCTURE_VALIDITY']['status']=='FAIL'

def test_explicit_multi_source_conflict_requires_both_sources_and_preservation():
    o,g=sample();g.update(source_sha256s=['s','other'],conflicts=['source_conflict'],context_values={'source_conflict':'Team owns Task; second source denies assignment'})
    other=dict(o['evidence'][0],evidence_id='e2',source_sha256='other');o['evidence'].append(other)
    o['items'].append(dict(kind='conflict',key='source_conflict',meaning=g['context_values']['source_conflict'],evidence_class='SOURCE_DIRECT',evidence_refs=['e1','e2']))
    assert ontology_grader(o,g)['task_success'] is True
    o['items'].pop();assert ontology_grader(o,g)['dimensions']['COMPETENCY_COVERAGE']['status']=='FAIL'
