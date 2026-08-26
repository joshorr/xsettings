"""

See doc-comments for `BaseSettings` below.


"""

from typing import (
    Dict, Any, Union, TypeVar, Protocol, Optional, Iterable, List, Type, TYPE_CHECKING
)

from xinject import Dependency, XContext
from xloop import xloop
from xsentinels import Default

from xsettings.fields import generate_setting_fields, SettingsField, SettingsClassProperty
from xsettings.errors import SettingsValueError

if TYPE_CHECKING:
    from .retreivers import SettingsRetrieverProtocol

T = TypeVar("T")


RetrieverOrList = 'Union[SettingsRetrieverProtocol, Iterable[SettingsRetrieverProtocol]]'


class _SettingsMeta(type):
    """Represents the class-type instance/obj of the `BaseSettings` class.
    Any attributes in this object will be class-level attributes of
    a class or subclass of `BaseSettings`.

    ie: A `_SettingsMeta` instance is created each time a new BaseSettings or BaseSettings subclass
        type/class is created (it represents the class/type its self).
    """

    # This will be a class-attributes on the normal `BaseSettings` class/subclasses.
    _setting_fields: Dict[str, SettingsField]
    _default_retrievers: 'List[SettingsRetrieverProtocol]'

    _there_is_plain_superclass: bool
    """ There is some other superclass, other then BaseSettings/object/Dependency. """

    _setting_subclasses_in_mro: 'List[Type[BaseSettings]]'
    """
    Includes self/cls plus all superclasses who are BaseSettings subclasses in __mro__
    (but not BaseSettings it's self); in the same order that they appears in __mro__.
    """

    def __new__(
        mcls,
        name,
        bases,
        attrs: Dict[str, Any],
        *,
        default_retrievers: RetrieverOrList = None,
        skip_field_generation: bool = False,
        **kwargs,
    ):
        """
        The instance of `mcls` is a BaseSettings class or subclass
        (not BaseSettings object, the class its self).

        Objective in this method is to create a set of SettingsField object(s) for use by the new
        BaseSettings subclass, and set their default-settings correctly if the user did not
        provide an explict setting.

        Args:
            name: Name of the new class
            bases: Base-classes, in left-to-right order.
            attrs: Attributes provided on class at class definition time.

            default_retriever: Used to retrieve values for a `SettingsField` if Field has
                no set retriever (ie: not set directly be user).

                This can be passed in like so:
                `class MySettings(BaseSettings, default_retriever=...)`

            **kwargs: Any extra arguments get supplied to the super-class-type.
        """
        # These defaults may be altered later on in this method (after class is created)...
        attrs['_there_is_plain_superclass'] = False
        attrs['_setting_subclasses_in_mro'] = []
        attrs['_default_retrievers'] = list(xloop(default_retrievers))

        if skip_field_generation:
            # Skip doing anything special with any BaseSettings classes created in our/this module;
            # They are abstract classes and are need to be sub-classed to do anything with them.
            attrs['_setting_fields'] = {}
            cls = super().__new__(mcls, name, bases, attrs, **kwargs)  # noqa
            return cls

        # W need to get base-types in mro order, before we create the class.
        types_in_mro = type(name, bases, {}, skip_field_generation=True).__mro__[1:]

        # And look through the __mro__ python determined while creating the class,
        # we cache the specific ones/information we need this one time so future operators
        # are simpler/faster.
        setting_subclasses_in_mro = []

        # We install can't include 'us' because our type has not been created yet.
        attrs['_setting_subclasses_in_mro'] = setting_subclasses_in_mro
        for c in types_in_mro:
            # Skip the ones that are always present, and don't need to examined...
            if c is BaseSettings:
                continue
            if c is object:
                continue
            if c is Dependency:
                continue

            # We want to know the order if aby BaseSettings subclasses that we are inheriting from.
            # Also want to know if there are any plain/non-setting classes in our parent hierarchy
            # (that are not object/Dependency, as they both will always be present).
            if issubclass(c, BaseSettings):
                setting_subclasses_in_mro.append(c)
            else:
                attrs['_there_is_plain_superclass'] = True

        parent_fields = {}

        for c in reversed(setting_subclasses_in_mro):
            parent_fields.update(c._setting_fields)

        setting_fields = generate_setting_fields(
            attrs, parent_fields
        )

        attrs["_setting_fields"] = setting_fields

        # Any attributes that were converted to fields we remove from class attributes,
        # they instead will be dynamically looked up lazily as-needed via their associated field.
        for k in setting_fields.keys():
            attrs.pop(k, None)

        # This creates the new BaseSettings class/subclass.
        cls = super().__new__(mcls, name, bases, attrs, **kwargs)

        # Insert newly crated class into top of its setting subclasses list.
        cls._setting_subclasses_in_mro.insert(0, cls)

        # We now link source_class of each field to us; helps with debugging.
        for field in setting_fields.values():
            field.source_class = cls

        return cls

    settings__default_retrievers: 'List[SettingsRetrieverProtocol]'

    # @SettingsClassProperty
    @property
    def settings__default_retrievers(self) -> 'List[SettingsRetrieverProtocol]':
        """
        You can add one or more retrievers to this `subclass` of BaseSettings
        (modifies default_retrievers for the entire class + subclasses, only modifies this specific
        class).

        You can add or modify the list of default-retrievers via
        `BaseSettings.settings__default_retrievers`. It's a list that you can directly modify;
        ie: `MySettings.settings__default_retrievers.append(my_retriever)`.

        ## Background

        Below is a quick summary, you can see more detailed information in main docs under the
        `"How Setting Field Values Are Resolved"` heading.

        Directly set values (ie: `self.some_settings = 'some-value'`)
        are first checked for in self, and next in `xinject.context.XContext.dependency_chain`
        (looking at each instance currently in the dependency-chain, see link for details).

        If value can't be found set on self or in dependency chain,
        the retrievers are checked next.

        First the field's individual retriever is checked (directly on field object,
        this includes any `@property` fields too as the property getter method is stored on
        field's individual retriever).

        After the individual field retrievers are consulted, instance retrievers are checked next
        before finally checking the default-retrievers for the entire class.

        They are checked in the order added.

        Child dependencies (of the same exactly class/type) in the
        `xinject.context.XContext.dependency_chain` will also check these instance-retrievers.

        The dependency chain is checked in the expected order of first consulting self,
         then the chain in most recent parent first order.

        For more details on how parent/child dependencies work see
        `xinject.context.XContext.dependency_chain`.

        After the dependency-chain is checked, the default-retrievers are checked
        in python's `mro` (method-resolution-order), checking its own class first
        before checking any super-classes for default-retrievers.

        Returns:
            A list of default-retrievers you can examine and/or modify as needed.
        """
        return self._default_retrievers

    def __getattr__(self, key: str) -> SettingsClassProperty:
        """
        We will return a `ClassProperty` object setup to retrieve the value asked for as
        a type of forward-reference/pointer. It will, when set into an object or class,
        retrieve the value from self for `key` when it's asked too.

        Example:

        >>> class MySettings(BaseSettings):
        ...    my_url_setting: str
        >>>
        >>> class SomeClass:
        ...    some_attr = MySettings.my_url_setting
        >>>
        >>> MySettings.grab().my_url_setting = "my-url"
        >>> assert SomeClass.some_attr == "my-url"
        """

        # Anything that starts with `_` or starts with `settings__`
        # is handled like a normal pythonattribute.
        if key.startswith("_") or key.startswith("settings__"):
            raise AttributeError(
                f"An attribute lookup that start with `_` or `settings__` just happened ({key}) "
                f"and it does not exist. "
                f"Attributes name this way can't be fields, but they should also exist so there "
                f"must be some sort of bug.... details: "
                f"attribute name ({key}) on BaseSettings subclass ({self})."
            )

        for c in self._setting_subclasses_in_mro:
            c: _SettingsMeta
            if key in c._setting_fields:
                break
            # We got to `BaseSettings` without finding anything, BaseSettings has no fields,
            # raise exception about how we could not find field.
            if c is BaseSettings:
                raise AttributeError(
                    f"Have no class-attribute or defined SettingsField for "
                    f"attribute name ({key}) on BaseSettings subclass ({self})."
                )

        @SettingsClassProperty
        def lazy_retriever(calling_cls):
            return getattr(self.grab(), key)

        return lazy_retriever

    def __setattr__(self, key: str, value: Union[SettingsField, Any]):
        """
        Setting any public-attribute on class is currently only supported for changing
        an existing field's default value.

        We may do something more with this in the future, for now leaving other
        use-cases unsupported (such as creating new setting fields on already created subclasses).
        """
        if key.startswith("_"):
            return super().__setattr__(key, value)

        field = None
        for c in self._setting_subclasses_in_mro:
            c: _SettingsMeta
            if field := c._setting_fields.get(key):
                break
            # We got to `BaseSettings` without finding anything, BaseSettings has no fields,
            # give-up searching for field.
            if c is BaseSettings:
                break

        if not field:
            # Right now we don't support making new SettingField's after the BaseSettings subclass
            # has been created. We could decide to do that in the future, but for now we
            # are keeping things simpler.
            raise AttributeError(
                f"Setting new fields on BaseSettings subclass unsupported currently, attempted to "
                f"set key ({key}) with value ({value})."
            )

        # Set default value of an existing field with `key` attribute-name:
        field.default_value = value


