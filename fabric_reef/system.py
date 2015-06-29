# 
# System Utils
#

from fabric.api import env, require, run, sudo
from .utils import run_bg
from .context import virtualenv, run_web


def restart_site():
    """ Gracefully restart gunicorn using supervisor. """
    require('service_name')

    sudo('supervisorctl reread')
    sudo('supervisorctl restart %s' % env.service_name)

    # Restart Celery services
    sudo('supervisorctl restart celery')
    sudo('supervisorctl restart celerybeat')

    flush_memcache()

    with virtualenv():
        run_web('./manage.py warmup --settings=%s' % env.django_settings)


def flush_memcache():
    run('echo \'flush_all\' | nc -q1 localhost 11211')
