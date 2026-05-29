"""Automatically Generated WISDEM interface for the user-defined CSM implementation."""

import openmdao.api as om
from attrs import fields

from csm.base_model import CSMBase


model_map = {
    "CSMBase": CSMBase,
}


class WisdemCSM(om.Group):
    """Basic ``Group`` model to create the CSM interface."""

    def initialize(self):
        """Initializes the CSM ``Group`` model to create the CSM interface."""
        self.options.declare("model", default="CSMBase")

    def setup(self):
        """Sets up the CSM ``Group`` model to create the CSM interface."""
        self.add_subsystem("csm", WisdemCSMBase(model=self.options["model"]), promotes=["*"])


class WisdemCSMBase(om.ExplicitComponent):
    """CSM ``ExplicitComponent`` for the WISDEM interface capable of setting up the expected
    inputs and outputs based on the user-defined :py:attr:`model`.
    """

    def setup(self):
        """Sets up the ``ExplicitComponent`` model for the CSM."""
        self.options.declare("model", default="CSMBase")
        self.csm_model = model_map[self.options["model"]]

        for f in fields(self.csm_model):
            meta = f.metadata
            if (_io := meta.get("io")) is not None:
                name = f.name
                default = f.default
                match _io:
                    case "input":
                        self.add_input(name, default, units=meta["units"])
                    case "output":
                        self.add_output(name, default, units=meta["units"])
                    case "both":
                        self.add_input(name, default, units=meta["units"])
                        self.add_output(name, default, units=meta["units"])

    def compute(self, inputs, outputs, discrete_inputs=None, discrete_outputs=None):
        """Runs the ``ExplicitComponent.compute()`` method after custom setup."""
        self.model = self.csm_model(**inputs)
        self.model.run()
        outputs |= self.model.get_results()
