"""Import-name shim only; upstream test_gate.py bytes remain unchanged."""
import sys, types
from catalyst_platform._vendor.skillopt_sleep import gate
for name in ('skillopt','skillopt.evaluation'):
    module=types.ModuleType(name);module.__path__=[];sys.modules[name]=module
sys.modules['skillopt.evaluation.gate']=gate
