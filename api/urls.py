from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static
from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from . import views

urlpatterns = [
    url(r'^api/(?P<slug>[-\w]+)/$', views.index, name='index'),
    ]
