import dataclasses
from typing import Callable
from copy import copy
from typing import Type, Any, Dict, Generic, TypeVar, TYPE_CHECKING, get_type_hints
import typing_inspect

from .default_converters import DEFAULT_CONVERTERS
from xsentinels import unwrap_union, Default

try:
    import annotationlib
except ImportError:
    annotationlib = None

if TYPE_CHECKING:
    from .settings import BaseSettings
    from .retreivers import SettingsRetrieverProtocol

T = TypeVar("T")


# It's both an attribute and a value error
# (attribute is missing and/or value has some other issue)
# `AttributeError` helps pdoc3 know that there is no value safely
# (ie: it will continue to generate docs).
class SettingsConversionError(ValueError, AttributeError):
    pass


class SettingsClassProperty(Generic[T]):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls) -> T:
        return self.fget(owner_cls)


class _PropertyRetriever:
    """
    Special case, internally used retriever only assigned to individual fields
    (and not as a default retriever for the entire BaseSettings subclass).

    What is used to wrap a `@property` on a BaseSettings subclass.
    We don't use the default retriever for any defined properties on a BaseSettings subclass,
    we instead use `PropertyRetriever`; as the property it's self is considered the 'retriever'.

    Will check the property getter function to retrieve the value by calling its
    `__get__()` method, passing the settings object involved as the
    object/type the property is getting a value for; just like any other
    normal property would have happened when the value is asked for.
    """
    property_retriever: property

    def __init__(self, property_retriever: property):
        self.property_retriever = property_retriever

    def __call__(self, *, field: 'SettingsField', settings: 'BaseSettings') -> Any:
        return self.property_retriever.__get__(settings, type(settings))


