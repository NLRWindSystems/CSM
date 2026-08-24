from csm.models.nlr2015 import Land2015NLR
from csm.models.nlr2020 import Land2020NLR
from csm.models.nlr2021 import Land2021NLR
from csm.models.base_model import CSMBase


__all__ = ["CSM", "run_config"]
__version__ = "0.1"


def get_model(name: str | int) -> type[CSMBase]:
    """Retrieves the desired model class based on the model name or alias :py:attr:`name`.

    Args:
        name (str | int): A model name or valid alias for a model. Aliases are as follows:

            - :py:class:`CSMBase`: "base", "CSMBase"
            - :py:class:`Land2015NLR`: "2015", 2015, "nlr2015", "land2015", "Land2015NLR"

    Raises:
        NotImplementedError: Raised if :py:attr:`name` is an invalid model name or alias.

    Returns:
        Type[CSMBase]: The ``CSMBase`` model or one of its subclasses.
    """
    match name:
        case "base" | "CSMBase":
            return CSMBase
        case "2015" | 2015 | "land-2015" | "Land2015NLR" | "nlr-2015":
            return Land2015NLR
        case "2020" | 2020 | "land-2020" | "Land2020NLR" | "nlr-2020":
            return Land2020NLR
        case "2021" | 2021 | "land-2021" | "Land2021NLR" | "nlr-2021":
            return Land2021NLR
        case _:
            raise NotImplementedError(f"'{name}' is invalid.")
