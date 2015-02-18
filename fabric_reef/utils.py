# 
# Fabric Common Utils
#

from fabric.api import env, sudo, cd, run
from fabric.contrib.files import exists
from fabric.colors import green, red
from .context import run_web


def status_update(message):
    """ Print status update message. """
    print(green(message))


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


def get_geoip_data():
    with cd(env.directory):
        run_web('curl https://geolite.maxmind.com/download/geoip/database/GeoLiteCountry/GeoIP.dat.gz | gunzip - > GeoIP.dat')
