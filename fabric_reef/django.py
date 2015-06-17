#
# Django Utils
#

from .context import *
from .utils import *


def generate_css():
    # Building CSS
    sudo('gem install bourbon neat')

    with frontend():
        with cd('sass/lib'):
            run_web('bourbon install')
            run_web('neat install')

        run_web('npm install')
        run_web('grunt build:css:all --env={}'.format(env.sass_env))


def generate_ember():
    with frontend():
        run_web('bower install')
        run_web('./patch.sh')
        run_web('LOCALES=all CLIENTS=all ./node_modules/.bin/ember build')


def prepare_django():
    """ Prepare a deployment. """
    require('django_settings')

    status_update('Preparing deployment.')

    generate_css()

    get_geoip_data()

    with virtualenv():
        # TODO: Filter out the following messages:
        # "Could not find a tag or branch '<commit_id>', assuming commit."

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

        # Update public schema
        run_web('./manage.py sync_schemas --shared --noinput --settings=%s' % env.django_settings)
        run_web('./manage.py migrate_schemas --shared --noinput --settings=%s' % env.django_settings)

        # Update all schemas
        run_web('./manage.py sync_schemas --noinput --settings=%s' % env.django_settings)
        run_web('./manage.py migrate_schemas --noinput --settings=%s' % env.django_settings)

        # Fetch and compile translations
        #run_web('./manage.py txpull --deploy --all --settings=%s' % env.django_settings)
        run_web('./manage.py txpull --frontend --deploy --all --settings=%s' % env.django_settings)
        run_web('./manage.py compilepo --settings=%s' % env.django_settings)

        generate_ember();
        run_web('./manage.py makejs --settings=%s' % env.django_settings)

        # Create default fonts / css directories if they don't exist.
        # This is needed on first deploy when there are no tenants.
        run_web('mkdir -p frontend/static/fonts')
        run_web('mkdir -p frontend/static/css')

        # Collect static assets
        run_web('./manage.py tenant_collectstatic -l -v 0 --noinput --settings=%s' % env.django_settings)
