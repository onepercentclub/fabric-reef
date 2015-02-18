# 
# Git Utils
#

from fabric.api import env, cd, require, run, local, put
from git import Repo
from .context import run_web


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



