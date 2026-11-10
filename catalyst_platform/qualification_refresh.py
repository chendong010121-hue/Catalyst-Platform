"""Bounded public official metadata check, never a model/API/credential call.

Only an unchanged declaration can refresh automatically. Changed model, price
or capacity needs the exact local proposal confirmation; unknown layouts stop.
"""
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import hashlib
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from .model_qualification import PRICE_URL, load_qualification


def fetch_official():
    class SameHost(HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            if urlsplit(newurl).scheme!='https' or urlsplit(newurl).hostname!='api-docs.deepseek.com':
                raise ValueError('official_metadata_redirect_denied')
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    with build_opener(SameHost()).open(Request(PRICE_URL,headers={'Accept':'text/html',
            'User-Agent':'Catalyst-public-qualification/1'}),timeout=8) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError('official_metadata_too_large')
    return raw


def parse_official(raw,current):
    class Table(HTMLParser):
        def __init__(self):super().__init__();self.cell=None;self.row=[];self.rows=[]
        def handle_starttag(self,t,a):
            if t in ('td','th'):self.cell=[]
            if t=='tr':self.row=[]
        def handle_data(self,d):
            if self.cell is not None:self.cell.append(d)
        def handle_endtag(self,t):
            if t in ('td','th') and self.cell is not None:
                self.row.append(re.sub(r'\s+','',''.join(self.cell)));self.cell=None
            if t=='tr' and self.row:self.rows.append(self.row)
    p=Table();p.feed(raw.decode('utf-8'));rows=p.rows
    def one(label):
        found=[r for r in rows if r[0]==label]
        if len(found)!=1 or len(found[0])<2:raise ValueError('official_metadata_layout_unrecognized')
        return found[0]
    header=[re.sub(r'\([0-9]+\)','',cell) for cell in one('模型')[1:]]
    if current['model'] not in header:
        raise ValueError('official_model_identity_mismatch')
    # Every price row carries one cell per model, in the order the header declares.
    column=header.index(current['model'])
    if one('BASEURL(OpenAI格式)')[1]!='https://api.deepseek.com':
        raise ValueError('official_endpoint_mismatch')
    version=one('模型版本')[1:][column] if len(one('模型版本'))>1+column else one('模型版本')[1]
    def capacity(label):
        match=re.fullmatch(r'(?:最大)?([0-9]+)([KM]?)',one(label)[1])
        if not match:raise ValueError('official_capacity_unrecognized')
        # Conservative decimal K/M; no optimistic interpretation of vendor units.
        return int(match[1])*{'':1,'K':1000,'M':1000000}[match[2]]
    def peak(marker):
        indices=[i for i,r in enumerate(rows) if any(marker==v for v in r)]
        if len(indices)!=1 or indices[0]+1>=len(rows):raise ValueError('official_price_unrecognized')
        r=rows[indices[0]+1]
        if len(r)<2+column or r[0]!='高峰时段' or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?元',r[1+column]):
            raise ValueError('official_price_unrecognized')
        return r[1+column][:-1]
    value=dict(current)
    value.update(schema_version=2,served_models=list(dict.fromkeys([current['model'],version.lower(),version])),
        input_cny_per_million=peak('百万tokens输入（缓存未命中）'),
        output_cny_per_million=peak('百万tokens输出'),
        cache_hit_cny_per_million=peak('百万tokens输入（缓存命中）'),
        max_output_tokens=capacity('输出长度'))
    if value['input_token_limit']+value['max_output_tokens']>capacity('上下文长度'):
        raise ValueError('official_context_capacity_exceeded')
    return value


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class QualificationReview:
    def __init__(self,app,current_path):
        self.app=app;self.current_path=current_path
        self.root=app.state_root/'workspace-settings'
        self.proposal_path=self.root/'qualification-proposal.json'
        self.active_path=self.root/'model-qualification.json'

    def _archive(self,prefix,sha,value):
        # Bounded Windows paths; full hashes remain inside each record. A
        # truncated-name collision refuses rather than replacing prior evidence.
        path=self.app.state_root/'q'/(prefix+'_'+sha[:24]+'.json')
        if path.exists():
            old=json.loads(path.read_text(encoding='utf-8'))
            strip=lambda v:{k:x for k,x in v.items() if k!='timestamp'}
            if strip(old)!=strip(value):raise ValueError('qualification_history_collision')
        else:self.app._atomic_json(path,value)

    def check(self,*,fetch=fetch_official):
        current=load_qualification(self.current_path)
        old=json.loads(current.path.read_text(encoding='utf-8'))
        raw=fetch()
        if not isinstance(raw,bytes) or len(raw)>2_000_000:raise ValueError('official_metadata_invalid')
        value=parse_official(raw,old);now=datetime.now(timezone.utc)
        value.update(verified_at=now.isoformat(),valid_until=(now+timedelta(hours=24)).isoformat())
        candidate=self.root/'qualification-candidate.json'
        self.app._atomic_json(candidate,value)
        load_qualification(candidate).assert_current(now)
        body=dict(qualification=value,source_sha256=hashlib.sha256(raw).hexdigest(),source_url=PRICE_URL,
                  checked_at=now.isoformat())
        unchanged={k:v for k,v in old.items() if k not in {'verified_at','valid_until'}}=={
            k:v for k,v in value.items() if k not in {'verified_at','valid_until'}}
        proposal=dict(body,proposal_sha256=digest(body),status='UNCHANGED_REFRESHED' if unchanged else 'REVIEW_REQUIRED')
        self._archive('p',proposal['proposal_sha256'],proposal)
        self._archive('s',body['source_sha256'],dict(source_url=PRICE_URL,sha256=body['source_sha256'],html=raw.decode('utf-8')))
        self.app._atomic_json(self.proposal_path,proposal)
        if unchanged:self.approve(proposal['proposal_sha256'],confirmed=True)
        return proposal

    def approve(self,approval,*,confirmed):
        value=json.loads(self.proposal_path.read_text(encoding='utf-8'))
        body={k:v for k,v in value.items() if k not in {'proposal_sha256','status'}}
        if confirmed is not True or approval!=digest(body) or value['proposal_sha256']!=approval:
            raise ValueError('official_metadata_approval_mismatch')
        candidate=self.root/'qualification-candidate.json'
        self.app._atomic_json(candidate,value['qualification'])
        q=load_qualification(candidate);q.assert_current(datetime.now(timezone.utc))
        self._archive('q',q.sha256,value['qualification'])
        self._archive('a',approval,
            dict(proposal_sha256=approval,qualification_sha256=q.sha256,confirmed=True,
                 kind='UNCHANGED_PUBLIC_REFRESH' if value['status']=='UNCHANGED_REFRESHED' else 'OWNER_EXPLICIT',
                 timestamp=datetime.now(timezone.utc).isoformat()))
        self.app._atomic_json(self.active_path,value['qualification'])
        return load_qualification(self.active_path)
