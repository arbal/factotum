from dashboard.models import *

def get_extracted_models(t):
    '''Returns the parent model function and and the associated child model
    based on datagroup type'''
    def one():
        return (ExtractedText.objects.get_or_create, ExtractedChemical)

    def two():
        return (ExtractedText.objects.get_or_create, ExtractedFunctionalUse)

    def three():
        return (ExtractedCPCat.objects.get_or_create, ExtractedListPresence)

    models = {
        'Composition': one,
        'Functional use': two,
        'Chemical presence list': three
    }
    func = models.get(t, lambda: None)
    return func()

def clean_dict(odict, model):
    return {f.name:odict[f.name]
            for f in model._meta.get_fields()
            if f.name in odict.keys()}

def update_fields(odict, model):
    '''Takes a dict and updates the associated fields w/in the model'''
    for f in model._meta.get_fields():
        if f.name in odict.keys():
            setattr(model,f.name,odict[f.name])
