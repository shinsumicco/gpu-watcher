# -*- coding: utf-8 -*-
import os
import sys
import time
import sqlite3
import logging
import paramiko
import argparse
from contextlib import closing
from collections import namedtuple
from datetime import datetime as dt
from datetime import timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

logger = logging.getLogger(__name__)
logging.getLogger("paramiko").setLevel(logging.WARNING)

gpu_info = namedtuple("gpu_info", ("gpu_index", "gpu_name",
                                   "memory_free", "memory_used", "memory_total",
                                   "utilization_gpu", "utilization_memory",
                                   "remote_time_stamp", "local_time_stamp"))


class Database:
    def __init__(self, cfg: config.ConfigParser):
        self.cfg = cfg

    def refresh(self):
        # acquire the database
        with closing(sqlite3.connect(self.cfg.fp_gpu_db)) as gpu_db:
            # acquire the cursor
            cursor = gpu_db.cursor()
            # create records for each server
            for ssh_cfg in self.cfg.ssh_cfgs.values():
                # create a table if it doesn't exist
                create_table = "CREATE TABLE IF NOT EXISTS {} " \
                               "(gpu_index INT, gpu_name VARCHAR(64), " \
                               "memory_free INT, memory_used INT, memory_total INT, " \
                               "utilization_gpu INT, utilization_memory INT, " \
                               "remote_time_stamp TIMESTAMP, local_time_stamp TIMESTAMP)".format(ssh_cfg.host)
                cursor.execute(create_table)
                gpu_db.commit()

                # acquire the GPU statuses
                current_statuses = self.__nvidia_smi(ssh_cfg)
                if current_statuses is not None and 0 < len(current_statuses):
                    logger.info("Acquired the GPU status from {} ({}).".format(ssh_cfg.hostname, ssh_cfg.host))

                    # insert the records
                    insert = "INSERT INTO {} " \
                             "(gpu_index, gpu_name, " \
                             "memory_free, memory_used, memory_total, " \
                             "utilization_gpu, utilization_memory," \
                             "remote_time_stamp, local_time_stamp) VALUES (?,?,?,?,?,?,?,?,?)".format(ssh_cfg.host)
                    for current_status in current_statuses:
                        cursor.execute(insert, list(current_status))

                # delete the old records
                delete = "DELETE FROM {} " \
                         "WHERE local_time_stamp <= ?".format(ssh_cfg.host)
                outdated_time_stamp = (dt.now() - timedelta(days=7)).strftime('%s')
                cursor.execute(delete, [outdated_time_stamp])

                # commit the database
                gpu_db.commit()

                # count the number of records for each server
                if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
                    count = "SELECT COUNT(*) from {}".format(ssh_cfg.host)
                    cursor.execute(count)
                    num = cursor.fetchall()[0][0]
                    logger.debug("The table for {} has {} records.".format(ssh_cfg.host, num))

    def __nvidia_smi(self, ssh_cfg: config.ssh_cfg):
        logger.info("Connect to {} ({}).".format(ssh_cfg.hostname, ssh_cfg.host))

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            pkey = paramiko.RSAKey.from_private_key_file(ssh_cfg.identity_file)
        except OSError as e:
            logger.fatal("Couldn't find the private key file '{}'.".format(e.filename))
            return None

        try:
            # connect to the server
            ssh.connect(ssh_cfg.hostname, username=ssh_cfg.user, port=ssh_cfg.port, pkey=pkey, timeout=10.0)

            # execute nvidia-smi
            _, stdout, _ = ssh.exec_command("nvidia-smi "
                                            "--query-gpu=index,gpu_name,"
                                            "memory.free,memory.used,memory.total,"
                                            "utilization.gpu,utilization.memory,timestamp "
                                            "--format=csv,noheader,nounits")

            # parse the output
            rets = str(stdout.read())[2:-3].split("\\n")

            # parse the output according to gpu_info
            current_statuses = []
            for ret in rets:
                raw_status = ret.split(", ")
                status = gpu_info(int(raw_status[0]), raw_status[1],
                                  int(raw_status[2]), int(raw_status[3]), int(raw_status[4]),
                                  int(raw_status[5]), int(raw_status[6]),
                                  dt.strptime(raw_status[7][:-4], "%Y/%m/%d %H:%M:%S").strftime("%s"), dt.now().strftime("%s"))
                current_statuses.append(status)
        except paramiko.SSHException as e:
            logger.fatal("Couldn't create a SSH session with {} ({}). {}".format(ssh_cfg.hostname, ssh_cfg.host, e.args[0]))
            current_statuses = None
        finally:
            # disconnect the ssh session
            ssh.close()

        return current_statuses


def main():
    while True:
        database.refresh()
        time.sleep(5)


def fork():
    pid = os.fork()
    if pid > 0:
        pid_file = open("/var/run/gpu-database.pid", "w")
        pid_file.write(str(pid) + "\n")
        pid_file.close()
        sys.exit()
    if pid == 0:
        main()


if __name__ == "__main__":
    # format the logger output
    logging.basicConfig(filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpu_database.log"),
                        level=logging.INFO,
                        format="%(asctime)s: [%(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser()
    parser.add_argument(dest="fp_config", help="config file path (config.yaml)", type=str)
    parser.add_argument("--daemon", dest="daemon", help="run as a daemon", action="store_true")
    args = parser.parse_args()

    # parse the config file
    cfg = config.ConfigParser(args.fp_config)

    # refresh the database
    database = Database(cfg)

    if args.daemon:
        # daemonize the process
        if os.getuid() != 0:
            sys.stderr.write("Running as daemon process needs sudo!\n")
            exit(1)
        fork()
    else:
        # while loop
        main()
