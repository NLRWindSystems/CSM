from csm.models import CSMBase, Land2015NLR, Land2020NLR, Land2021NLR, available_models


__version__ = "0.0.1"


def get_model(name: str | int) -> type[CSMBase]:
    """Retrieves the desired model class based on the model name or alias :py:attr:`name`.

    Args:
        name (str | int): A model name or valid alias for a model. Aliases are as follows:

            - :py:class:`CSMBase`: "base", "CSMBase"
            - :py:class:`Land2015NLR`: "2015", 2015, "nlr2015", "land2015", "Land2015NLR", "NLR 2015"
            - :py:class:`Land2020NLR`: "2020", 2020, "nlr2020", "land2020", "Land2020NLR", "NLR 2020"
            - :py:class:`Land2021NLR`: "2021", 2021, "nlr2021", "land2021", "Land2021NLR", "NLR 2021"

    Raises:
        NotImplementedError: Raised if :py:attr:`name` is an invalid model name or alias.

    Returns:
        Type[CSMBase]: The ``CSMBase`` model or one of its subclasses.
    """
    match name:
        case "base" | "CSMBase":
            return CSMBase
        case "2015" | 2015 | "land-2015" | "Land2015NLR" | "nlr-2015" | "NLR 2015":
            return Land2015NLR
        case "2020" | 2020 | "land-2020" | "Land2020NLR" | "nlr-2020" | "NLR 2020":
            return Land2020NLR
        case "2021" | 2021 | "land-2021" | "Land2021NLR" | "nlr-2021" | "NLR 2021":
            return Land2021NLR
        case _:
            raise NotImplementedError(f"'{name}' is invalid, use one of: {available_models}.")
