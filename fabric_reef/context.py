# 
# Fabric Context Utils
#

from datetime import datetime
from fabric.api import env, sudo, prefix, cd, require
from contextlib import contextmanager


@contextmanager
def virtualenv():
    """
    Make sure everything is executed from within the virtual environment.

    Example::

        with virtualenv():
            run('./manage.py collectstatic')

    """
    require('directory')

    with cd(env.directory):
        with prefix('source {0}/bin/activate'.format(env.virtualenv_dir_name)):
            yield


@contextmanager
def maintenance():
    run_web('ln -sf /var/www/maintenance.html /var/www/maintenance_on.html')
    yield
    run_web('rm /var/www/maintenance_on.html')


@contextmanager
def frontend():
    require('directory')

    with cd('{}/frontend'.format(env.directory)):
        yield


def run_web(*args, **kwargs):
    """ Run a command as the web user. """
    require('web_user')

    kwargs.setdefault('user', env.web_user)

    return sudo(*args, **kwargs)