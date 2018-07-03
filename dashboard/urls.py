from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static
from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from . import views

urlpatterns = [
	url(r'^$', views.index, 				name='index'),
	url(r'^datasources/$', views.data_source_list,
											name='data_source_list'),
	url(r'^datasource/(?P<pk>\d+)$', views.data_source_detail,
											name='data_source_detail'),
	url(r'^datasource/new$', views.data_source_create,
											name='data_source_new'),
	url(r'^datasource/edit/(?P<pk>\d+)$', views.data_source_update,
											name='data_source_edit'),
	url(r'^datasource/delete/(?P<pk>\d+)$', views.data_source_delete,
											name='data_source_delete'),
	url(r'^datagroups/$', views.data_group_list,
											name='data_group_list'),
	url(r'^datagroup/(?P<pk>\d+)$', views.data_group_detail,
											name='data_group_detail'),
	url(r'^datagroup/docs_csv/(?P<pk>\d+)$', views.dg_dd_csv_view,
											name='dg_dd_csv_view'),
	url(r'^datagroup/new$', views.data_group_create,
											name='data_group_new'),
	url(r'^datagroup/edit/(?P<pk>\d+)$', views.data_group_update,
											name='data_group_edit'),
	url(r'^datagroup/delete/(?P<pk>\d+)$', views.data_group_delete,
											name='data_group_delete'),
	url(r'^product_curation/$', views.product_curation_index,
											name='product_curation'),
	url(r'^product_curation/$', views.product_curation_index,
											name='product_curation'),
	url(r'^category_assignment/(?P<pk>\d+)$', views.category_assignment,
											name='category_assignment'),
	url(r'^link_product_list/(?P<pk>\d+)$', views.link_product_list,
											name='link_product_list'),
	url(r'^link_product_form/(?P<pk>\d+)$', views.link_product_form,
											name='link_product_form'),
	url(r'^qa/extractionscript/(?P<pk>\d+)$', views.extraction_script_qa,
											name='extraction_script_qa'),
	url(r'^qa/extractedtext/(?P<pk>\d+)$', views.extracted_text_qa,
											name='extracted_text_qa'),
	url(r'^extractionscript/(?P<pk>\d+)$', views.extraction_script_detail,
											name='extraction_script_detail'),
	url(r'^qa/$', views.qa_index, 			name='qa'),
	url(r'^product_puc/(?P<pk>\d+)$', views.assign_puc_to_product,
											name='product_puc'),
	url(r'^puc-autocomplete/$',
					views.product_autocomplete.PUCAutocomplete.as_view(),
											name='puc-autocomplete'),
	url(r'^product/(?P<pk>\d+)$', views.product_detail,
											name='product_detail'),
    url(r'^products/$', views.product_list, name='product_list'),
    url(r'^datadocument/(?P<pk>\d+)$', views.data_document_detail,
											name='data_document'),
    url(r'^search/', include('haystack.urls')),
    url(r'^find/', views.search.FacetedSearchView.as_view(),
											name='haystack_search'),
    url(r'^p_json/', views.product_ajax, 	name='p_ajax_url'),
	url(r'^chem_search/', views.chem_search, name='chem_search'),
    #url(r'^search/', FacetedSearchView(form_class=FacetedSearchForm, facet_fields=['brand_name','prod_cat']), name='haystack_search'),
	# test with: /puc-autocomplete/?q=Art
]

if settings.DEBUG is True:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