@dataclasses.dataclass
class SettingsField:
    name: str = None
    """ Defaults to the attribute name, but you can override this to provide an alternate name
        to lookup the value with.

        Example Use Case:

        For plain BaseSettings classes, name is not really used.
        But it can be useful in custom/special retrievers.

        An example of such a one is ConfigSettings/ConfigRetriever.

        `xcon.config.ConfigSettings` uses a ConfigRetriever, which will use this name
        field attribute to retrieve a named values from`xcon.config.Config`.

        So you can override the name to tell ConfigSettings what name to use to retrieve value
        with.  Allows you to have an attribute name on your ConfigSettings class that
        is different then the one used to retrieve the values.
    """

    source_class: 'Type[BaseSettings]' = None
    """
    For debug purposes only. Will be set when the class level SettingsField is created. It is a
    way to get back to the source BaseSettings class.

    It's positioned just after `name` so it's printed earlier in a log-line.
    """

    source_name: str = dataclasses.field(default=None)
    """
    For debug purposes only. Will be overwritten when the class level SettingsField is created.
    It will be set to the name of the attribute on the settings class where it originated.

    It's positioned just after `source_class` so it's printed earlier in a log-line.
    """

    required: bool = None
    """
    By default settings are required, if a None would be returned we instead raise an exception.
    If `required` is set to False, a None will be returned instead of raising an exception.

    This here in the dataclass defaults to None so we can detect if user has set this or not.
    When fields are finalized into a BaseSettings subclass, and this is still a None,
    we will determine the `required` value like so:

    if field-type-hint is wrapped in an Optional, ie: `Optional[str]`,
    we will set `required = False`.

    If a field-type-hint is a Union with a None, ie: `Union[str, None]`,
    we will set `required = False`.

    Otherwise (the default), we will set `required = True`.
    """

    converter: Callable = None
    """Set from property.type_hint or from type(property.default_value) if type_hint is not
    specified. Used to convert retrieved values to a desired type. Only called if the retrieved
    value is not of type `type_hint`

    IE:
    >>> if not isinstance(value, type_hint):
    >>>    value = field.converter(value)
    """

    type_hint: Type = None
    """ Set from property.type_hint or from type(property.default_value) if type_hint is not
    specified. Used to determine if the converter should be called or not. If not set then the
    converter will always be called.
    """

    retriever: 'SettingsRetrieverProtocol' = None
    """
    Retriever callable to use to retrieve settings from some source.

    Can be any callable that follows the `xsettings.retriever.SettingsRetrieverProtocol` calling
    interface.

    System will try this retriever first (if set to something),
    before trying other retrievers such as instance-retrievers
    `xsettings.settings.BaseSettings.add_instance_retrievers`
    or default-retrievers `xsettings.settings.BaseSettings.__init_subclass__`.

    See those links for more details (such as how dependency-chain and mro parents are resolved
    when looking for other retrievers).

    Example:

    >>> class MySettings(default_retriever=MyRetriever())
    ...     my_field: str  # <-- will use `MyRetriever` instance for it's retriever
    """

    default_value: Any = None
    """
    This field settings defaults to whatever is assigned to the class-attribute:

    ```python
    class MySettings(BaseSettings):
         my_attribute_with_default_value: str = "some-default-value"
    ```

    The default_value is a fall-back value that is used as a last-restort if the setting is
    not set to anything and/or can't be retrieved.

    Used by `xsettings.retriever.SettingsRetrieverProtocol` and it's subclasses
    (such as ConfigRetriever from xcon).

    The default value can also be a property object
    (such as forward-reference from another BaseSettings class).

    If it's a property object, we will ask the object for it's property value and
    use that for the default-value when needed.
    """

    @property
    def getter(self):
        """
        Like the built-in `@property` of python, except you can also place a SettingsField and set
        any field-options you like, so it lets you make a SettingsField with custom options that
        also has a property attached.

        We place your function into a `property` object, and then place property object
        into the `SettingsField.retreiver` for you.

        Basically, used to easily set a retreiver property function on self via the standard
        property decorator syntax.

        See the [README's/Main-Module's Properties](./#properties) section for more details.
        But in summary, it works like normal python properties
        except that we currently put the property function into the `retreiver`
        SettingsField attribute instead of `fget`
        (normal Python `property` objects use the `fget` attribute to store the property function).

        Again, I would encourage you to read the [Properties](./#properties) section for
        more details.

        Property setters are currently unsupported (see Properties section/link above for
        more details on why). It's something we could support in the future if we wanted.

        For now, when someone sets a value on a property getter, we will store that as the
        settings field value and return that in the future
        (ie: overriding the retriever property method with a set value).

        You can define a property like normal, and Settings will create a default SettingsField
        object for it like you would expect.

        But, if you NEED to customize the Field object, this is where the `.getter` on
        SettingsField becomes handy.

        >>> class MySettings(BaseSettings):
        ...
        ...    # You can easily setup a field like normal, and then use getter to setup
        ...    # the getter function for the field.
        ...
        ...    my_field: str = SettingsField(required=False)
        ...
        ...    @my_field.getter
        ...    def my_field(self):
        ...         return 'some value'
        ...
        ...   # If you don't need any customization on the SettingsField,
        ...   # You can also just simply define a property like normal:
        ...   @property
        ...   def non_custom_field(self) -> int:
        ...       return 42
        """

        # We return a function, that is called by Python for us.
        # Python provides the original function as an argument.
        # Whatever we return from this internal method is what is left on
        # the class afterwards. In this case, the original SettingsField (self).
        def wrap_property_getter_func(func):
            wrapped_property = property(fget=func)
            self.retriever = _PropertyRetriever(wrapped_property)
            return self

        return wrap_property_getter_func

    def merge(self, override: "SettingsField"):
        if not override:
            # Nothing to merge in with...
            return

        self.required = override.required
        if override.name:
            self.name = override.name
        if override.converter:
            self.converter = override.converter
        if override.type_hint:
            self.type_hint = override.type_hint
        if override.retriever:
            self.retriever = override.retriever

        if override.default_value is not None:
            # Copy default value in case it's a mutable object, like a dict.
            self.default_value = copy(override.default_value)
        return self

    def retrieve_value(self, *, settings: 'BaseSettings'):
        """Convenience method for getting the value from the retriever."""
        return self.retriever(self, settings=settings)

    def convert_value(self, value):
        """
        Controls converting a value.

        To find a converter, we check these in order, first one found is what we use:

        1. We first check `self.converter`.
        2. Next, `xsettings.default_converters.DEFAULT_CONVERTERS`.
        3. Finally, we fall-back to using the type-hint (ie: `int(value)` or `str(value)`).

        Args:
            value: Value to be converted.
                Conversion is skipped if:

                - value is `None`.
                - `SettingsField.converter` is `None`.
                - value is of type `SettingsField.type_hint`.

                An error will be raised of conversion results in a `None` value and
                `SettingsField.required` is True.

        Returns: Converted Value
        """
        original_value = value

        # Check for a user-provided converter....
        converter = self.converter

        if not converter:
            converter = DEFAULT_CONVERTERS.get(self.type_hint, None)

            # If the value is still `Default`, we 'default' the value to `None`,
            # as our default converters or using the type-hint directly don't really
            # deal with `Default`.
            #
            # BUT we will let a user-provided converter get the `Default` value, so it
            # can decide on its own what to do with it.
            if value is Default:
                value = None

        if not converter:
            converter = self._get_default_converter()

        if converter and value is not None:
            hint = self._get_base_typehint()
            if not hint or not isinstance(value, hint):
                try:
                    value = converter(value)
                except Exception as e:
                    raise SettingsConversionError(
                        f'While attempting to convert value ({original_value}) '
                        f'via converter ({self.converter}), for field ({self}); '
                        f'we got an error ({e}).'
                    )

        # If the value is still `Default` at this point, we default it to `None`.
        if value is Default:
            value = None

        if value is None and original_value is not None and self.required:
            raise SettingsConversionError(
                f'After converting value ({original_value}) '
                f'via converter ({self.converter}), we got back a `None` value '
                f'for a required field ({self}).'
            )
        return value

    def _get_default_converter(self) -> Callable:
        hint = self.type_hint
        if isinstance(hint, typing_inspect.typingGenericAlias):
            # Only produce error if the type does not match and so system attempts to use
            # the default converter.
            def generic_converter_error(x):
                # todo: support looking at generic arg(s), converting any that need it and then
                #   putting result into generic type; and if it's a generic Sequence,
                #   use a List or Tuple, and so on...
                raise SettingsConversionError(
                    f"Unsupported: Can't convert value {x} into a generic type "
                    f"(future feature)."
                )
            return generic_converter_error

        # By default, convert using the type-hint;
        # ie: If `int` was type-hint, then it could do `int(value)` to get an `int` out of `value`.
        return hint

    def _get_base_typehint(self):
        hint = self.type_hint
        if not hint:
            return None

        origin = typing_inspect.get_origin(hint)
        if origin is None:
            return hint
        return origin


