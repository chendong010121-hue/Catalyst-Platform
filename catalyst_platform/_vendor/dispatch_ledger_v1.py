"""Campaign-local dispatch receipts; does not replace the existing P0 ModelTask."""
import os, json, hashlib, datetime, msvcrt
from pathlib import Path
from decimal import Decimal

RESERVE = Decimal('0.465536')
CAP = Decimal('1.862144')
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def digest(v): return hashlib.sha256(canonical(v)).hexdigest()
def put(path, data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f: f.write(data);f.flush();os.fsync(f.fileno())

class Lock:
    def __init__(self,path): self.path=Path(path);self.f=None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.f=self.path.open('a+b');self.f.seek(0)
        if self.path.stat().st_size==0:self.f.write(b'0');self.f.flush();os.fsync(self.f.fileno())
        self.f.seek(0)
        try:msvcrt.locking(self.f.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:self.f.close();self.f=None;raise ValueError('exclusive execution busy') from None
        return self
    def __exit__(self,*args):
        if self.f:self.f.seek(0);msvcrt.locking(self.f.fileno(),msvcrt.LK_UNLCK,1);self.f.close();self.f=None

class Ledger:
    def __init__(self,root,*,policy=None):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.policy=policy
        if policy is not None:
            if type(policy.get('max_requests'))!=int or not 1<=policy['max_requests']<=100:raise ValueError('finite request cap required')
            for key in ('reserve_cny','budget_cny','input_cny_per_million','output_cny_per_million','cache_hit_cny_per_million'):
                v=Decimal(policy[key])
                if not v.is_finite() or v<0:raise ValueError('finite price/budget required')
            if Decimal(policy['reserve_cny'])<=0 or not policy.get('task_id'):raise ValueError('task reservation required')
            with Lock(self.root/'LEDGER.lock'):
                pin=self.root/'M6B_POLICY.json'
                if not pin.exists():put(pin,canonical(policy))
                if pin.read_bytes()!=canonical(policy):raise ValueError('task policy drift')
        self.path=self.root/('M6B_DISPATCH_LEDGER.jsonl' if policy is not None else 'M3_DISPATCH_LEDGER.jsonl')
    def read(self):
        if not self.path.exists():return []
        raw=self.path.read_bytes()
        if raw and not raw.endswith(b'\n'):raise ValueError('partial ledger: reconcile, never retry')
        rows=[];prev='0'*64
        for line in raw.splitlines():
            row=json.loads(line);h=row.pop('hash')
            if row['previous']!=prev or digest(row)!=h:raise ValueError('ledger integrity failure')
            row['hash']=h;rows.append(row);prev=h
        return rows
    def _append(self,rows,event,**fields):
        row=dict(sequence=len(rows)+1,previous=rows[-1]['hash'] if rows else '0'*64,
                 time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),event=event,**fields)
        row['hash']=digest(row)
        with self.path.open('ab') as f:f.write(canonical(row)+b'\n');f.flush();os.fsync(f.fileno())
        return row
    @staticmethod
    def _dispatch_state(rows):
        pending={r['slot'] for r in rows if r['event']=='RESERVED_BEFORE_SEND'}-{r['slot'] for r in rows if r['event']=='METERED'}
        stopped=any(r['event'] in ('FAILED_STOP','GATE_STOP') for r in rows)
        return pending,stopped
    def is_settled(self):
        """Read verified ledger facts only; not dispatch or resume authorization.

        Corrupt/partial receipts still raise. Empty receipts are settled, and
        P0 uncertainty, task caps, stage order and Owner scope remain separate.
        """
        pending,stopped=self._dispatch_state(self.read())
        return not pending and not stopped
    def reserve(self,arm,stage,request_sha,**meta):
        with Lock(self.root/'LEDGER.lock'):
            rows=self.read();reserved=[r for r in rows if r['event']=='RESERVED_BEFORE_SEND']
            pending,stopped=self._dispatch_state(rows)
            if stopped:raise ValueError('global gate closed')
            if pending:raise ValueError('pending dispatch: consumed, no retry')
            if self.policy is not None:
                if (self.root/'M6B_POLICY.json').read_bytes()!=canonical(self.policy):raise ValueError('task policy drift')
                if stage not in ('optimizer.propose','subject.selection','subject.extraction','optimizer.decision'):raise ValueError('task stage')
                if not isinstance(arm,str) or not arm.startswith(('parent','round')):raise ValueError('task arm')
                if any(r['arm']==arm and r['stage']==stage for r in reserved):raise ValueError('duplicate task request')
                order=('subject.selection','subject.extraction') if arm.startswith('parent') else ('optimizer.propose','subject.selection','subject.extraction','optimizer.decision')
                own=[r for r in reserved if r['arm']==arm]
                if len(own)>=len(order) or stage!=order[len(own)]:raise ValueError('task stage order')
                reserve=Decimal(self.policy['reserve_cny'])
                if len(reserved)>=self.policy['max_requests'] or (len(reserved)+1)*reserve>Decimal(self.policy['budget_cny']):raise ValueError('task dispatch/budget cap')
                return self._append(rows,'RESERVED_BEFORE_SEND',slot=len(reserved)+1,arm=arm,stage=stage,request_sha256=request_sha,reserved_cny=str(reserve),task_id=self.policy['task_id'],**meta)
            if arm not in ('A','B') or stage not in ('selection','extraction'):raise ValueError('unknown arm/stage')
            own=[r for r in reserved if r['arm']==arm]
            if len(reserved)>=4 or len(own)>=2 or (len(reserved)+1)*RESERVE>CAP:raise ValueError('dispatch/budget cap')
            if any(r['stage']==stage for r in own):raise ValueError('duplicate stage forbidden')
            if (not own and stage!='selection') or (own and stage!='extraction'):raise ValueError('stage order')
            slot=len(reserved)+1
            return self._append(rows,'RESERVED_BEFORE_SEND',slot=slot,arm=arm,stage=stage,
                request_sha256=request_sha,reserved_cny=str(RESERVE),**meta)
    def fail(self,slot,reason):
        with Lock(self.root/'LEDGER.lock'):
            return self._append(self.read(),'FAILED_STOP',slot=slot,reason=reason,retained_cny=str(self.policy['reserve_cny'] if self.policy else RESERVE))
    def stop(self,reason):
        with Lock(self.root/'LEDGER.lock'):return self._append(self.read(),'GATE_STOP',reason=reason)
    def settle(self,slot,data,output_cap):
        with Lock(self.root/'LEDGER.lock'):
            rows=self.read()
            if any(r['event']=='METERED' and r['slot']==slot for r in rows):raise ValueError('duplicate settlement')
            reserved=next(r for r in rows if r['event']=='RESERVED_BEFORE_SEND' and r['slot']==slot)
            u=data.get('usage');model=data.get('model');fp=data.get('system_fingerprint')
            if not isinstance(u,dict):raise ValueError('usage missing')
            p,c=u.get('prompt_tokens'),u.get('completion_tokens')
            if type(p)!=int or type(c)!=int or p<0 or c<0 or p>200000 or c>output_cap:raise ValueError('usage bound')
            if u.get('total_tokens')!=p+c:raise ValueError('usage total mismatch')
            hit=u.get('prompt_cache_hit_tokens');miss=u.get('prompt_cache_miss_tokens')
            details=u.get('prompt_tokens_details') or {}
            if hit is None:hit=details.get('cached_tokens',0)
            if miss is None:miss=p-hit
            if type(hit)!=int or type(miss)!=int or min(hit,miss)<0 or hit+miss!=p:raise ValueError('cache usage mismatch')
            if 'cached_tokens' in details and details['cached_tokens']!=hit:raise ValueError('cache details mismatch')
            rates=self.policy or dict(input_cny_per_million='2',cache_hit_cny_per_million='0.04',output_cny_per_million='8')
            cost=(Decimal(miss)*Decimal(rates['input_cny_per_million'])+Decimal(hit)*Decimal(rates['cache_hit_cny_per_million'])+Decimal(c)*Decimal(rates['output_cny_per_million']))/1000000
            reserve=Decimal(self.policy['reserve_cny']) if self.policy else RESERVE
            if cost>reserve:raise ValueError('actual estimated cost exceeds reserve')
            models=self.policy.get('served_models',[self.policy['model']]) if self.policy else ('deepseek-flash','deepseek-v4.1-flash-1017','DeepSeek-V4.1-Flash-1017')
            if model not in models:raise ValueError('model drift')
            # Alias alone cannot demonstrate backend equality. Missing fingerprint stops.
            if not isinstance(fp,str) or not fp.strip():raise ValueError('served backend fingerprint unavailable')
            prior=[r for r in rows if r['event']=='METERED']
            if any((r['model'],r['system_fingerprint'])!=(model,fp) for r in prior):raise ValueError('model/fingerprint drift')
            return self._append(rows,'METERED',slot=slot,arm=reserved['arm'],stage=reserved['stage'],
                provider_request_id=data.get('id'),model=model,system_fingerprint=fp,usage=u,
                peak_rate_estimated_cny=str(cost),retained_authorization_reserve_cny=str(reserve),
                supplier_invoice_verified=False)
