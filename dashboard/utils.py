from dashboard.models import *

def get_extracted_models(t):
    '''Returns the parent model function and and the associated child model
    based on datagroup type'''
    def one():
        return (ExtractedText, ExtractedChemical)

    def two():
        return (ExtractedText, ExtractedFunctionalUse)

    def three():
        return (ExtractedCPCat, ExtractedListPresence)

    def four():
        return (ExtractedText, ExtractedHabitsAndPractices)

    models = {
        'CO': one,
        'FU': two,
        'CP': three,
        'HP': four,
        'UN': one
    }
    func = models.get(t, lambda: None)
    return func()

def clean_dict(odict, model):
    '''Cleans out key:value pairs that aren't in the model fields
    '''
    return {f.name:odict[f.name]
            for f in model._meta.get_fields()
            if f.name in odict.keys()}

def update_fields(odict, model):
    '''Takes a dict and updates the associated fields w/in the model'''
    for f in model._meta.get_fields():
        if f.name in odict.keys():
            setattr(model,f.name,odict[f.name])