def _allowed_field(k: str, v):
    # For private attributes, don't make fields.
    if k.startswith("_"):
        return False

    # These should be normal properties, defined directly on the class.
    # if isinstance(v, property):
    #     return False

    if isinstance(v, staticmethod):
        return False

    if isinstance(v, classmethod):
        return False

    # For normal methods/callables, don't generate a field.
    return not callable(v)


def generate_setting_fields(
        attrs, parent_fields: Dict[str, SettingsField] = None
) -> Dict[str, SettingsField]:
    """
    Takes a dict of class attributes and returns a dict of SettingsField.
    Ignores any attr that is private (starts with '_') or is a callable or has __get__ defined
    (Assuming that the __get__ is not of type SettingsClassProperty).
    Uses attrs.__annotations__ to provide type hints.

    Args:
        attrs:
        setting_subclasses_in_mro:

    Returns:
        Dict[str, SettingsField] -- Note: All returned SettingsFields will always have the
        following fields defined
        - field.name (Name of attrs key. Overridden by SettingsField.name)
        - field.required (Default to True, Overridden by SettingsField.required)
        - field.type_hint (Uses annotations to define type. If not set then uses default_value
        type. If not set then defaults to `str`
        - field.retriever (Uses passed in default_retriever. Overridden by SettingsField.retriever
        - field.source_name (Name of attrs key)

    """
    if not parent_fields:
        parent_fields = {}

    if annotationlib:
        # Use new Python 3.14 way of doing this:
        annotate_func = annotationlib.get_annotate_from_class_namespace(attrs)
        # Using `VALUE` format, since we require all types to already be available at class-creation time.
        if annotate_func:
            annotations = annotationlib.call_annotate_function(annotate_func, format=annotationlib.Format.VALUE)
        else:
            annotations = None
    else:
        # Use old Python <3.14 way of doing this:
        annotations = attrs.get("__annotations__", None)

    fields = {k: v for k, v in attrs.items() if _allowed_field(k, v)}

    allowed_field_names = set(fields.keys())
    if annotations:
        for key in annotations.keys():
            if not key.startswith("_") and key not in attrs:
                allowed_field_names.add(key)

    setting_fields: Dict[str, SettingsField] = {}
    already_merged_parent_for_field = set()

    def merge_field(attr_key, merge_field):
        if attr_key not in setting_fields:
            setting_fields[attr_key] = SettingsField(
                name=attr_key, source_name=attr_key
            )

        # If we have not merged parent field yet,
        # then do so first before we merge anything else into new field.
        #
        # The objective is to only merge parents into fields that are defined/overriden
        # on the child-class; we don't otherwise want the parent-field in the child-class.
        #
        # If they are not defined as new field on the child class, we should directly
        # use the parent field when it's asked for on child and NOT generate a new child field
        # for that parent field.
        if attr_key not in already_merged_parent_for_field:
            already_merged_parent_for_field.add(attr_key)
            if p_field := parent_fields.get(attr_key):
                setting_fields[attr_key].merge(p_field)

        setting_fields[attr_key].merge(merge_field)

    _add_field_default_from_attrs(fields, merge_field)
    _add_field_typehints_from_annotations(annotations, allowed_field_names, merge_field)
    _unwrap_typehints(fields, merge_field)
    _add_field_overrides_from_attrs(fields, merge_field)

    for field in setting_fields.values():
        # if we have a default_value but no type_hint, use type of default_value as a last-ditch
        # effort to get a type-hint.
        if field.type_hint is None and field.default_value is not None:
            default_value = field.default_value
            # todo: I would like to put a property/getter in a `SettingsField.fget` attribute.
            #   would make things simpler, especially if we ever support setter properties.
            #   and I would not have to worry about this below.
            if not isinstance(default_value, property) and not hasattr(default_value, '__get__'):
                field.type_hint = type(field.default_value)

        _assert_retriever_valid(field)

        if field.type_hint in (None, Any, type(None)):
            raise AssertionError(
                f"Must have type-hint for field ({field}). This may be because there is a "
                f"property defined on BaseSettings subclass that has no return type-hint,"
                f"or type annotation for it somewhere else in the class. "
                f"Or it could be the type-hint is `Any` or `NoneType` which are also "
                f"not supported. Or there may be some other reason there is no type hint. "
                f""
                f"If it's due to using a property-getter, here are two easy ways to specify "
                f"type-hint for a property-field: "
                f""
                f"1. You can do type annotation via: `some_field: int` somewhere in the class. "
                f""
                f"2. You can specify property return-type via: "
                f"`@property \\n def some_field() -> int:"
                f""
            )

        unwrapped_results = unwrap_union(field.type_hint)
        field.type_hint = unwrapped_results.unwrapped_type

        if field.required is None:
            field.required = not unwrapped_results.is_optional

        # Sanity check/fallback, the above is_optional should be good enough.
        if field.required is None:
            field.required = True

    return setting_fields


