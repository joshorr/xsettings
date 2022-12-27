import os
from decimal import Decimal
from enum import Enum
import datetime as dt
from typing import Any

import pytest
from xsentinels import Default

from xsettings.env_settings import EnvSettings
from xsettings.fields import SettingsConversionError
from xsettings.settings import Settings, SettingsField, SettingsValueError, SettingsRetriever
from xsettings.settings import PropertyRetriever


def test_set_default_value_after_settings_subclass_created():
    class MySettings(Settings):
        my_str: str

    my_settings = MySettings.proxy()

    with pytest.raises(SettingsValueError, match=r'Missing value.+my_str.+MySettings'):
        v = my_settings.my_str

    MySettings.my_str = 'default-value'
    assert my_settings.my_str == 'default-value'

    class OtherSettings(Settings):
        other_str: str

    MySettings.my_str = OtherSettings.other_str
    with pytest.raises(SettingsValueError, match=r'Missing value.+other_str.+OtherSettings'):
        v = my_settings.my_str

    OtherSettings.grab().other_str = 'my-setting'
    assert my_settings.my_str == 'my-setting'


def test_use_property_on_settings_subclass():
    value_to_retrieve = "RetrievedValue"

    class MyRetriever(SettingsRetriever):
        def retrieve_value(self, field: SettingsField) -> Any:
            nonlocal value_to_retrieve
            return value_to_retrieve

    class MyForwardSettings(Settings):
        my_forwarded_field: str = "my_forwarded_field-value"

    class MySettings(Settings, default_retriever=MyRetriever()):
        my_field = "my_field-value"

        @property
        def my_prop(self) -> str:
            return "my_prop-a-value"

        @property
        def another_prop(self) -> str:
            return "another_prop-value"

        my_field_with_default_as_prop: str = SettingsField(default_value=another_prop)
        forwarded: str = MyForwardSettings.my_forwarded_field

    my_settings = MySettings.grab()
    assert my_settings.my_prop == 'my_prop-a-value'
    assert my_settings.my_field == 'RetrievedValue'
    assert my_settings.my_field_with_default_as_prop == 'RetrievedValue'
    assert my_settings.forwarded == 'RetrievedValue'

    # When the retriever can't retrieve the value, should fall back to the default values
    value_to_retrieve = None
    assert my_settings.my_field == 'my_field-value'
    assert my_settings.my_field_with_default_as_prop == 'another_prop-value'
    assert my_settings.forwarded == 'my_forwarded_field-value'

    # Should work regardless if there is a retreived value or not.
    assert my_settings.my_prop == 'my_prop-a-value'


def test_default_converters():
    def my_converter(value):
        return Decimal(1.654)

    class MySettings(Settings):
        my_bool: bool
        my_date: dt.date = "2023-03-04"
        my_datetime: dt.datetime = "2020-01-09T12:00:02"
        my_decimal: Decimal
        my_custom_converter: Decimal = SettingsField(converter=my_converter)

    my_settings = MySettings.proxy()

    my_settings.my_bool = "false"
    my_settings.my_decimal = "542.32"
    my_settings.my_custom_converter = "542.32"

    assert my_settings.my_bool is False
    assert my_settings.my_date == dt.date(2023, 3, 4)
    assert my_settings.my_datetime == dt.datetime(2020, 1, 9, 12, 0, 2)
    assert my_settings.my_decimal == Decimal("542.32")
    assert my_settings.my_custom_converter == Decimal(1.654)


def test_defaults():
    class MySettings(Settings):
        no_default: int
        default_convert_str_to_int: int = "3"
        default_no_conversion_needed: int = 6
        default_no_type_hint = 4
        not_required: int = SettingsField(required=False)
        default_convert_str_to_decimal: str = SettingsField(default_value=5, converter=Decimal)

    my_settings = MySettings()
    with pytest.raises(SettingsValueError) as error_info:
        my_settings.no_default
    assert "Missing value for SettingsField(name='no_default" in error_info.value.args[0]
    assert my_settings.default_convert_str_to_int == 3
    assert my_settings.default_no_conversion_needed == 6
    assert my_settings.default_no_type_hint == 4
    assert my_settings.not_required is None
    assert my_settings.default_convert_str_to_decimal == Decimal("5")


def test_conversion_returns_none():
    class MySettings(Settings):
        requried: str = SettingsField(default_value=3, converter=lambda x: None)
        not_requried: str = SettingsField(
            default_value=3, converter=lambda x: None, required=False
        )

    my_settings = MySettings()
    assert my_settings.not_requried is None
    with pytest.raises(SettingsConversionError, match='After converting value'):
        my_settings.requried  # noqa


