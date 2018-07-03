# drop and replace schema local_factotum

######## At the command prompt:
""" 
python manage.py loaddata prod_20180328
python manage.py loaddata 00_superuser 
"""

from django.contrib.auth.models import User
from dashboard.models import DataSource, DataGroup, DataDocument, ProductDocument, Product, ProductCategory
from django.db.models import Count

# prep the objects by switching their related user to Karyn
karyn = User.objects.get(username='Karyn')

DataGroup.objects.values('downloaded_by__username').annotate(n=Count('id'))
Product.objects.values('puc_assigned_usr_id__username').annotate(n=Count('id'))

DataGroup.objects.all().update(downloaded_by=karyn)
Product.objects.all().update(puc_assigned_usr_id=karyn)

ProductCategory.objects.all().update(last_edited_by=karyn)

# Remove all the real-world users
User.objects.exclude(username='Karyn').delete()

# delete products and datadocuments where their crosswalk id is greater than 200
ProductDocument.objects.filter(id__gt=200).select_related('document').delete()

# Delete the now-unlinked products
Product.objects.exclude(id__in=ProductDocument.objects.all().values('product_id')).delete()

# Delete a few more data groups
DataGroup.objects.filter(id__in=[19,23,24]).delete()

######## At the command prompt:

""" 
python manage.py dumpdata dashboard.grouptype dashboard.documenttype dashboard.unittype dashboard.weightfractiontype dashboard.pucattribute --format=yaml > ./dashboard/fixtures/01_lookups.yaml
python manage.py dumpdata dashboard.datasource --format=yaml > ./dashboard/fixtures/02_datasource.yaml
python manage.py dumpdata dashboard.datagroup --format=yaml > ./dashboard/fixtures/03_datagroup.yaml
python manage.py dumpdata dashboard.PUC --format=yaml > ./dashboard/fixtures/04_PUC.yaml
python manage.py dumpdata dashboard.product --format=yaml > ./dashboard/fixtures/05_product.yaml
python manage.py dumpdata dashboard.datadocument --format=yaml > ./dashboard/fixtures/06_datadocument.yaml
python manage.py dumpdata dashboard.script --format=yaml > ./dashboard/fixtures/07_script.yaml
python manage.py dumpdata dashboard.extractedtext --format=yaml > ./dashboard/fixtures/08_extractedtext.yaml
python manage.py dumpdata dashboard.productdocument --format=yaml > ./dashboard/fixtures/09_productdocument.yaml
python manage.py dumpdata dashboard.extractedchemical --format=yaml > ./dashboard/fixtures/10_extractedchemical.yaml
python manage.py dumpdata dashboard.dsstoxsubstance --format=yaml > ./dashboard/fixtures/11_dsstoxsubstance.yaml
"""
