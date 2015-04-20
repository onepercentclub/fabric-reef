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



@roles('backup')
@task
def restore_db():
    backup_dir = "/home/backups/saas-backups/saas/"
    with cd(backup_dir):
        output = run("ls -1t *.bz2 | head -1")
        try:
            filename = output.split()[0]
        except IndexError:
            print "No database backup file found"

        if filename:
            get(remote_path="{0}/{1}".format(backup_dir, filename), local_path="./dump.sql.bz2")
            confirmed = confirm('Are you sure you want to replace the current database?', default=False)
            if confirmed:
                replace_db("./dump.sql.bz2")
                set_tenant_domains()


def replace_db(filename="./dump.sql.bz2", db_name="saas"):
    local("dropdb {0}".format(db_name))
    local("createdb {0}".format(db_name))
    local("bunzip2 {0} -c | psql {1}".format(filename, db_name))


def set_tenant_domains(domain_base="localhost", db_name="saas"):
    cmd = "UPDATE clients_client SET domain_url = CONCAT(schema_name, '.{0}')".format(domain_base)
    local('echo "{0}" | psql {1}'.format(cmd, db_name))

def run_migrations():
    run_web('./manage.py migrate_schemas --settings=%s' % env.django_settings)


def unpack_db(filename="dump.sql.bz2"):
    try:
        local("bunzip2 {0}".format(filename))
    except IndexError:
        print "No database file found"


@task
def sync_media(local_static_dir="static/"):
    """ Sync media from production backup to local. """
    media_dir = "onepercentclub-backups/onepercentsite/media-backup/media"
    backup_host = "backups@bluebucket.onepercentclub.com"
    local("rsync -chavzP --stats {0}:{1} {2}".format(backup_host, media_dir, local_static_dir))
    print("Done. Now use 'runserver --nostatic' or delete all entries in 'thumbnail_kvstore' table.")

