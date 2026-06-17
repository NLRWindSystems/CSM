"""Provides all the ``attrs``-based utilities for the CSM base model and its subclasses."""

from typing import Any

from attrs import Attribute, field, converters, validators
from attr._make import attrib


def create_field(
    obj: type, units: str = "unitless", io_type: str = "input", *, default: int | None = None
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
        default (int, optional):  Value of the default, if not None. Should be used sparingly.

    Returns:
        attrs.field:
            Creates an :py:attr:`attrs.field` object for the attribute.

    Raises:
        NotImplementedError:
            Raised if an unsupported type object is passed. Only ``int``, ``float``, and ``bool``
            are accepted at this time.
    """
    if obj is int:
        _field = field(
            default=None,
            validator=validators.optional(validators.instance_of(int)),
            metadata={"units": units, "io": io_type},
        )
        return _field
    if obj is float:
        _field = field(
            default=None,
            converter=converters.optional(float),
            validator=validators.optional(validators.instance_of(float)),
            metadata={"units": units, "io": io_type},
        )
        return _field
    if obj is bool:
        _field = field(
            default=None,
            validator=validators.optional(validators.instance_of(bool)),
            metadata={"units": units, "io": io_type},
        )
        return _field
    raise NotImplementedError(f"No setup created for type: {obj}")


def reuse(attribute: Attribute, default: Any, *, init: bool | None = None) -> attrib:
    """Reuses an existing :py:attr:`attrs.Attribute` object with an updated default value.

    Borrowed idea from https://github.com/python-attrs/attrs/pull/1429 until the functionality
    is fully integrated.

    Args:
        attribute (:py:attr:`attrs.Attribute`): The attribute to modify.
        default (Any): The new default value.
        init (bool | None): Custom value for the `init` attribute, if modification is desired. If
            None, then the existing value for the :py:attr:`attribute` will be used.
            Defaults to False.

    Returns:
        attrib: The new attribute object used in class initialization.
    """
    kwargs = {
        "default": default,
        # "factory": attribute.default.factory,
        "converter": attribute.converter,
        "validator": attribute.validator,
        "metadata": attribute.metadata,
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
