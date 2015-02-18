# 
# System Utils
#

from fabric.api import env, require, run
from .utils import run_bg


def restart_site():
    """ Gracefully restart gunicorn using supervisor. """
    require('service_name')

    run('supervisorctl reread')
    run('supervisorctl restart %s' % env.service_name)

    flush_memcache()

    # Ping the server for en / nl to ensure compressed assets are created
    # Do this in the background to avoid locking up the fab task
    for lang in ['en', 'nl']:
        run_bg('curl -vLk https://{host}/{lang}'.format(host=env.host, lang=lang))


def flush_memcache():
    run('echo \'flush_all\' | nc -q1 localhost 11211')
