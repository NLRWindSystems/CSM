from pathlib import Path

from csm.csm import CSM
from csm.run import run_parameter_config
from csm.util import import_model


parent_dir = Path(__file__).parent / "model"
for p in parent_dir.glob("[!__]*[!__].py"):
    globals()[p.stem] = import_model(p.stem, parent_dir)


__all__ = ["CSM", "run_parameter_config"]
