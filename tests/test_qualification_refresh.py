from pathlib import Path
import pytest
from catalyst_platform.model_qualification import DEFAULT_QUALIFICATION
from catalyst_platform.workspace_session import WorkspaceUserSession

HTML=Path(__file__).parent/'fixtures/deepseek_official_pricing_table_20261027.html'


def test_official_metadata_is_reviewed_before_capacity_change(tmp_path):
    from catalyst_platform.qualification_refresh import QualificationReview
    host=WorkspaceUserSession(tmp_path/'workspace')
    review=QualificationReview(host.app,DEFAULT_QUALIFICATION)
    proposal=review.check(fetch=lambda:HTML.read_bytes())
    assert proposal['status']=='REVIEW_REQUIRED'
    assert proposal['qualification']['max_output_tokens']==384000
    assert not review.active_path.exists()
    with pytest.raises(ValueError):review.approve('0'*64,confirmed=True)
    q=review.approve(proposal['proposal_sha256'],confirmed=True)
    assert q.max_output_tokens==384000
    assert q.input_cny_per_million=='2' and q.output_cny_per_million=='8'
    repeated=QualificationReview(host.app,q.path).check(fetch=lambda:HTML.read_bytes())
    assert repeated['status']=='UNCHANGED_REFRESHED'


def test_changed_or_unavailable_official_layout_cannot_refresh_qualification(tmp_path):
    from catalyst_platform.qualification_refresh import QualificationReview
    host=WorkspaceUserSession(tmp_path/'workspace');review=QualificationReview(host.app,DEFAULT_QUALIFICATION)
    with pytest.raises(ValueError):review.check(fetch=lambda:b'<html>unverified</html>')
    assert not review.active_path.exists()

@pytest.mark.parametrize('html',[b'<table><tr><td>model</td></tr></table>',b'<html></html>'])
def test_malformed_official_table_fails_closed(tmp_path,html):
    from catalyst_platform.qualification_refresh import QualificationReview
    host=WorkspaceUserSession(tmp_path/'workspace');review=QualificationReview(host.app,DEFAULT_QUALIFICATION)
    with pytest.raises(ValueError):review.check(fetch=lambda:html)
    assert not review.active_path.exists()
