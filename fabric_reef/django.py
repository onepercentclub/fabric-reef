#
# Django Utils
#

from .context import *
from .utils import *

def prepare_frontend():
    status_update('Preparing frontend...')


    sudo('gem install bourbon neat')
    sudo('npm install -g ember-cli@0.2.5 --unsafe-perm')
    
    with frontend():
        run_web('npm i && bower i')

        with cd('sass/lib'):
            run_web('bourbon install')
            run_web('neat install')


def generate_frontend():
    status_update('Generating frontend...')

    # fetch translations for api and frontend
    with virtualenv():
        run_web('./pull_translations.py --all')
    
    with frontend():
        # Building CSS
        run_web('grunt build:css:all --env={}'.format(env.sass_env))
        run_web('LOCALES=all CLIENTS=all ember build --environment={}'.format(env.effective_roles[0]))


def prepare_backend():
    require('django_settings')

    status_update('Preparing Django...')

    with virtualenv():
        # TODO: Filter out the following messages:
        # "Could not find a tag or branch '<commit_id>', assuming commit."

        get_geoip_data()

        # TODO: should we move these pip installs to ansible?
        run_web('pip install --upgrade pip==6.0.8')
        run_web('pip install wheel')

        # Pip install packages for app
        run_web('pip install --use-mirrors --use-wheel --process-dependency-links --find-links=https://stream.onepercentclub.com/wheelhouse/ -r requirements/requirements.txt')

        # Remove and compile the .pyc files.
        run_web('find . -name \*.pyc -delete')
        run_web('./manage.py compile_pyc --settings=%s' % env.django_settings)

        # Make sure the web user can read and write the static media dir.
        sudo('chmod a+rw static/media')


def update_app():
    """ Prepare a deployment. """
    require('django_settings')

    status_update('Updating app...')
    generate_frontend()

    with virtualenv():

        # compile api translations
        run_web('./manage.py compilepo --settings=%s' % env.django_settings)

        # Update public schema
        run_web('./manage.py sync_schemas --shared --noinput --settings=%s' % env.django_settings)
        run_web('./manage.py migrate_schemas --shared --noinput --settings=%s' % env.django_settings)

        # Update all schemas
        run_web('./manage.py sync_schemas --noinput --settings=%s' % env.django_settings)
        run_web('./manage.py migrate_schemas --noinput --settings=%s' % env.django_settings)

        run_web('./manage.py collectstatic -l -v 0 --noinput --settings=%s' % env.django_settings)
