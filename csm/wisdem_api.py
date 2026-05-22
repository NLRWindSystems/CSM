import openmdao.api as om

from csm import CSMBase

model_map = {
    "CSMBase": CSMBase,
}

class WisdemCSM(om.Group):
    def initialize(self):
        self.options.declare("model", default="CSMBase")
    
    def setup(self):
        self.add_subsystem("csm", WisdemCSMBase(model=self.options["model"]), promotes=["*"])

class WisdemCSMBase(om.ExplicitComponent):
    def setup(self):
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
                    case "both"
                        self.add_input(name, default, units=meta["units"])
                        self.add_output(name, default, units=meta["units"])

    def compute(self, inputs, outputs):
        self.model = self.csm_model(**inputs)
        self.model.run()
        outputs |= self.model.get_results()