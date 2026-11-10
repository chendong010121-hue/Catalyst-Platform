"""Assemble the ORIGINAL server with a deterministic transport for browser QA.

No provider/loop implementation is added. This fixture must not be used as a
production launcher or semantic benchmark. All input is synthetic.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    network=[];forbidden=[]
    original_connect=socket.socket.connect
    original_connect_ex=socket.socket.connect_ex
    original_resolve=socket.getaddrinfo
    def permitted(address):
        return isinstance(address,tuple) and address[0] in ('127.0.0.1','::1','localhost')
    def connect(sock,address):
        if sock.family in (socket.AF_INET,socket.AF_INET6) and not permitted(address):
            network.append(str(address));raise RuntimeError('QUALIFICATION_EXTERNAL_CONNECT_DENIED')
        return original_connect(sock,address)
    def connect_ex(sock,address):
        if sock.family in (socket.AF_INET,socket.AF_INET6) and not permitted(address):
            network.append(str(address));raise RuntimeError('QUALIFICATION_EXTERNAL_CONNECT_DENIED')
        return original_connect_ex(sock,address)
    def resolve(host,*rest,**kw):
        if host not in ('127.0.0.1','::1','localhost',None):
            network.append(str(host));raise RuntimeError('QUALIFICATION_EXTERNAL_DNS_DENIED')
        return original_resolve(host,*rest,**kw)
    socket.socket.connect=connect;socket.socket.connect_ex=connect_ex;socket.getaddrinfo=resolve
    def audit(event,values):
        if event=='open' and values and isinstance(values[0],(str,bytes,Path)):
            path=str(values[0]).replace('\\','/').lower()
            if path.startswith('e:/catalyst_architecture_integration/') or path.startswith('e:/c02m3/'):
                forbidden.append(path);raise RuntimeError('HISTORICAL_HOST_OR_RUN_READ_DENIED')
    sys.addaudithook(audit)
    from catalyst_platform.workspace_ui import create_workspace_server
    from catalyst_platform.asset_records import builtin_assets
    from catalyst_platform.workspace_ledger import HOST_DURABLE
    import catalyst_platform.workbench as workbench
    import agent_runtime.runtime as runtime
    server=create_workspace_server(args.workspace,port=args.port,mode='MOCK')
    session=server.run_request
    session.app.components.assets.register(builtin_assets())
    call_file=args.out/'deterministic-calls.jsonl'
    def save_state():
        (args.out/'fences.json').write_text(json.dumps(dict(external_attempts=network,
            forbidden_reads=forbidden,fixture='DETERMINISTIC_TRANSPORT_NOT_LIVE_API',
            real_api_calls=0),indent=2),encoding='utf-8')
    def exchange(url,headers,body):
        rows=session.settings.ledger.read()
        assert rows[-1]['event']=='RESERVED_BEFORE_SEND'
        assert rows[-1]['request_sha256']==hashlib.sha256(body).hexdigest()
        request=json.loads(body)
        scenario='ordinary'
        text='\n'.join(str(m.get('content','')) for m in request['messages'])
        if 'OFFLINE_FIXTURE_TIMEOUT' in text:scenario='timeout'
        elif 'OFFLINE_FIXTURE_SLOW' in text:scenario='slow'
        number=1+len(call_file.read_text(encoding='utf-8').splitlines()) if call_file.exists() else 1
        record=dict(ordinal=number,scenario=scenario,request_sha256=hashlib.sha256(body).hexdigest(),
                    original_request=request,real_api=False)
        with call_file.open('a',encoding='utf-8') as handle:handle.write(json.dumps(record,ensure_ascii=False)+'\n')
        save_state()
        if scenario=='timeout':raise TimeoutError('synthetic fixture timeout; no remote request')
        if scenario=='slow':
            until=time.monotonic()+15
            while time.monotonic()<until and not session.settings.provider.cancelled:time.sleep(.05)
        tools=request.get('tools') or []
        tool_messages=[m for m in request['messages'] if m['role']=='tool']
        if tools and not tool_messages:
            name=tools[0]['function']['name']
            message=dict(role='assistant',content=None,tool_calls=[dict(id='qualification-tool-call',
                type='function',function=dict(name=name,arguments='{"query":"*"}'))])
            finish='tool_calls'
        else:
            message=dict(role='assistant',content='离线模型替身：Catalyst 已通过原 Harness 执行本次机制测试。'
                         +('已收到真实 Wiki 产品资产工具结果；不代表真实模型语义能力。' if tool_messages else
                           '可查看能力、运行证据和资料；本回答不是外部模型输出。'))
            finish='stop'
        response=dict(id=f'offline-qualification-{number}',model=request.get('model') or 'deepseek-flash',
            system_fingerprint='offline-qualification-fixture',
            choices=[dict(index=0,message=message,finish_reason=finish)],
            usage=dict(prompt_tokens=100,completion_tokens=20,total_tokens=120))
        (args.out/f'response-{number}.json').write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf-8')
        return 200,response
    session.settings.transport_override=exchange
    (args.out/'ready.json').write_text(json.dumps(dict(port=server.server_port,
        workspace=str(args.workspace.resolve()),source_root=str(Path(workbench.__file__).resolve().parents[1]),
        runtime_source=runtime.__file__,ledger_source=str(HOST_DURABLE),
        fixture='DETERMINISTIC_TRANSPORT_NOT_LIVE_API'),indent=2),encoding='utf-8')
    save_state()
    try:server.serve_forever()
    finally:server.server_close();save_state()


if __name__=='__main__':main()
