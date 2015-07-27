#
# Django Utils
#

from .context import *
from .utils import *

def prepare_frontend():
    status_update('Preparing frontend...')
    sudo('npm install -g ember-cli@0.2.5 --unsafe-perm')

    with frontend():
        run_web('npm i && bower i')


def build_frontend(pull_translations=True):
    status_update('Updating frontend...')

    # fetch translations for api and frontend
    if pull_translations:
        with virtualenv():
            run_web('./pull_translations.py --all --deploy')

    with frontend():
        # Building CSS
        run_web('grunt build')

        # Delete any existing build directory
        run_web('rm -Rf dist-latest')

        if env.effective_roles[0] == 'staging':
            ember_env = 'production'
        else:
            ember_env = env.effective_roles[0]

        run_web('LOCALES=all CLIENTS=all ember build --output-path=dist-latest --environment={}'.format(ember_env))


def update_frontend():
    with frontend():
        run_web('rm -Rf dist-previous')
        run_web('mv dist dist-previous')
        run_web('mv dist-latest dist')


def prepare_backend():
    require('django_settings')
    status_update('Preparing backend...')

    with virtualenv():
        # TODO: Filter out the following messages:
        # "Could not find a tag or branch '<commit_id>', assuming commit."

        get_geoip_data()

        # TODO: should we move these pip installs to ansible?
        run_web('pip install --upgrade pip==6.0.8')
        run_web('pip install wheel')

        # Pip install packages for app
        # Remove and compile the .pyc files.
        run_web('find . -name \*.pyc -delete')
        run_web('find ../env/src/ -name \*.pyc -delete')
        run_web('./manage.py compile_pyc --settings=%s' % env.django_settings)

        # Make sure the web user can read and write the static media dir.
        sudo('chmod a+rw static/media')


def update_backend():
    """ Prepare a deployment. """
    require('django_settings')
    status_update('Updating backend...')

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
