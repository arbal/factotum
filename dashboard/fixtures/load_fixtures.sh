python manage.py flush

python manage.py makemigrations
python manage.py migrate
# specialP@55word
python manage.py loaddata 00_superuser 01_lookups \
    02_datasource 03_datagroup 04_PUC 05_product \
    06_datadocument 07_script 08_extractedtext \
    09_productdocument 10_extractedchemical \
    11_dsstoxsubstance
# Alternate "lite" files
python manage.py loaddata 00_superuser 01_lookups \
    02_datasource 03_datagroup 04_PUC 05_product_lite \
    06_datadocument_lite 07_script 08_extractedtext_lite \
    09_productdocument_lite 10_extractedchemical \
    11_dsstoxsubstance

# some shells prefer one line
python manage.py loaddata 00_superuser 01_lookups 02_datasource 03_datagroup 04_PUC 05_product 06_datadocument 07_script 08_extractedtext   09_productdocument 10_extractedchemical  11_dsstoxsubstance