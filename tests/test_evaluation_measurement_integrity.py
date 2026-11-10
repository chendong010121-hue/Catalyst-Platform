"""Measurement identity attacks, without changing any product/grader source."""
import importlib.util
import pytest
from catalyst_platform.evaluation_adapter import check_health,run_evaluation,compare_evaluations
from tests.test_shared_evaluation_adapter import PROFILE,probes,entry,case


def test_changed_grader_source_cannot_select_candidate(tmp_path):
    source=tmp_path/'private_grader.py'
    source.write_text("def grade(o,g):\n    ok=o.get('answer')==g['answer']\n    return {'task_success':ok,'dimensions':{'TASK_SUCCESS':{'status':'PASS' if ok else 'FAIL','value':float(ok)}},'critical_faults':[],'failure_class':None if ok else 'CAPABILITY_FAILURE'}\n",encoding='utf-8')
    spec=importlib.util.spec_from_file_location('isolated_private_grader',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    grader=module.grade;health=check_health(PROFILE,grader,probes())
    for arm in ['a','b']:run_evaluation(PROFILE,[case()],entry,grader,tmp_path/arm,health=health,target_identity=arm)
    source.write_text(source.read_text(encoding='utf-8')+'# changed measurement identity\n',encoding='utf-8')
    with pytest.raises(ValueError,match='measurement identity'):compare_evaluations(tmp_path/'a',tmp_path/'b')
