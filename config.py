# -*- coding: utf-8 -*-
import os
import sys
import yaml
import logging
from collections import namedtuple

logger = logging.getLogger(__name__)

ssh_cfg = namedtuple("ssh_cfg", ("host", "hostname", "user", "identity_file", "port"))


class ConfigParser:
    def __init__(self, fp_cfg):
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
                    ssh_cfg(cfg["Host"], cfg["HostName"], cfg["User"], cfg["IdentityFile"], cfg["Port"])
            except KeyError as e:
                logger.fatal("Invalid config style: couldn't find the field '{}'. Will be terminated.".format(e))
                sys.exit(1)
