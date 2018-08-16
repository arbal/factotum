from haystack.forms import FacetedSearchForm

class FacetedProductSearchForm(FacetedSearchForm):
  def __init__(self, *args, **kwargs):
    data = dict(kwargs.get("data", []))
    self.pucs = data.get('pucs', [])
    self.brands = data.get('brand_name', [])
    self.models = data.get('facet_model_name',[])
    self.group_types = data.get('group_type',[])
    super(FacetedProductSearchForm, self).__init__(*args, **kwargs)

  def search(self):
    sqs = super(FacetedProductSearchForm, self).search()
    # The SearchQuerySet should only return Products and Data Documents
    sqs = sqs.filter(facet_model_name__in=['Data Document' ,'Product'])
    #print(sqs.facet_counts())
    if self.pucs:
        query = None
        for puc in self.pucs:
            if query:
                query += u' OR '
            else:
                query = u''
            query += u'"%s"' % sqs.query.clean(puc)
        sqs = sqs.narrow(u'puc:%s' % query)
    if self.group_types:
        query = None
        for group_type in self.group_types:
            if query:
                query += u' OR '
            else:
                query = u''
            query += u'"%s"' % sqs.query.clean(group_type)
        sqs = sqs.narrow(u'group_type:%s' % query)
    if self.brands:
        query = None
        for brand in self.brands:
            if query:
                query += u' OR '
            else:
                query = u''
            query += u'"%s"' % sqs.query.clean(brand)
        sqs = sqs.narrow(u'brand_name_exact:%s' % query)
    if self.models:
        query = None
        for model in self.models:
            if query:
                query += u' OR '
            else:
                query = u''
            query += u'"%s"' % sqs.query.clean(model)
        sqs = sqs.narrow(u'facet_model_name:%s' % query)
    return sqs
