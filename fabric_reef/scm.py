# 
# Git Utils
#

from fabric.api import env, cd, require, run, local, put
from git import Repo
from .context import run_web
from .utils import status_update


def assert_release_tag(commit, tag):
    """
    Make sure the given commit has the given tag and confirm if not so.
    """
    tags = get_commit_tags(commit)

    # Match a single string as to ignore versions in "tag-<VERSION>"
    if not tag in ' '.join(tags):
        # It's not found, confirm with user
        confirm_wrong_tag(commit, tag)


def make_versioned_tag(tag, version):
    """ Generate a versioned version of a tag. """
    return '%s-%d' % (tag, version)


def tag_commit(commit_id, tag):
    """
    Tag the specified commit and push it to the server.
    Overwriting old tags with the same name.
    """
    local('git tag %s %s' % (tag, commit_id))
    local('git push origin %s' % tag)


def find_latest_tag_version(tag):
    """ Find the latest version for the given tag. Returns an integer. """
    r = Repo()

    version = 1
    while make_versioned_tag(tag, version+1) in r.tags:
        version += 1

    status_update(
        'Latest version for tag %s is %d: %s' % \
            (tag, version, make_versioned_tag(tag, version))
    )

    return version


def find_available_tag(tag):
    """
    Find the latest available version for a versioned tag of the form tag-N.
    """
    latest_version = find_latest_tag_version(tag)
    new_tag = make_versioned_tag(tag, latest_version+1)

    return new_tag


def confirm_wrong_tag(commit, tag):
    """ Confirm deployment when commit does not have expected tag. """
    require('noinput')

    print(red('WARNING: This commit does not have the %s tag.' % tag))

    if not env.noinput:
        confirmed = confirm('Are you really sure you want to deploy %s?' % commit.hexsha, default=False)

        if not confirmed:
            abort('Confirmation required to continue.')


def update_tar(commit_id):
    """ Update the remote to given commit_id using tar. """
    require('directory')

    log = run_web('echo ${GITHUB_AUTH:?"Need to set GITHUB_AUTH"}')
    if 'Need to set' in log:
        raise Exception('GITHUB_AUTH env required for production deploy')

    status_update('Fetching archive of commit {0}.'.format(commit_id))

    filepath = '/tmp/{0}.tar.gz'.format(commit_id)
    run_web('curl -H "Authorization: token $GITHUB_AUTH" -L https://api.github.com/repos/onepercentclub/reef/tarball/{0} > {1}'.format(commit_id, filepath))
    
    with cd(env.directory):
        run_web('tar zxvf {0} --strip 1'.format(filepath))
        run_web('rm {0}'.format(filepath))


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