def test_enum():
    class MyEnum(Enum):
        FIVE = 5
        SIX = 6

    class MySettings(Settings):
        enum: MyEnum
        enum2: MyEnum = SettingsField(converter=MyEnum)

    my_settings = MySettings()
    my_settings.enum = 5
    my_settings.enum2 = 6
    assert my_settings.enum == MyEnum.FIVE
    assert my_settings.enum2 == MyEnum.SIX


def test_field_in_class_reuse():
    class MySettings(Settings):
        a: int = 1

    class MyClass:
        my_var = MySettings.a

    assert MyClass.my_var == 1
    assert MyClass().my_var == 1


def test_field_overwriting():
    class MySettings(Settings):
        a: str

    class MyEnvSettings(EnvSettings):
        b: int

    my_settings = MySettings.grab()
    my_env_settings = MyEnvSettings.grab()
    with pytest.raises(SettingsValueError):
        my_env_settings.b
    with pytest.raises(SettingsValueError):
        my_settings.a

    os.environ['b'] = "5"

    assert 5 == my_env_settings.b
    with pytest.raises(SettingsValueError):
        my_settings.a

    my_settings.a = MyEnvSettings.b

    assert my_env_settings.b == 5
    assert my_settings.a == "5"

    os.environ['b'] = "6"

    assert my_env_settings.b == 6
    assert my_settings.a == "6"


def test_field_overwriting_classlevel():
    os.environ.pop("b", None)

    class KevinEnvSettings(EnvSettings):
        b: int

    class KevinSettings(Settings):
        a: str = KevinEnvSettings.b

    my_env_settings = KevinEnvSettings.grab()
    my_settings = KevinSettings.grab()
    with pytest.raises(SettingsValueError):
        my_env_settings.b
    with pytest.raises(SettingsValueError):
        my_settings.a

    os.environ['b'] = "5"

    assert my_env_settings.b == 5
    assert my_settings.a == "5"


def test_class_field_overwrite():
    class MySettings(Settings):
        a: str

    with pytest.raises(AttributeError):
        MySettings.b = 3


def test_settings_inheritance_not_allowed():
    class MySettings(Settings):
        a: int

    with pytest.raises(AssertionError):
        class MySubSettings(MySettings):
            b: int


def test_property_as_forward_ref_works_via_return_type():
    did_call_property = False

    class ASettings(Settings):
        other_setting = 3

        @property
        def prop_to_forward_ref(self) -> str:
            nonlocal did_call_property
            did_call_property = True
            assert isinstance(self, ASettings)
            return self.other_setting

    class BSettings(Settings):
        b_settings_forward_from_a: Decimal = ASettings.prop_to_forward_ref

    assert ASettings.grab().other_setting == 3
    assert did_call_property is False
    did_call_property = False

    assert ASettings.grab().prop_to_forward_ref == '3'
    assert did_call_property is True
    did_call_property = False

    assert BSettings.grab().b_settings_forward_from_a == Decimal('3')
    assert did_call_property is True
    did_call_property = False

    field = ASettings._setting_fields['prop_to_forward_ref']
    assert field.type_hint is str
    assert field.name == 'prop_to_forward_ref'
    assert isinstance(field.retriever, PropertyRetriever)


def test_property_as_forward_ref_works_via_annotation():
    did_call_property = False

    class AProperty:
        # Defining it here so it's easy to get a refrence back to the orginal property object.
        @property
        def prop_to_forward_ref(self):
            nonlocal did_call_property
            did_call_property = True
            assert isinstance(self, ASettings)
            return self.other_setting

    class ASettings(Settings):
        other_setting = 3

        # Also testing if annotation if defined separately still works vs a property/default-value.
        prop_to_forward_ref = AProperty.prop_to_forward_ref
        prop_to_forward_ref: str

    class BSettings(Settings):
        b_settings_forward_from_a: Decimal = ASettings.prop_to_forward_ref

    assert ASettings.grab().other_setting == 3
    assert did_call_property is False
    did_call_property = False

    assert ASettings.grab().prop_to_forward_ref == '3'
    assert did_call_property is True
    did_call_property = False

    assert BSettings.grab().b_settings_forward_from_a == Decimal('3')
    assert did_call_property is True
    did_call_property = False

    field = ASettings._setting_fields['prop_to_forward_ref']
    assert field.type_hint is str
    assert field.name == 'prop_to_forward_ref'
    assert isinstance(field.retriever, PropertyRetriever)
    assert isinstance(field.retriever.property_retriever, property)
    assert field.retriever.property_retriever is AProperty.prop_to_forward_ref
    assert field.default_value is None


