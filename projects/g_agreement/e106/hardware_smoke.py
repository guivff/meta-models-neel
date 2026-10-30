"""Read-only finite-logit observer for the registered B200 sealed readout smoke."""
class FiniteLogits:
    def __init__(self,model):self.model=model.get_base_model() if callable(getattr(model,"get_base_model",None)) else model;self.calls=0;self.finite=None
    def __enter__(self):
        import torch
        def observe(module,inputs,output):
            logits=getattr(output,'logits',None)
            if logits is None:raise RuntimeError('B200 model smoke requires actual logits')
            flag=torch.isfinite(logits).all()
            self.finite=flag if self.finite is None else self.finite & flag;self.calls+=1
            # No return: never replace/modify model outputs.
        self.handle=self.model.register_forward_hook(observe);return self
    def __exit__(self,*args):self.handle.remove()
    def receipt(self):
        if not self.calls or self.finite is None or not bool(self.finite):raise RuntimeError('B200 sealed greedy smoke missing/nonfinite logits')
        return {'forward_calls':self.calls,'all_logits_finite':True,'read_only_observer':True}
