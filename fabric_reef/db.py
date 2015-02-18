# 
# DB Utils
#

from datetime import datetime
from fabric.api import env
from .context import run_web


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