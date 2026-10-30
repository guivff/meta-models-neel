"""Operational device binding; the frozen Oracle native method is inherited unchanged."""
def check_device(gpu_type):
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or gpu_type not in torch.cuda.get_device_name(0):
        raise ValueError('Assigned single H200/B200 required')
    return dict(gpu_type=gpu_type,actual_gpu_name=torch.cuda.get_device_name(0),torch=torch.__version__)


def load_b200(backend):
    from projects.g_agreement.e97.hardware import load_b200 as original_loader
    original_loader(backend)


def smoke(backend,inputs,out,write):
    from projects.g_agreement.e97.hardware import smoke as original_smoke
    original_smoke(backend,'oracle',inputs,out,write)


def backend(module,root,assets,assignment,inputs,out,write):
    gpu=assignment.get('gpu_type')
    if gpu not in ('H200','B200') or assignment.get('analysis_unit_gpu_types')!={'E79_extension':gpu}:
        raise ValueError('One assigned GPU type for all real/control units')
    if gpu=='B200':
        import hashlib
        refs=assignment.get('hardware_reference_files',{})
        if inputs is None or set(refs)!={'SMOKE_oracle.json','SMOKE_oracle.npy'}:
            raise ValueError('B200 requires sealed three-item H200 references')
        for name,digest in refs.items():
            if hashlib.sha256((inputs/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Sealed H200 smoke fixture changed')
    class Bound(module.Backend):
        def load_oracle(self):
            hardware=check_device(gpu)
            if gpu=='B200':load_b200(self)
            else:super().load_oracle()
            write(out/'HARDWARE.json',hardware)
            if gpu=='B200':smoke(self,inputs,out,write)
    return Bound(root,assets,{'gpu_type':gpu})