class BaseSettings(
    Dependency,
    metaclass=_SettingsMeta,

    # We should preserve any setting classes in global context between unit-test function runs.
    remove_between_unittests=True,

    # No default retrievers for BaseSettings.
    default_retrievers=[],

    # BaseSettings has no fields, it's a special abstract-type of class skip field generation.
    # You should never use this option in a BaseSettings subclass.
    skip_field_generation=True
):
    """
    Base Settings class. For all class properties defined there will be a corresponding
    _settings_field["name"] = SettingsField created value that will control how this value is
    read and manipulated.

    The purpose of the Settings class is to allow a library or project/service to define a
    number of settings that are needed in order to function. You define a number of Settings
    properties to indicate what settings are available to use in the project.

    You define a Settings and properties very similar to how you define a dataclass. You specify
    a property name, type_hint, and default_value.

    >>> class MySettings(BaseSettings):
    ...    name: type_hint = default_value

    A default `SettingsField` will be configured using the name, type_hint, and default_value as
    follows -- `SettingsField(name=name, type_hint=type_hint, converter=type_hint,
    default_value=default_value, resolver=default_resolver)`

    This functionality can be overridden by setting the default_value to a custom `SettingsField`.
    The custom `SettingsField` will be merged with the default `SettingsField` overriding any
    fields that were defined in the custom SettingsField.

    It's important to note that while we are setting these attributes on the class they will not
    remain as attributes on the class. The _SettingsMeta will take each attribute and convert
    them to a SettingsField and then place them in the class's _setting_fields attribute.

    Example of various ways to allocate a SettingsField on a Settings subclass:

    >>> class MySettings(BaseSettings):
    ...     setting_1: int
    Allocates
    >>> SettingsField(name="setting_1", type_hint=int, resolver=SettingsResolver)

    >>> class MySettings(BaseSettings):
    ...     setting_1: int = 3
    Allocates
    >>> SettingsField(name="setting_1", type_hint=int, resolver=SettingsResolver, default_value=3)

    >>> class MySettings(BaseSettings):
    ...     setting_1 = 3
    Allocates
    >>> SettingsField(name="setting_1", type_hint=int, resolver=SettingsResolver, default_value=3)

    >>> class MySettings(BaseSettings):
    ...     setting_1: int = SettingsField(name="other", required=False)
    Allocates
    >>> SettingsField(name="other", type_hint=int, resolver=SettingsResolver, required=False)

    ## Accessing Class (not instance) Attributes = Lazy Property Reference

    You can do lazy forward-refrences by simply asking the Settings class (not instance) for a
    attribute. Doing so will return a `SettingsClassProperty` that is a forward reference to the
    singleton instance class attribute.

    Examples of how you might use this

    >>> class MySettings(BaseSettings):
    ...    my_url_setting: str
    >>> class MySubSettings(BaseSettings):
    ...    my_field: str
    >>> class SomeClass:
    ...    some_attr = MySettings.my_url_setting
    >>>
    >>> MySettings.grab().my_url_setting = "my-url"
    >>> MySubSettings.grab().my_field = MySettings.my_url_setting
    >>>
    >>> assert SomeClass.some_attr == "my-url"
    >>> assert MySubSettings.grab().some_attr == "my-url"
    >>> assert MySettings.grab().some_attr == "my-url"

    ## Setting public Class Attributes after creation time not allowed
    Attempting to set a public class level attribute will result in an Error being raised.

    ## Settings Attribute (Property) Inheritance not allowed
    To keep things as simple as possible we don't allow SettingsClass attribute inheritance. You
    can however create a parent class that defines methods / @properties that can be inherited.
    Trying to set a regular (non-method/non-property/public) attribute will raise an error.

    ## Accessing Instance Properties = Get Value and Convert
    When calling MySettings.grab().my_setting the Settings class will attempt to retrieve and
    convert the corresponding value. Getting the the source value and converting the value is
    controlled by the SettingsField. Here is how it works.

    Start by attempting to retrieve a property from the class instance
    >>> MyClass.grab().my_setting

    The Settings class will do the following
    1. Attempt to retrieve a value.
       a. Lookup value from self via `object.__getattribute__(self, key)`
       b. If an AttributeError is thrown then lookup the value from the corresponding field
       via `self._settings_field[name].get_value()`
    2. Convert the retrieved value by calling `self._settings_field[name].convert_value(value)`

    .. todo:: We don't support property setters/deleters at the moment.
              We would need to implement a `__setattr__` here, where it would check
              for a property setter/getter on field object.
              (Consider a explicit `fget` and `fset` attribute on SettingsField at that point)
    """

    _instance_retrievers: 'List[SettingsRetrieverProtocol]'

    def __init__(
            self,
            retrievers: (
                    'Optional[Union[List[SettingsRetrieverProtocol], SettingsRetrieverProtocol]]'
            ) = None,
            **kwargs
    ):
        """
        Set attributes to values that are passed via key-word arguments, these are the initial
        values for the settings instance your creating; they are set directly on the instance
        as if you did this:

        ```python
        # These two statements do the same thing:
        obj = SomeSettings(some_keyword_arg="hello")

        obj = SomeSettings()
        obj.some_keyword_arg="hello"
        ```
        Args:
            retrievers: can be used to populate new instance's retrievers,
            see `BaseSettings.settings__instance_retrievers`.

        """
        self._instance_retrievers = list(xloop(retrievers))

        for k, v in kwargs.items():
            setattr(self, k, v)

    def add_instance_retrievers(
            self, retrievers: 'Union[List[SettingsRetrieverProtocol], SettingsRetrieverProtocol]'
    ):
        from warnings import warn
        warn(
            f"BaseSettings.add_instance_retrievers is now deprecated, "
            f"was used on subclass ({type(self)}); "
            f"use property `settings__instance_retrievers` and call 'append' on result; "
            f"ie: `my_settings.settings__instance_retrievers.append(retriever)"
        )
        self.settings__instance_retrievers.extend(xloop(retrievers))

    @property
    def settings__instance_retrievers(self) -> 'List[SettingsRetrieverProtocol]':
        """
        You can add one or more retrievers to this `instance` of settings
        (won't modify default_retrievers for the entire class, only modifies this specific
        instance).

        You can add or modify the list of instance-retrievers via
        `BaseSettings.settings__instance_retrievers`. It's a list that you can directly modify;
        ie: `my_settings.settings__instance_retrievers.append(my_retriever)`.

        ## Background

        Below is a quick summary, you can see more detailed information in main docs under the
        `"How Setting Field Values Are Resolved"` heading.

        Directly set values (ie: `self.some_settings = 'some-value'`)
        are first checked for in self, and next in `xinject.context.XContext.dependency_chain`
        (looking at each instance currently in the dependency-chain, see link for details).

        If value can't be found set on self or in dependency chain,
        the retrievers are checked next.

        First the field's individual retriever is checked (directly on field object,
        this includes any `@property` fields too as the property getter method is stored on
        field's individual retriever).

        After the individual field retrievers are consulted, instance retrievers are checked next
        before finally checking the default-retrievers for the entire class.

        They are checked in the order added.

        Child dependencies (of the same exactly class/type) in the
        `xinject.context.XContext.dependency_chain` will also check these instance-retrievers.

        The dependency chain is checked in the expected order of first consulting self,
         then the chain in most recent parent first order.

        For more details on how parent/child dependencies work see
        `xinject.context.XContext.dependency_chain`.

        After the dependency-chain is checked, the default-retrievers are checked
        in python's `mro` (method-resolution-order), checking its own class first
        before checking any super-classes for default-retrievers.

        Returns:
            A list of instance-retrievers you can examine and/or modify as needed.
        """
        return self._instance_retrievers

    def __getattribute__(self, key):
        # Anything that starts with `_` or starts with `settings__`
        # is handled like a normal python attribute.
        if key.startswith("_") or key.startswith("settings__"):
            return object.__getattribute__(self, key)

        attr_error = None
        value = None
        already_retrieved_normal_value = False
        cls = type(self)
        field: Optional[SettingsField] = None

        for c in cls._setting_subclasses_in_mro:
            c: _SettingsMeta
            # todo: use isinstance?
            if c is BaseSettings:
                # We got to the 'BaseSettings' base-class it's self, no need to go any further.
                break
            if field := c._setting_fields.get(key):
                # Found the field, break out of loop.
                break

        def get_normal_value(obj: BaseSettings = self):
            nonlocal value
            nonlocal attr_error

            # Keep track that we already attempted to get normal value.
            nonlocal already_retrieved_normal_value
            if obj is self:
                already_retrieved_normal_value = True

            try:
                # Look for an attribute on self first.
                value = object.__getattribute__(obj, key)
                if hasattr(value, "__get__"):
                    value = value.__get__(obj, cls)
                attr_error = None
            except AttributeError as error:
                attr_error = error

        # We don't want to grab the value like normal if we are a field
        # and DON'T have a locally/instance value defined for attribute.
        # This helps Setting classes that are subclasses of Plain classes
        # attempt to retrieve the value via the field retriever/mechanism
        # before using that plain-classes, class attribute.
        #
        # Otherwise, the plain-class attribute would ALWAYS be used over the field,
        # making the subclasses field definition somewhat useless.
        if not self._there_is_plain_superclass or not field or key in self.__dict__:
            get_normal_value()

        if not already_retrieved_normal_value or value is None:
            # See if any parent-setting-instances (not super/base classes)
            for parent_settings in XContext.grab().dependency_chain(cls):
                if key in parent_settings.__dict__:
                    get_normal_value(parent_settings)

                if value is not None:
                    break
        try:
            if field:
                return _resolve_field_value(settings=self, field=field, key=key, value=value)
        except SettingsValueError as e:
            # todo: Do some sort of refactoring/splitting this out of this method
            #       (starting to get too large).

            # We had a field and could not retrieve the value, if we have not already attempted
            # to get the 'normal' value via our base-classes attributes , then attempt that;
            # If there is a plain class in are superclass/base-classes (ie: non-Setting)
            # This will check for a value in that class as well.
            if already_retrieved_normal_value:
                # Just continue the original exception
                raise

            get_normal_value()
            if attr_error:
                # Could not get the normal value from superclass, raise original exception.
                # todo: for Python 3.11, we can raise both exceptions (e + attr_error)
                #       we actually have two separate trees of exceptions here!
                #       For now we are prioritizing field value retrieval exception
                #       as the 'from' exception and putting the plain-class attribute error
                #       inside this exception.,
                raise SettingsValueError(
                    f"After attempting to get field value "
                    f"(the 'from' exception with message [{e}]); "
                    f"I tried to get value from plain superclass and that was also unsuccessful "
                    f"and produced exception/error: ({attr_error}); "
                    f"for field ({field})."
                ) from e

            if value is None and field.required:
                raise SettingsValueError(
                    f"After attempting to get field value I next tried to get it from the plain "
                    f"superclass but got None (details: via 'from' exception with message {e}); "
                    f"for field ({field})."
                ) from e

            value = field.convert_value(value)
            if value is None and field.required:
                raise SettingsValueError(
                    f"After attempting to get field value I next tried to get it from the plain "
                    f"superclass, it came back with a value. But after running the `converter` on "
                    f"the retrieved value a None was the result and this field is required; "
                    f"for field ({field})."
                ) from e
            return value

        if attr_error:
            raise AttributeError(
                f"Unable to retrieve settings attribute ({key}) from ({self}), "
                f"there was no defined class-level settings field and no value set for "
                f"attribute on object, see original exception for more details."
            ) from attr_error

        return value