def test_property_field_detects_no_type_hint():
    with pytest.raises(AssertionError, match='Must have type-hint for field'):
        class ASettings(Settings):
            # We specify no type-annotation or return-type for property,
            # we should get an error while class is being constructed.
            @property
            def prop_to_forward_ref(self):
                pass


def test_property_field_detects_setter_being_used():
    with pytest.raises(AssertionError, match='You can only use read-only properties'):
        class ASettings(Settings):
            @property
            def random_property_field(self):
                return None

            # Right now we don't support setter property fields.
            # We COULD support them without too much effort, but it's some for a future feature.
            @random_property_field.setter
            def random_property_field(self, value):
                pass

            random_property_field: str


def test_settings_inheritance_without_fields_allowed():
    class MySettings(Settings):
        # Methods don't have fields generated for them.
        def test_method(self) -> int:
            return 1

        # staticmethod don't have fields generated for them.
        @staticmethod
        def static_method() -> int:
            return 5

        # classmethod don't have fields generated for them.
        @classmethod
        def class_method(cls) -> int:
            assert cls is MySettings
            return 4

        # This is a callable/method and so won't have a field generated for it.
        test_lambda = lambda x: 3

        # Private properties should not have a field generated for them!!!
        _private_property = 6

    class MySubSettings(MySettings):
        b: int

    sub_settings = MySubSettings()

    assert len(MySettings._setting_fields) == 0

    assert len(MySubSettings._setting_fields) == 1
    assert MySubSettings._setting_fields['b'].name == 'b'

    assert sub_settings.test_method() == 1
    assert sub_settings.test_lambda() == 3
    assert MySettings.class_method() == 4
    assert MySettings.static_method() == 5
    assert MySettings._private_property == 6


def test_source_class():
    class MySettings(Settings):
        a: int

    field: SettingsField = MySettings._setting_fields["a"]
    assert field.source_class == MySettings


def test_new_fields():
    class MySettings(Settings):
        a: int

    my_settings = MySettings()

    with pytest.raises(AttributeError):
        my_settings.other

    my_settings.other = 5
    assert my_settings.other == 5

    field = SettingsField(default_value=3)
    my_settings.other = field
    assert my_settings.other == field


def test_property_that_returns_diffrent_type():
    class MySettings(Settings):
        # Does not matter if this is before or after the property,
        # Python stores type annotations in a separate area vs normal class attribute values in
        # Python.
        some_setting: Decimal

        @property
        def some_setting(self):
            return "1.34"

    assert MySettings.grab().some_setting == Decimal("1.34")


def test_property_with_custom_field():
    class MySettings(Settings):
        # Does not matter if this is before or after the property,
        # Python stores type annotations in a separate area vs normal class attribute values in
        # Python.
        some_setting: str = SettingsField(required=False)

        @some_setting.getter
        def some_setting(self):
            return "1.36"

    assert MySettings.grab().some_setting == "1.36"


def test_converter_error_has_good_message():
    class TestSettings(Settings):
        # Default value is a blank string (can't convert to int directly).
        some_int_setting: int = ''

    with pytest.raises(
        SettingsConversionError, match="While attempting to convert value.*name='some_int_setting'"
    ):
        my_int = TestSettings.grab().some_int_setting


def test_super_class_with_default_value_uses_retriever():
    class PlainInterface:
        # Define an attribute with `Default`
        some_default_attr = Default

        # Define an attribute with some other value:
        some_other_attr = True

    class PlainSettings(Settings):
        str_attr: str = "my-str"
        bool_attr: bool = False

    class MySettings(Settings, PlainInterface):
        # Make them fields in our Settings subclass, default value to another settings class.
        some_default_attr: str = PlainSettings.str_attr
        some_other_attr: bool = PlainSettings.bool_attr

    my_settings = MySettings.grab()

    # The `Default` value in super-class will inform settings to attempt to retrieve the value,
    # and resolve the 'default' nature of it.
    assert my_settings.some_default_attr == 'my-str'

    # todo: May create a v2 of xyn-settings someday that will look at attributes directly assigned
    #   to self, then and retrieved value, then any plain super-class set value.
    #   For now, we treat all super-class values on attributes as-if  they were directly assigned
    #   to the settings instance; ie: we will NOT try to 'retrieve' the value unless the value is
    #   set to `Default` in either the instance or superclass (whatever value it finds via normal
    #   python attribute retrieval rules).

    # Super class has an explicit value, so that is what is used over any retrieved/default value.
    assert my_settings.some_other_attr is True
