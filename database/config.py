# -*- coding: utf-8 -*-
import os
import sys
import yaml
import logging
from collections import namedtuple

logger = logging.getLogger(__name__)

ssh_cfg = namedtuple("ssh_cfg", ("host", "hostname", "user", "identity_file", "port", "num_gpu"))


class ConfigParser:
    def __init__(self, fp_cfg: str):
        # config file path
        self.fp_cfg = os.path.realpath(os.path.expanduser(fp_cfg))

        # check if the config file can be opened correctly
        try:
            with open(self.fp_cfg, "r") as fin:
                # check if the config file can be parsed as YAML
                try:
                    self.yaml = yaml.load(fin)
                except yaml.YAMLError as e:
                    logger.fatal("Couldn't parse the config file '{}' as YAML.".format(self.fp_cfg))
                    sys.exit(1)
                logger.info("The config file '{}' has been imported.".format(self.fp_cfg))
        except OSError as e:
            logger.fatal("Couldn't find the config file '{}'.".format(e.filename))
            sys.exit(1)

        # ssh config dict
        self.ssh_cfgs = {}
        for cfg in self.yaml["ssh_cfgs"]:
            # check if the keys of the dict are exist
            try:
                self.ssh_cfgs[cfg["Host"]] = \
                    ssh_cfg(cfg["Host"], cfg["HostName"], cfg["User"], cfg["IdentityFile"], cfg["Port"], cfg["NumGPU"])
            except KeyError as e:
                logger.fatal("Couldn't find the field {} in the config file. Will be terminated.".format(e))
                sys.exit(1)
        logger.info("Load the {} configuration(s) of the servers from the config file.".format(len(self.ssh_cfgs.keys())))

        # sqlite3 database
        self.fp_gpu_db = os.path.realpath(os.path.join(os.path.dirname(__file__), "gpu_database.sqlite3"))
        try:
            self.fp_gpu_db = os.path.join(os.path.dirname(self.fp_cfg), self.yaml["gpu_db"])
            self.fp_gpu_db = os.path.realpath(self.fp_gpu_db)
        except KeyError as e:
            logger.warning("Couldn't find the field {} in the config file. Use the default.".format(e))
        logger.info("The database path is set as '{}'.".format(self.fp_gpu_db))
