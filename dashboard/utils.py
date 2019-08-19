from django import forms
from django.forms.models import apply_limit_choices_to_to_formfield
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Aggregate
from dashboard.models import (
    ExtractedChemical,
    ExtractedCPCat,
    ExtractedFunctionalUse,
    ExtractedHabitsAndPractices,
    ExtractedHHDoc,
    ExtractedHHRec,
    ExtractedListPresence,
    ExtractedText,
)


class GroupConcat(Aggregate):
    """Allows Django to use the MySQL GROUP_CONCAT aggregation.

    Arguments:
        separator (str): the delimiter to use (default=',')

    Example:
        Pizza.objects.annotate(
            topping_str=GroupConcat(
                'toppings',
                separator=', ',
                distinct=True,
            )
        )
    """

    function = "GROUP_CONCAT"
    template = "%(function)s(%(distinct)s%(expressions)s SEPARATOR '%(separator)s')"
    allow_distinct = True

    def __init__(self, expression, separator=",", **extra):
        super().__init__(expression, separator=separator, **extra)


class SimpleTree:
    """A simple tree data structure. Used for traversing PUCs.
    
    Properties:
        name (str): the node name
        value (any): the root node value
        leaves (list): a list of children SimpleTree objects
    """

    def __init__(self, name=None, value=None, leaves=[]):
        """Initialize a SimpleTree instance.

        Arguments:
            name (str): the node name (default=None)
            value (any): the root node value (default=None)
            leaves (list): a list of children SimpleTree objects (default=[])
        """
        self.name = name
        self.value = value
        self.leaves = leaves

    def set(self, names, value, default=None):
        """Recursively add leaves to a SimpleTree object.

        Arguments:
            names (iter): an iterable of names to route the leaf under
            value (any): the leaf value (default=default)
            default (any): if a leaf doesn't exist upstream from the destination
                           use this value as the upstream leaf value
        """
        root = self
        for name in names:
            try:
                leaf = next(l for l in root.leaves if l.name == name)
            except StopIteration:
                leaf = SimpleTree(name=name, value=default, leaves=[])
                root.leaves.append(leaf)
            root = leaf
        root.value = value

    def iter(self):
        """Return an iterator than traverses the tree downward."""
        yield self
        for leaf in self.leaves:
            yield from leaf.iter()

    def find(self, names):
        """Breadth-first search

        Arguments:
            names (iter): an iterable containing the the names to look for

        Returns:
            a SimpleTree object
        """
        root = self
        for name in names:
            root = next(l for l in root.leaves if l.name == name)
        return root

      
def get_extracted_models(t):
    """Returns the parent model function and and the associated child model
    based on datagroup type"""
    if t == "CO" or t == "UN":
        return (ExtractedText, ExtractedChemical)
    elif t == "FU":
        return (ExtractedText, ExtractedFunctionalUse)
    elif t == "CP":
        return (ExtractedCPCat, ExtractedListPresence)
    elif t == "HP":
        return (ExtractedText, ExtractedHabitsAndPractices)
    elif t == "HH":
        return (ExtractedHHDoc, ExtractedHHRec)
    else:
        return (None, None)


def clean_dict(odict, model, translations={}):
    """Cleans out key:value pairs that aren't in the model fields
    """
    cleaned = {}
    for k, v in odict.items():
        translated_k = translations.get(k, k)
        try:
            model._meta.get_field(translated_k)
            cleaned[translated_k] = v
        except FieldDoesNotExist:
            continue
    return cleaned


def update_fields(odict, model):
    """Takes a dict and updates the associated fields w/in the model"""
    for f in model._meta.get_fields():
        if f.name in odict.keys():
            setattr(model, f.name, odict[f.name])


def field_for_model(model, field, **kwargs):
    """Get a form field from a model."""
    return model._meta.get_field(field).formfield(**kwargs)


def get_form_for_models(
    *args,
    fields=[],
    translations={},
    required=[],
    skip_missing=False,
    formfieldkwargs={},
):
    """Returns a form for the models and fields provided."""
    field_dict = {}
    required = set(required)
    for f in fields:
        translated_field = translations.get(f, f)
        for m in args:
            formfield = None
            try:
                k = formfieldkwargs.get(translated_field, {})
                modelfield = m._meta.get_field(translated_field)
                formfield = modelfield.formfield(**k)
                if formfield is None and modelfield.one_to_one:
                    if "queryset" in k:
                        formfield = forms.ModelChoiceField(**k)
                    else:
                        formfield = forms.ModelChoiceField(
                            queryset=modelfield.target_field.model.objects.all(), **k
                        )
                apply_limit_choices_to_to_formfield(formfield)
                if modelfield.validators != formfield.validators:
                    formfield.validators = modelfield.validators
                if f in required:
                    formfield.required = True
                break
            except FieldDoesNotExist:
                continue
        if formfield:
            field_dict[f] = formfield
        elif not skip_missing:
            raise FieldDoesNotExist("The field '%s' was not found" % translated_field)
    return type("ModelMuxForm", (forms.Form,), field_dict)


def gather_errors(form_instance, values=False):
    """Gather errors for formsets or forms."""
    errors = []
    if type(form_instance.errors) == list:
        tmp_errors = {}
        for i, error_dict in enumerate(form_instance.errors):
            for field, error in error_dict.as_data().items():
                for e in error:
                    all_msgs = [e.message] + e.messages
                    for all_e in all_msgs:
                        error_mesage = "%s: %s" % (field, all_e)
                        if error_mesage in tmp_errors:
                            tmp_errors[error_mesage].append(i)
                        else:
                            tmp_errors[error_mesage] = [i]
        for error, i in tmp_errors.items():
            if values:
                field = error.split(":")[0]
                prefix = form_instance.prefix
                try:
                    uniq = set(
                        form_instance.data["%s-%d-%s" % (prefix, row, field)]
                        for row in i
                    )
                except KeyError:
                    uniq = set()
            else:
                uniq = list(set(row + 1 for row in i))
                uniq.sort()
                uniq = [str(i) for i in uniq]
            if len(uniq) > 1:
                i_str = "values" if values else "rows"
            elif len(uniq) == 1:
                i_str = "value" if values else "row"
            else:
                i_str = ""
            if i_str:
                errors.append("%s (%s %s)" % (error, i_str, ", ".join(uniq)))
            else:
                errors.append(error)
    else:
        for field, error in form_instance.errors.as_data().items():
            if field == "__all__":
                errors.append(error[0].message)
                return errors
            for e in error:
                errors.append("%s: %s" % (field, e.message))
    if hasattr(form_instance, "non_form_errors"):
        for error in form_instance.non_form_errors().as_data():
            errors.append(error.message)
    err_search = lambda s: any(s in e for e in errors)
    err_filter = lambda s: list(e for e in errors if s not in e)
    err_rep = lambda s, r: list(e.replace(s, r) for e in errors)
    if err_search("This field is required") and err_search("Please submit 1 or more"):
        errors = err_filter("Please submit 1 or more")
    errors = err_rep("Forms", "Entries")
    errors = err_rep("Form", "Entry")
    errors = err_rep("forms", "entries")
    errors = err_rep("form", "entry")
    return errors