def _add_field_typehints_from_annotations(annotations, allowed_field_names, merge_field):
    """Get our type-hints and merge/create fields from them. Ignore anything not in
    allowed_field_names

    Args:
        allowed_field_names: Used to exclude fields from inherited classes
    """
    if annotations:
        for k, v in annotations.items():
            if k in allowed_field_names:
                merge_field(k, SettingsField(type_hint=v))


def _add_field_default_from_attrs(class_attrs: Dict[str, Any], merge_field):
    """We take the public initial class attributes and their values and merge/create
    fields from them.
    """
    for k, v in class_attrs.items():
        if isinstance(v, SettingsField):
            # The attribute is a SettingsField, nothing more to do.
            continue

        field_values = SettingsField()

        if hasattr(v, '__get__'):
            default_type = None
            v: property

            # 'fget' on properties are the getter-function.
            if callable(getattr(v, 'fget', None)):
                # Extract type-hint from the getter-functions return annotation;
                # We will use it as a default/fallback type-hint.
                prop_getter_return_type = get_type_hints(v.fget).get('return', None)
                if prop_getter_return_type is not None:
                    field_values.type_hint = prop_getter_return_type

            if isinstance(v, property):
                # We currently don't support property setters/deleters.
                # TODO: Support property setters someday.
                if v.fset or v.fdel:
                    raise AssertionError(
                        "BaseSettings and SettingsField's currently don't have the ability to "
                        "support a property setter/deleter. You can only use read-only properties "
                        "with them. However, you can set a value on a settings field that has a "
                        "property getter, and that value will be used like you would expect. "
                        "When you do that, the set value will be used and the property getter "
                        "will not be called but the set value will instead be returned directly. "
                        "We may support property setters in the future."
                    )

                # For normal properties, we always wrap them in a _PropertyRetriever,
                # and use that for the field's retriever; we consider a normal property
                # the 'retriever' for that value. If user did not directly set the value
                # the retriever, ie: this _PropertyRetriever will be called and it will in turn
                # call the wrapped property to 'retriever' the value.
                field_values.retriever = _PropertyRetriever(v)
            else:
                field_values.default_value = v
        else:
            field_values.default_value = v
            field_values.type_hint = type(v)

        # Call provided merge function that merges our field values into the final field object.
        merge_field(k, field_values)


def _unwrap_typehints(field_attrs: Dict[str, Any], merge_field):
    """We take the public initial class attributes and their values and merge/create
    fields from them.
    """
    for k, v in field_attrs.items():
        field = v
        if isinstance(v, SettingsField):
            merge_field(k, field)


def _add_field_overrides_from_attrs(field_attrs: Dict[str, Any], merge_field):
    """We take the public initial class attributes and their values and merge/create
    fields from them.
    """
    for k, v in field_attrs.items():
        if isinstance(v, SettingsField):
            merge_field(k, v)


def _assert_retriever_valid(field):
    if field.retriever is None:
        return
    assert callable(field.retriever), (
        f"Invalid retriever for field {field}, needs to be callable, see "
        f"SettingsRetrieverProtocol."
    )
