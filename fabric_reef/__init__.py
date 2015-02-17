# 
# Utility functions for standard fabric deploys 
#

from datetime import datetime

from fabric.api import env, sudo, prefix, cd, require, run, local, put
from fabric.contrib.files import exists
from fabric.colors import green, red

from contextlib import contextmanager

from git import Repo


VERSION = (1,0,0, 'final')

def _get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2] is not None:
        version = '%s.%s' % (version, VERSION[2])
    if VERSION[3] != 'final':
        if VERSION[4] > 0:
            version = '%s%s%s' % (version, VERSION[3][0], VERSION[4])
        else:
            version = '%s%s' % (version, VERSION[3][0])
    return version

__version__ = _get_version()


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
def frontend():
    require('directory')

    with cd('{}/frontend'.format(env.directory)):
        yield


def status_update(message):
    """ Print status update message. """
    print(green(message))


def run_web(*args, **kwargs):
    """ Run a command as the web user. """
    require('web_user')

    kwargs.setdefault('user', env.web_user)

    return sudo(*args, **kwargs)


def run_bg(cmd, before=None, sockname="dtach", use_sudo=False):
    """Run a command in the background using dtach

    :param cmd: The command to run
    :param before: The command to run before the dtach. E.g. exporting environment variable
    :param sockname: The socket name to use for the temp file
    :param use_sudo: Whether or not to use sudo
    """
    if not exists("/usr/bin/dtach"):
        sudo("apt-get install dtach")
    if before:
        cmd = "{}; dtach -n `mktemp -u /tmp/{}.XXXX` {}".format(before, sockname, cmd)
    else:
        cmd = "dtach -n `mktemp -u /tmp/{}.XXXX` {}".format(sockname, cmd)
    if use_sudo:
        return sudo(cmd)
    else:
        return run(cmd)


# 
# Git Utils
#

def update_tar(commit_id):
    """ Update the remote to given commit_id using tar. """
    require('directory')

    status_update('Transferring archive of commit {0}.'.format(commit_id))

    filename = '{0}.tbz2'.format(commit_id)
    local('git archive {0} | bzip2 -c > {1}'.format(commit_id, filename))
    put(filename, '/tmp')

    with cd(env.directory):
        run_web('tar xjf /tmp/{0}'.format(filename))
        run('rm /tmp/{0}'.format(filename))

    local('rm -f {0}'.format(filename))


def describe_commit(commit):
    """
    Return a verbose commit name based on shortened hash, tags and summary.
    """

    tags = ' '.join(get_commit_tags(commit))

    if tags:
        return '%s %s: %s' % (commit.hexsha[:7], tags, commit.summary)
    else:
        return '%s: %s' % (commit.hexsha[:7], commit.summary)


def get_commit(revspec):
    """
    Find the specified commit by revspec.
    """

    r = Repo()

    # Get the commit from the repo
    commit = r.commit(revspec)
    status_update('Deploying commit %s' % describe_commit(commit))

    return commit


def get_commit_tags(commit):
    """ Get all tags for a commit. """

    r = Repo()

    tags = set()

    for tag in r.tags:
        if tag.commit == commit:
            tags.add(tag.name)

    return tags


def git_fetch_local():
    """ Fetch local GIT updates. """
    local('git fetch -q')


def update_git(commit):
    """ Update the repo to given commit_id. """
    require('directory')

    status_update('Updating git repository to %s' % describe_commit(commit))

    with cd(env.directory):
        # Make sure only to fetch the required branch
        # This script should fail if we are updating to a non-deploy commit
        run_web('git fetch -q -p')
        run_web('git reset --hard')
        run_web('git checkout -q %s' % commit.hexsha)


def add_git_commit():
    with cd(env.directory):
        run_web('echo -e "\nGIT_COMMIT = \'`git log --oneline | head -n1 | cut -c1-7`\'" >> reef/settings/base.py')


# 
# Django Utils
#

def set_django_settings():
    """ Environment-dependant Django settings. """
    require('host')
    environment = env.host.split('.', 1)[0]
    env.django_settings = 'reef.settings.server_%s' % environment


def generate_css():
    # Building CSS
    sudo('gem install bourbon neat')
    
    with frontend():
        with cd('sass/lib'):
            run_web('bourbon install')
            run_web('neat install')

        run_web('npm install')
        run_web('grunt build:css:all')


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


# 
# Misc Utils
#

def backup_db(db_username="reef", db_name="reef", commit=None):
    """ 
        Function to locally backup the database, copy it to the backup server, and then clean the local server backup again. 
        Intended for the 'deploy_production' task.
    """ 

    print("Backing up database - ".format(db_name))
    
    time = datetime.now().strftime('%d-%m-%Y:%H:%M')
    backup_host = env.roledefs['backup'][0]
    backup_path = '/home/backups/{}-backups/'.format(env.service_name)
    backup_name = '{0}-{1}-{2}.sql.bz2'.format(db_name, time, commit)

    # Export the database
    run_web("pg_dump -x --no-owner --username={0} {1} | bzip2 -c > /tmp/{2}".format(db_username, db_name, backup_name))

    # TODO: create the backup directory if it doesn't exist. 
    # Move the database to backup
    print("Copying dump to backup server")
    run_web("scp /tmp/{0} {1}:{2}/".format(backup_name, backup_host, backup_path))

    # Clearup the local database dump
    print("Removing local db dump")
    run_web("rm /tmp/{0}".format(backup_name))


def flush_memcache():
    run('echo \'flush_all\' | nc -q1 localhost 11211')


def get_geoip_data():
    with cd(env.directory):
        run_web('curl https://geolite.maxmind.com/download/geoip/database/GeoLiteCountry/GeoIP.dat.gz | gunzip - > GeoIP.dat')
