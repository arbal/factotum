# activate the environment
source activate factotum

# flush the database
python manage.py flush

# make migrations
python manage.py makemigrations
python manage.py migrate

# specialP@55word
python manage.py loaddata 00_superuser 01_lookups 02_datasource \
    03_datagroup 04_productcategory 05_product 06_datadocument 07_script \
    08_extractedtext 09_productdocument 10_extractedchemical 11_dsstoxsubstance

# rebuild the search engine index
python manage.py rebuild_index

# relaunch the server
python manage.py runserver

# run test suite
python manage.py test dashboard.tests