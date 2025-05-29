# dialer-reports-django
Yeastar dialer reports platform build in Django

## Installation
1. Create virtual environment
   - python -m venv .ven
2. Activate venv
   - .venv/scripts/activate
3. Install dependancies from requirements.txt
   - pip install -r requirements.txt
4. cd to the main project folder 'core' where the manage.py file is situated and run migrations
   - python manage.py makemigrations
   - python manage.py migrate
5. Create a superuser
   - python manage.py createsuperuser
       i  enter email
       ii enter password
6. Start dev server to test
   - python manage.py runserver
   
