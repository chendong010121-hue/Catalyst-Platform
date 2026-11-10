"""Trusted local model/rate qualification, not credentials or live discovery.

The operator owns the file. Validation binds its bytes and finite validity to
one original ModelTask. A declaration is not a supplier signature or API test.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal, DecimalException
import hashlib
import json
import re
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent / 'config'
# The models this product may switch between. Each one carries its own qualification
# file, because a price and a capacity belong to a model, not to a provider.
QUALIFIED_MODELS = ('deepseek-flash', 'deepseek-v4-pro')
MODEL_QUALIFICATION_FILES = {name: _CONFIG_DIR / (name + '.json') for name in QUALIFIED_MODELS}
DEFAULT_QUALIFICATION = MODEL_QUALIFICATION_FILES['deepseek-flash']
_SERVED_MODEL_PATTERN = {
    'deepseek-flash': r'deepseek-(?:v[0-9]+(?:\.[0-9]+)*-)?flash(?:-[0-9]{4,8})?',
    'deepseek-v4-pro': r'deepseek-(?:v[0-9]+(?:\.[0-9]+)*-)?pro(?:-[0-9]{4,8})?',
}


def qualification_for(model):
    """The shipped qualification of one model; an unqualified name is refused."""
    path = MODEL_QUALIFICATION_FILES.get(model)
    if path is None or not path.is_file():
        raise ValueError('model_not_qualified')
    return path
PRICE_URL = 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/'
FIELDS = {'schema_version','provider_id','model','base_url','served_models','price_reference',
          'verified_at','valid_until','input_cny_per_million','output_cny_per_million',
          'cache_hit_cny_per_million','input_token_limit','max_output_tokens'}


def _read(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(16385)
    except OSError:
        raise ValueError('model_qualification_unavailable') from None
    if len(raw)>16384:
        raise ValueError('model_qualification_invalid')
    return raw


def _pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('model_qualification_invalid')
        value[key]=item
    return value


def _instant(value):
    if not isinstance(value,str):raise ValueError('model_qualification_invalid')
    try:
        instant=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:
        raise ValueError('model_qualification_invalid') from None
    if instant.tzinfo is None or instant.utcoffset()!=timedelta(0):
        raise ValueError('model_qualification_invalid')
    return instant


@dataclass(frozen=True)
class ModelQualification:
    path: Path
    sha256: str
    provider_id: str
    model: str
    base_url: str
    served_models: tuple[str,...]
    price_reference: str
    verified_at: datetime
    valid_until: datetime
    input_cny_per_million: str
    output_cny_per_million: str
    cache_hit_cny_per_million: str
    input_token_limit: int
    max_output_tokens: int

    def assert_current(self, now):
        if hashlib.sha256(_read(self.path)).hexdigest()!=self.sha256:
            raise ValueError('model_qualification_changed')
        if now < self.verified_at:
            raise ValueError('model_qualification_not_yet_valid')
        if now >= self.valid_until:
            raise ValueError('official_price_refresh_required')

    def summary(self):
        return dict(qualification_sha256=self.sha256, provider_id=self.provider_id,
                    model=self.model, base_url=self.base_url, price_reference=self.price_reference,
                    price_verified_date=self.verified_at.date().isoformat(),
                    qualification_verified_at=self.verified_at.isoformat(),
                    qualification_valid_until=self.valid_until.isoformat(),
                    input_cny_per_million=self.input_cny_per_million,
                    output_cny_per_million=self.output_cny_per_million,
                    cache_hit_cny_per_million=self.cache_hit_cny_per_million,
                    input_token_limit=self.input_token_limit,
                    qualification_output_token_limit=self.max_output_tokens,
                    qualification_kind='LOCAL_OPERATOR_DECLARATION_NOT_API_VERIFICATION')


def load_qualification(path=DEFAULT_QUALIFICATION):
    path=Path(path).resolve()
    raw=_read(path)
    try:
        data=json.loads(raw, object_pairs_hook=_pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(data,dict) or set(data)!=FIELDS:raise ValueError()
        if type(data['schema_version']) is not int or data['schema_version'] not in (1,2):raise ValueError()
        if (data['provider_id'],data['base_url'],data['price_reference'])!=(
            'deepseek','https://api.deepseek.com',PRICE_URL):raise ValueError()
        if data['model'] not in MODEL_QUALIFICATION_FILES:raise ValueError()
        models=data['served_models']
        if (not isinstance(models,list) or not 1<=len(models)<=8 or
            any(not isinstance(m,str) or not 1<=len(m)<=100 or
                re.fullmatch(_SERVED_MODEL_PATTERN[data['model']],m,re.IGNORECASE) is None for m in models)
            or len(models)!=len(set(models)) or data['model'] not in models):raise ValueError()
        verified,until=_instant(data['verified_at']),_instant(data['valid_until'])
        if not timedelta(0)<until-verified<=timedelta(hours=24):raise ValueError()
        output_capacity=4096 if data['schema_version']==1 else 1_048_576
        for field,cap in [('input_token_limit',64000),('max_output_tokens',output_capacity)]:
            minimum=128 if field=='max_output_tokens' else 1
            if type(data[field]) is not int or not minimum<=data[field]<=cap:raise ValueError()
        money=[]
        for key in ['input_cny_per_million','output_cny_per_million','cache_hit_cny_per_million']:
            value=data[key]
            if not isinstance(value,str) or not 1<=len(value)<=32:raise ValueError()
            rate=Decimal(value)
            if not rate.is_finite() or rate<0:raise ValueError()
            money.append(rate)
        if money[0]<=0 or money[1]<=0 or money[2]>money[0]:raise ValueError()
        reserve=(data['input_token_limit']*money[0]+data['max_output_tokens']*money[1])/1000000
        if not reserve.is_finite() or reserve<=0:raise ValueError()
    except (ValueError,TypeError,DecimalException,UnicodeError,OverflowError,RecursionError):
        raise ValueError('model_qualification_invalid') from None
    return ModelQualification(path,hashlib.sha256(raw).hexdigest(),data['provider_id'],data['model'],
        data['base_url'],tuple(models),data['price_reference'],verified,until,
        data['input_cny_per_million'],data['output_cny_per_million'],data['cache_hit_cny_per_million'],
        data['input_token_limit'],data['max_output_tokens'])


def main():
    parser=argparse.ArgumentParser(description='Check a trusted model qualification locally; no credentials or network.')
    parser.add_argument('--file',type=Path,default=DEFAULT_QUALIFICATION)
    args=parser.parse_args()
    try:
        qualified=load_qualification(args.file)
        qualified.assert_current(datetime.now(timezone.utc))
    except ValueError as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc),'api_calls':0}))
        return 2
    print(json.dumps({'status':'QUALIFIED_LOCAL_DECLARATION','api_calls':0,**qualified.summary()}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
