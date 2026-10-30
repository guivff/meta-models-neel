import ast
from pathlib import Path
import pytest

def test_only_fixed_experiment_identifier_exempted():
    path=Path(__file__).with_name('operator_assignment.py')
    fn=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='validate_placeholders')
    env={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),env)
    check=env['validate_placeholders'];spec={'assignment_schema':{'experiment':'E97_CAPTURE_V2'}}
    check({'experiment':'E97_CAPTURE_V2','pod_id':'abc123'},spec)
    for bad in [{'experiment':'OTHER_EXPERIMENT'},{'experiment':'E97_CAPTURE_V2','pod_id':'POD_ID'}]:
        with pytest.raises(AssertionError):check(bad,spec)
