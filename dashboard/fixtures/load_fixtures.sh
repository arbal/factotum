python manage.py flush

python manage.py makemigrations
python manage.py migrate
# specialP@55word
python manage.py loaddata 00_superuser 01_lookups \
    02_datasource 03_datagroup 04_PUC 05_product \
    06_datadocument 08_extractedtext 065_rawchem_etc \
    07_script  09_productdocument  12_habits_and_practices \
    13_habits_and_practices_to_puc 14_product_to_puc   18_puc_tag


# some shells prefer one line
<<<<<<< HEAD
python manage.py loaddata 00_superuser 01_lookups 02_datasource 03_datagroup 04_PUC 05_product 06_datadocument 08_extractedtext 065_rawchem_etc 07_script  09_productdocument  12_habits_and_practices 13_habits_and_practices_to_puc 14_product_to_puc   18_puc_tag
=======
python manage.py loaddata 00_superuser 01_lookups 02_datasource 03_datagroup 04_PUC 05_product 06_datadocument 065_rawchem_etc 07_script 08_extractedtext 09_productdocument 12_habits_and_practices 13_habits_and_practices_to_puc 14_product_to_puc 15_extractedfunctionaluse  16_extractedcpcat 17_extractedlistpresence 18_puc_tag
>>>>>>> dev
