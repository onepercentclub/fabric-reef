# 
# Django Utils
#

from .context import *
from .utils import *


def set_django_settings():
    """ Environment-dependant Django settings. """
    require('host')
    environment = env.host.split('.', 1)[0]
    env.django_settings = 'reef.settings.server_%s' % environment


def generate_css(env='dev'):
    # Building CSS
    sudo('gem install bourbon neat')
    
    with frontend():
        with cd('sass/lib'):
            run_web('bourbon install')
            run_web('neat install')

        run_web('npm install')
        run_web('grunt build:css:all --env={}'.format(env))


def prepare_django():
    """ Prepare a deployment. """
    set_django_settings()

    require('django_settings')

    status_update('Preparing deployment.')

    generate_css()

    get_geoip_data()

    with virtualenv():
        # TODO: Filter out the following messages:
        # "Could not find a tag or branch '<commit_id>', assuming commit."
        run_web('pip install --use-mirrors --use-wheel --process-dependency-links --find-links=https://stream.onepercentclub.com/wheelhouse/ -r requirements/requirements.txt')

        # Remove and compile the .pyc files.
        run_web('find . -name \*.pyc -delete')
        run_web('./manage.py compile_pyc --settings=%s' % env.django_settings)

        # Fetch and compile translations
        run_web('./manage.py txpull --all --settings=%s' % env.django_settings)
        run_web('./manage.py compilepo --settings=%s' % env.django_settings)

        # Make sure the web user can read and write the static media dir.
        sudo('chmod a+rw static/media')

        run_web('./manage.py sync_schemas --migrate --noinput --settings=%s' % env.django_settings)
        run_web('./manage.py tenant_collectstatic -l -v 0 --noinput --settings=%s' % env.django_settings)
