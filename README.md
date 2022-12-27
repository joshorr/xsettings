- [Settings Library](#settings-library)
    * [Settings](#settings)
        + [Settings usage](#settings-usage)
            - [Class/Lazy Attribute Lookup](#classlazy-attribute-lookup)
            - [Change Default Value](#change-default-value)
            - [Setting New Setting on Class Attributes](#setting-new-setting-on-class-attributes)
            - [Class Instance Attribute lookup](#class-instance-attribute-lookup)
            - [Inheriting from Plain Classes](#inheriting-from-plain-classes)
    * [SettingsField](#settingsfield)
        + [How SettingsField is Generated](#how-settingsfield-is-generated)
    * [Converters](#converters)
    * [Properties](#properties)
        + [Supports Read-Only Properties](#supports-read-only-properties)
        + [Getter Properties Supported as a Forward/Lazy-Reference](#getter-properties-supported-as-a-forwardlazy-reference)
        + [Getter Property with Custom SettingsField](#getter-property-with-custom-settingsfield)
        + [Setter Properties Currently Unsupported](#setter-properties-currently-unsupported)
    * [SettingsRetriever](#settingsretriever)
    * [Things to Watch Out For](#things-to-watch-out-for)


# Settings Library

The settings library is seperated into a few core components. 
- Settings
- SettingsField
- SettingsRetriever

## Settings

This is the core class that Settings implementations will inherit from.
Settings can be used as source for external settings / variables that a given 
application / library needs in order to function. It provides future
developers an easy way to see what these external variables are and
where they are derived from.

In its simplest form a Settings class implementation is simply a class 
similar to a `@dataclass` that inherits from a given Settings base class. 

Example Settings File
```python
from xsettings import Settings, SettingsField

class MySettings(Settings):
    a: int
    b: int = 1
    c = "1"
    
    # For Full Customization, allocate SettingsField:
    d: str = SettingsField(...) 
```

Each of these attributes will be converted to a SettingsField object to
control future value lookup. Each part on the attribute (name, type_hint, 
default_value) will be reflected in the SettingsField. If you want more
customization you can set a SettingsField() as your default value and the
fields set in that will be overridden in the main SettingsField object.

### Settings usage

#### Class/Lazy Attribute Lookup

Referencing the attribute at the class level will return a `SettingsClassProperty`
rather than a SettingsField (or the default value). This is useful when you want
to do property chaining, or you want to use a property as a property in another
class

```python
from xsettings import Settings, EnvSettings
class MySettings(Settings):
    table_name: str
    
class MyTable:
    class Meta:
        # Example 1:
        table_name = MySettings.table_name

class MyEnvSettings(EnvSettings):
    my_table_name: str

# Example 2:
MySettings.grab().table_name = MyEnvSettings.my_table_name

# Example 3, default value of settings field can be a lazy-ref:
class MyOtherSettings(Settings):
    my_setting_attr: str = MyEnvSettings.my_table_name
```

#### Change Default Value

You can now (as of v1.3) change the default value on an already created Settings subclass:

```python
from xsettings import Settings, SettingsField

class MySettings(Settings):
    a: int
    b: int = 1

# Change default value later on;
# Now the `MySettings.a` will have a
# default/fallback value of `2`:
MySettings.a = 2

class MyOtherSettings(Settings):
    some_other_setting: str

# You can also set a lazy-ref as setting field's
# default value after it's class is created.
# (also if the type-hint's don't match it will convert
#  the value as needed like you would expect.
MyOtherSettings.some_other_setting = MySettings.b

# It's a str now, since `MyOtherSettings.some_other_setting` has a str typehint:
assert MyOtherSettings.grab().some_other_setting == '1'
```

#### Setting New Setting on Class Attributes

You can't create new settings attributes/fields on a Settings subclass after the class
is created (only during class creation).

You can set/change the default value for an existing settings attribute by simply assigning
to it as a class attribute (see topic [Change Default Value](#change-default-value)).

#### Class Instance Attribute lookup

Setting classes inherit from `1xinject.Dependency` and as such are considered singletons.
Instances should not be created. Instead, to access an instance you should do
`MySettings.grab()`; or you can use an `MySettings.proxy()`, ie:

```python
my_settings = MySettings.proxy()

# Can use `my_settings` just like `MySettings.grab().table_name`,
print(my_settings.table_name)

# You can also import the `my_settings` proxy into other modules, for use elsewhere.
from my_project.settings import my_settings
print(my_settings.table_`name)
```

Proxies are directly importable into other files, the proxy will lookup the current
dependency/singletone instance every time you access it for normal attributes and methods
(anything starting with a `_`/underscore is not proxied).

To lookup the value of a given settings simply reference it on the Singleton
instance via `MySettings.grab().table_name`. This will cause a lookup
to happen.

#### Inheriting from Plain Classes

Currently, there is a something to watch out for when you also inherit from a plain class
for you Settings subclass.

For now, we treat all plain super-class values on attributes as-if they were directly assigned
to the settings instance; ie: we will NOT try to 'retrieve' the value unless the value is
set to `xsentinels.Default` in either the instance or superclass (whatever value it finds via normal
python attribute retrieval rules).

You can use `xsentinels.Default` to force Settings to lookup the value and/or use its default value if it
has one.

May in the future create a v2 of xsettings someday that will look at attributes directly
assigned to self, then and retrieved value, then any plain super-class set value.

(For a more clear example of this, see unit test method `test_super_class_with_default_value_uses_retriever`)

## SettingsField

Provides value lookup configuration and functionality. It controls
how a source value is retrieved `xsettings.fields.SettingsField.retriever` and
converted `xsettings.fields.SettingsField.converter`.

If there is not SettingsField used/generated for an attribute,
then it's just a normal attribute.

No special features of the Settings class such as lazy/forward-references will work with them.

### How SettingsField is Generated

Right now, a SettingsField is only automatically generated for annotated attributes.

Also, one is generated for any `@property` functions
(you must define a return type-hint for property).

Normal functions currently DO NOT generate a field, also attributes without a type annotation
will also not automatically be generated.

Anything starting with an `_` will not have a field generated for it,
they are for use by properties/methods on the class and work like normal.

You can also generate your own SettingsField with custom options by creating
one and setting it on a class attribute, during the class creation process.

After a class is created, you can't change or add SettingFields to it anymore, currently.

Examples:

```python
from xsettings import Settings, SettingsField

class MySettings(Settings):
    custom_field: str = SettingsField(required=False)
    
    # SettingsField auto-generated for `a`:
    a: str
    
    # A Field is generated for `b`, the type-hint will be `type(2)`.
    b = 2
    
    # A field is NOT generated for anything that starts with an underscore (`_`),
    # They are considered internal attributes, and no Field is ever generated for them.
    _some_private_attr = 4
    
    # Field generated for `my_property`, it will be the fields 'retriever'.
    @property
    def my_property(self) -> str:
        return "hello"
    
    # No field is generated for `normal_method`:
    # Currently, any directly callable object/function as a class attribute value
    # will never allow you to have a Field generated for it.
    def normal_method(self):
        pass
```

## Converters

When Settings gets a value due to someone asking for an attribute on it's self, it will
attempt to convert the value if the value does not match the type-hint.

To find a converter, we check these in order, first one found is what we use:

1. We first check `self.converter`.
2. Next, `xsettings.default_converters.DEFAULT_CONVERTERS`.
3. Finally, we fall-back to using the type-hint (ie: `int(value)` or `str(value)`).

If the retreived value does not amtch the type-hint, it will run the converter by calling
it and passing the value to convert. The value to convert is whatever value was set,
retreived. It can also be the field's default-value if noting is set/retreived.


## Properties

### Supports Read-Only Properties

The Settings class also supports read-only properties, they are placed in a SettingField's
retriever (ie: `xsettings.fields.SettingField.retriever`).

When you access a value from a read-only property, when the value needs to be retrieved,
it will use the property as a way to fetch the 'storage' aspect of the field/attribute.

All other aspects of the process behave as it would for any other field.

This means in particular, after the field returns its value Settings will check the returned values
type against the field's type_hint, and if needed will convert it if needed before handing it to 
the thing that originally requested the attribute/value.

It also means that, if the Settings instance has a plain-value directly assigned to it,
that value will be used and the property will not be called at all
(since no value needs to be 'retrieved').

In effect, the property getter will only be called if a retrieved value is needed for the
attribute.

Here is an example below. Notice I have a type-hint for the return-type of the property.
This is used if there is no type-annotation defined for the field.

```python
from xsettings import Settings
from decimal import Decimal

class MySettings(Settings):
    @property
    def some_setting(self) -> Decimal:
        return "1.34"

assert MySettings.grab().some_setting == Decimal("1.34")
```

You can also define a type-annotation at the class level for the property like so:

```python
from xsettings import Settings
from decimal import Decimal

class MySettings(Settings):
    # Does not matter if this is before or after the property,
    # Python stores type annotations in a separate area vs normal class attribute values in Python.
    some_setting: Decimal
    
    @property
    def some_setting(self):
        return "1.34"

assert MySettings.grab().some_setting == Decimal("1.34")
```

### Getter Properties Supported as a Forward/Lazy-Reference

You can get a forward-ref for a property field on a Settings class,
just like any other field attribute on a Settings class:

```python
from xsettings import Settings
from decimal import Decimal

class MySettings(Settings):
    # Does not matter if this is before or after the property,
    # Python stores type annotations in a separate area vs normal class attribute values in Python.
    some_setting: Decimal
    
    @property
    def some_setting(self) -> Decimal:
        return "1.34"

class OtherSettings(Settings):
    other_setting: str = MySettings.some_setting
    
assert OtherSettings.grab().other_setting == "1.34"
```

In the example above, I also illustrate that a forward-ref will still pay-attention
to the type-hint assigned to the field. It's still converted as you would expect,
in this case we convert a Decimal object into a str object when the value for
`other_setting` is asked for.

### Getter Property with Custom SettingsField

You can also specify a custom SettingsField and still use a property with it.
Below is an example. See `xsettings.fields.SettingsField.getter` for more details.

```python
from xsettings import Settings, SettingsField
class MySettings(Settings):
    # Does not matter if this is before or after the property,
    # Python stores type annotations in a separate area vs normal class attribute values in
    # Python.
    some_setting: str = SettingsField(required=False)

    @some_setting.getter
    def some_setting(self):
        return "1.36"

assert MySettings.grab().some_setting == "1.36"
```


### Setter Properties Currently Unsupported

You can't currently have a setter defined for a property on a class.
This is something we CAN support without too much trouble, but have decided to
put off for a future, if we end up wanting to do it.

If you define a setter property on a Settings class, it will currently raise an error.

## SettingsRetriever

Its responsibility is providing functionality to retrieve a variable from 
some sort of variable store. The default `xsettings.settings.SettingsRetriever`
provides the base implementation. This implementation will always raise a 
SettingsValueError unless `xsettings.fields.SettingsField.required` has been marked as `False`.
Override the SettingsRetriever on a Settings class like this.

```python
from xsettings import Settings
class MySettings(Settings, default_retriever=MyRetriever()):
    pass
```

## Things to Watch Out For

- If a field has not type-hint, but does have a normal (non-property) default-value,
  The type of the default-value will be used for type-hint.
- If a field has no converter, it will use the type-hint as the converter by default.
- Every field must have a type-hint, otherwise an exception will be raised.
