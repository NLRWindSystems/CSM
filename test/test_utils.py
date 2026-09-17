import pytest
from attrs import define, fields, validators
from attr._make import _CountingAttr

from csm.models.utils import reuse, create_field, convert_if_allowable_type


@pytest.mark.unit
def test_convert_if_allowable_type(subtests):
    """Tests ``convert_if_allowable_type`` conversion helper."""
    with subtests.test("Float validation with no alternate allowed types"):
        val = 1
        res = convert_if_allowable_type(value=val, target=float, allowable=float)
        assert isinstance(res, int) and res == val

        val = "1"
        res = convert_if_allowable_type(value=val, target=float, allowable=float)
        assert isinstance(res, str) and res == val

        val = True
        res = convert_if_allowable_type(value=val, target=float, allowable=float)
        assert isinstance(res, bool) and res

    with subtests.test("Float validation with int allowed"):
        val = 1
        res = convert_if_allowable_type(value=val, target=float, allowable=int)
        assert isinstance(res, float) and res == val

    with subtests.test("Float validation with int allowed and bool value"):
        val = True
        res = convert_if_allowable_type(value=val, target=float, allowable=(int))
        assert isinstance(res, float) and res == 1.0

    with subtests.test("Int validation with no alternate allowed types"):
        val = 1.0
        res = convert_if_allowable_type(value=val, target=int, allowable=int)
        assert isinstance(res, float) and res == val

        val = True
        res = convert_if_allowable_type(value=val, target=int, allowable=int)
        assert isinstance(res, bool) and res

    with subtests.test("Int validation with int allowed and bool value"):
        val = True
        res = convert_if_allowable_type(value=val, target=int, allowable=(int))
        assert isinstance(res, int) and res == 1

    with subtests.test("Bool validation and float value"):
        val = 1.0
        res = convert_if_allowable_type(value=val, target=bool, allowable=(bool))
        assert isinstance(res, float) and res == 1.0

    with subtests.test("Bool validation and str value"):
        val = "1"
        res = convert_if_allowable_type(value=val, target=bool, allowable=(bool))
        assert isinstance(res, str) and res == "1"


def demo_converter(value: float) -> float:
    """Sample converter for a float field to ensure the additional converters are passed
    through correctly.
    """
    return value * 0.25


@define
class Demo:
    simple_int = create_field(int)
    simple_float = create_field(float)
    simple_bool = create_field(bool)
    converted_int = create_field(int, additional_converters=[int])
    converted_float = create_field(float, additional_converters=[demo_converter])
    limited_float = create_field(float, additional_validators=[validators.ge(0), validators.le(1)])
    output_float = create_field(float, io_type="output")
    both_float_units = create_field(float, units="kg", io_type="both")


@pytest.mark.unit
def test_create_field(subtests):
    """Test the ``create_field`` functionality``."""
    with subtests.test("Test input `obj` types"):
        with pytest.raises(NotImplementedError):
            create_field(dict)
        with pytest.raises(NotImplementedError):
            create_field(set)
        with pytest.raises(NotImplementedError):
            create_field(list)
        with pytest.raises(NotImplementedError):
            create_field(tuple)
        with pytest.raises(NotImplementedError):
            create_field(range)
        with pytest.raises(NotImplementedError):
            create_field(complex)
        assert isinstance(create_field(int), _CountingAttr)
        assert isinstance(create_field(float), _CountingAttr)
        assert isinstance(create_field(bool), _CountingAttr)

    with subtests.test("Test input `io_type` values"):
        with pytest.raises(TypeError):
            create_field(float, io_type=float)
        with pytest.raises(TypeError):
            create_field(float, io_type=("input", "output"))
        with pytest.raises(ValueError):
            create_field(float, io_type="inputs")
        with pytest.raises(ValueError):
            create_field(float, io_type="outputs")
        with pytest.raises(ValueError):
            create_field(float, io_type=" output")

        assert isinstance(create_field(float, io_type="input"), _CountingAttr)
        assert isinstance(create_field(float, io_type="OUTPUT"), _CountingAttr)
        assert isinstance(create_field(float, io_type="bOth"), _CountingAttr)

    with subtests.test("Check demo defaults "):
        model = Demo()
        assert model.simple_int is None
        assert model.simple_float is None
        assert model.simple_bool is None
        assert model.limited_float is None
        assert model.converted_int is None
        assert model.converted_float is None

        demo_fields = fields(Demo)
        assert demo_fields.simple_int.metadata["units"] == "unitless"
        assert demo_fields.simple_float.metadata["units"] == "unitless"
        assert demo_fields.simple_bool.metadata["units"] == "unitless"
        assert demo_fields.limited_float.metadata["units"] == "unitless"
        assert demo_fields.output_float.metadata["units"] == "unitless"
        assert demo_fields.converted_int.metadata["units"] == "unitless"
        assert demo_fields.converted_float.metadata["units"] == "unitless"
        assert demo_fields.both_float_units.metadata["units"] == "kg"
        assert demo_fields.simple_int.metadata["io"] == "input"
        assert demo_fields.simple_float.metadata["io"] == "input"
        assert demo_fields.simple_bool.metadata["io"] == "input"
        assert demo_fields.limited_float.metadata["io"] == "input"
        assert demo_fields.converted_int.metadata["io"] == "input"
        assert demo_fields.converted_float.metadata["io"] == "input"
        assert demo_fields.output_float.metadata["io"] == "output"
        assert demo_fields.both_float_units.metadata["io"] == "both"

    with subtests.test("Check demo setup"):
        model = Demo(
            simple_int=1,
            simple_float=2,
            simple_bool=True,
            limited_float=0.5,
            converted_int=2.2,
            converted_float=12,
        )
        assert isinstance(model.simple_int, int)
        assert model.simple_int == 1
        assert isinstance(model.simple_float, float)
        assert model.simple_float == 2.0
        assert isinstance(model.simple_bool, bool)
        assert model.simple_bool
        assert isinstance(model.limited_float, float)
        assert model.limited_float == 0.5
        assert isinstance(model.converted_int, int)
        assert model.converted_int == 2
        assert isinstance(model.converted_float, float)
        assert model.converted_float == 3

        with pytest.raises(ValueError):
            model.limited_float = 1.000001
        with pytest.raises(ValueError):
            model.limited_float = -0.000001


@pytest.mark.unit
def test_reuse():
    """Test reuse of attributes in subclasses."""
    base = fields(Demo)

    @define
    class SubDemo:
        simple_int = reuse(base.simple_int, default=12)
        simple_float = reuse(base.simple_int, default=1.2, init=False)

    sub = fields(SubDemo)
    base_simple_int = base.simple_int
    sub_simple_int = sub.simple_int
    assert sub_simple_int.default == 12
    assert not sub.simple_float.init

    assert sub_simple_int.converter == base_simple_int.converter
    assert sub_simple_int.validator == base_simple_int.validator
    assert sub_simple_int.metadata == base_simple_int.metadata
    assert sub_simple_int.repr == base_simple_int.repr
    assert sub_simple_int.init == base_simple_int.init
    assert sub_simple_int.eq == base_simple_int.eq
    assert sub_simple_int.type == base_simple_int.type
    assert sub_simple_int.order == base_simple_int.order
    assert sub_simple_int.on_setattr == base_simple_int.on_setattr
    assert sub_simple_int.alias == base_simple_int.alias

    with pytest.raises(TypeError):
        SubDemo(simple_float=33.3)
