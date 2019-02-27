# activate the environment
source activate factotum

# flush the database
python manage.py flush

# make migrations
python manage.py makemigrations
python manage.py migrate

# specialP@55word

# load fixtures

# rebuild the search engine index
python manage.py rebuild_index

# relaunch the server
python manage.py runserver

# run test suite
python manage.py test dashboard.tests