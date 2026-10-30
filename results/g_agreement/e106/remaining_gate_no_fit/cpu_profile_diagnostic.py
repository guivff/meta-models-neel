import sys,threading,torch
from projects.g_agreement.e106.dispatch_proof import CallProof

def target(x):return x*2
wrapped=torch.compiler.disable(target)
class F(torch.autograd.Function):
 @staticmethod
 def forward(ctx,x):return x.clone()
 @staticmethod
 def backward(ctx,g):return wrapped(g)
x=torch.ones(3,requires_grad=True)
with CallProof(target,{'status':'CPU_SYNTHETIC'}) as p:
 F.apply(x).sum().backward()
print('Torch',torch.__version__,'PROFILER_CALLS',p.calls)
seen=[]
sys.monitoring.use_tool_id(3,'E106 CPU proof')
sys.monitoring.register_callback(3,sys.monitoring.events.PY_START,lambda code,offset:seen.append(code.co_name) if code is target.__code__ else None)
sys.monitoring.set_local_events(3,target.__code__,sys.monitoring.events.PY_START)
F.apply(x).sum().backward()
sys.monitoring.free_tool_id(3)
print('PEP669_CALLS',seen)
