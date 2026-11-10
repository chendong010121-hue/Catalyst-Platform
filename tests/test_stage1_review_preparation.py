"""Review-copy integrity/privacy checks are independent of any model output."""
import pytest
from scripts.stage1_prepare_review import redact_text,verify_redaction


def test_review_copy_preserves_dates_units_and_nonfinancial_denominators():
    text='某组织2025年调研：32、52、157人，27%、65%、20%、15%；电话13812345678。'
    after,edits=redact_text(text,aliases={'某组织':'[组织甲]'},mask_numbers=False)
    assert '13812345678' not in after
    assert all(number in after for number in ['2025','32','52','157','27%','65%','20%','15%'])
    assert verify_redaction(text,after,edits)['fidelity_pass']
    assert all('before' not in e for e in edits)


def test_financial_copy_masks_values_without_inventing_replacements():
    text='2025年上半年收入12345.67万元，年度目标20000万元，预测19500万元。'
    after,edits=redact_text(text,aliases={},mask_numbers=True)
    assert '12345.67' not in after and '20000' not in after and '19500' not in after
    assert '2025' in after and '万元' in after and '预测' in after
    check=verify_redaction(text,after,edits)
    assert check['fidelity_pass'] and check['numeric_quality']=='NOT_EQUIVALENT_EXACT_VALUES_MASKED'


def test_independent_check_detects_undeclared_rewrite_or_bad_hash():
    raw='部门甲负责归档。'
    after,edits=redact_text(raw,aliases={'部门甲':'[部门A]'},mask_numbers=False)
    assert not verify_redaction(raw,after+'并拥有审批权。',edits)['fidelity_pass']
    edits[0]['before_sha256']='0'*64
    assert not verify_redaction(raw,after,edits)['fidelity_pass']
