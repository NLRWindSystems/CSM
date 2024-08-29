from pathlib import Path

from csm.csm import CSM
from csm.run import run_parameter_config
from csm.util import import_model


__all__ = ["CSM", "run_parameter_config"]

# dynamically import all models in the "model" directory
# assumes the class name and file name are the same
# This is not pretty and I don't like it
parent_dir = Path(__file__).parent / "model"
for p in parent_dir.glob("[!__]*[!__].py"):
    globals()[p.stem] = import_model(p.stem, parent_dir)
