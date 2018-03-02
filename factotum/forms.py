from haystack.forms import FacetedSearchForm

class FacetedProductSearchForm(FacetedSearchForm):
  def __init__(self, *args, **kwargs):
    data = dict(kwargs.get("data", []))
    self.categories = data.get('prod_cat', [])
    self.brands = data.get('brand_name', [])
    self.models = data.get('facet_model_name',[])
    super(FacetedProductSearchForm, self).__init__(*args, **kwargs)

  def search(self):
    sqs = super(FacetedProductSearchForm, self).search()
    if self.categories:
        query = None
    for category in self.categories:
        if query:
            query += u' OR '
        else:
            query = u''
        query += u'"%s"' % sqs.query.clean(category)
        sqs = sqs.narrow(u'prod_cat:%s' % query)
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