Settings = BaseSettings
"""
Deprecated; Use `BaseSettings` instead.

Here for backwards compatability, renamed original class from `Settings` to `BaseSettings`.
"""


def _resolve_field_value(settings: BaseSettings, field: SettingsField, key: str, value: Any):
    cls = type(settings)

    # If we have a field, and current value is Default, or we got AttributeError,
    # we attempt to retrieve the value via the field's retriever.
    if value is None or value is Default:
        def self_and_parent_retrievers():
            for r in settings._instance_retrievers:
                yield r

            for parent_settings in XContext.grab().dependency_chain(cls):
                # skip self if we are in chain, already did it.
                if parent_settings is settings:
                    continue
                for r in parent_settings._instance_retrievers:
                    yield r

            for parent_class in cls._setting_subclasses_in_mro:
                for r in parent_class._default_retrievers:
                    yield r

        for retriever in xloop(field.retriever, self_and_parent_retrievers()):
            value = retriever(field=field, settings=settings)

            if value is Default:
                # Use whatever the default value is, don't fall back and look in other retrievers.
                value = None
                break

            if value is not None:
                break

    if value is None:
        value = field.default_value
        if callable(value):
            value = value()

    if value is None:
        if field.required:
            # Data-classes will print out all their fields by default, should give good info!
            raise SettingsValueError(f"Missing value for {field}, while retrieving value.")
        value = None

    # If value is a property, get the value from the property...
    if value and hasattr(value, '__get__'):
        value = value.__get__(settings, cls)

    original_value = value
    value = field.convert_value(value)

    if value is None and field.required:
        raise SettingsValueError(
            f'Field ({field}) is required/non-optional and the value we have is '
            f'`None` after running the converter on the originally retrieved value of '
            f'({original_value}).'
        )
    return value


