"""Provides all the ``attrs``-based utilities for the CSM base model and its subclasses."""

from typing import Any
from functools import partial

from attrs import Attribute, field, converters, validators
from attr._make import attrib


def convert_if_allowable_type(value: Any, target: type, allowable: type | tuple[type]) -> Any:
    """Converts the type of :py:attr:`value` to the :py:attr:`target` type if it is one of an
    :py:attr:`allowable` type. If :py:attr:`value` is already the correct type, or is not of an
    :py:attr:`allowable` type for conversion, the :py:attr:`value` will be returned unmodified.

    Args:
        value (Any): User input field value.
        target (type): The type the :py:attr:`value` should be converted to if it is not already
            of that type.
        allowable (type | tuple[type]): The allowable type(s) for conversion, i.e., ``(str, int)``
            for a target type of ``float``.

    Returns:
        Any: The original :py:attr:`value` or a converted :py:attr:`value` of type
        :py:attr:`target`.
    """
    if isinstance(value, target) or not isinstance(value, allowable):
        return value
    return target(value)


convert_float = partial(convert_if_allowable_type, target=float, allowable=(int, str))


def create_field(
    obj: type,
    units: str = "unitless",
    io_type: str = "input",
    *,
    default: int | float | bool | None = None,
    additional_validators: list[callable] | None = None,
    additional_converters: list[callable] | None = None,
    **kwargs,
) -> field:
    """Creates an :py:attr:`obj`-based field with pre-loaded defaults, conversions, validations,
    and metadata.

    Args:
        obj (type): A type. Currently only accepts ``int``, ``float``, or ``bool``.
        units (str, optional): OpenMDAO-compatible units. See
            <https://openmdao.org/newdocs/versions/latest/features/units.html> for more details.
            Defaults to "unitless".
        io_type (str, optional): One of "input", "output", or "both" for how the attribute should be
            initialized within a WISDEM model. Typically ``xx_mass` and ``xx_cost`` attributes
            are both inputs and outputs. Defaults to "input".
        default (int | float | bool, optional): Value of the default, if not None.
        additional_validators (list[callable], optional): A list of additional validator functions
            to attach to the ``attrs.field`` initialization. Defaults to None
        additional_converters (list[callable], optional): A list of additional converter functions
            to attach to the ``attrs.field`` initialization. Defaults to None
        kwargs (dict[str, Any], optional): Additional parameterizations to pass to ``attrs.field``.

    Returns:
        attrs.field:
            Creates an :py:attr:`attrs.field` object for the attribute.

    Raises:
        NotImplementedError:
            Raised if an unsupported type object is passed. Only ``int``, ``float``, and ``bool``
            are accepted at this time.
    """
    io_types = ("input", "output", "both")
    if not isinstance(io_type, str):
        raise TypeError("`io_type` must be a `str` and one of 'input', 'output', or 'both'.")
    io_type = io_type.lower()
    if io_type not in io_types:
        raise ValueError("`io_type` must be one of 'input', 'output', or 'both'.")

    _converters = None
    if additional_converters is not None:
        _converters = [converters.optional(el) for el in additional_converters]

    _validators = [validators.optional(validators.instance_of(obj))]
    if additional_validators is not None:
        _validators += [validators.optional(el) for el in additional_validators]

    if obj is int:
        pass
    elif obj is float:
        if _converters is None:
            _converters = []
        _converters = [converters.optional(convert_float), *_converters]
    elif obj is bool:
        if _converters is None:
            _converters = []
        _converters = [converters.optional(converters.to_bool), *_converters]
    else:
        raise NotImplementedError(f"No setup created for type: {obj}")

    _field = field(
        default=default,
        converter=_converters,
        validator=_validators,
        metadata={"units": units, "io": io_type},
        **kwargs,
    )
    return _field


def reuse(
    attribute: Attribute,
    *,
    default: Any = None,
    metadata: dict | None = None,
    init: bool | None = None,
) -> attrib:
    """Reuses an existing :py:attr:`attrs.Attribute` object with an updated default value.

    Borrowed idea from https://github.com/python-attrs/attrs/pull/1429 until the functionality
    is fully integrated.

    Args:
        attribute (:py:attr:`attrs.Attribute`): The attribute to modify.
        default (Any, optional): The new default value.
        metadata (None, optional): Updated metadata dictionary to change attributes such as
            "units" or "io". Defaults to None.
        init (bool | None): Custom value for the `init` attribute, if modification is desired. If
            None, then the existing value for the :py:attr:`attribute` will be used.
            Defaults to False.

    Returns:
        attrib: The new attribute object used in class initialization.
    """
    attribute_metadata = dict(attribute.metadata)
    attribute_metadata.update(metadata if metadata is not None else {})

    # NOTE: if adding factory, then only one of default or factory can be used.
    kwargs = {
        "default": attribute.default if default is None else default,
        "converter": attribute.converter,
        "validator": attribute.validator,
        "metadata": attribute_metadata,
        "repr": attribute.repr,
        "cmp": None,
        "hash": attribute.hash,
        "init": attribute.init if init is None else init,
        "type": attribute.type,
        "kw_only": attribute.kw_only,
        "eq": attribute.eq,
        "order": attribute.order,
        "on_setattr": attribute.on_setattr,
        "alias": attribute.alias,
    }
    return attrib(**kwargs)


Attribute.reuse = reuse
