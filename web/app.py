# -*-coding:utf-8-*-
import os
import sys
import json
import time
import sqlite3
import logging
import argparse
from contextlib import closing
from datetime import datetime, timedelta

import tornado.autoreload
import tornado.ioloop
import tornado.web
import tornado.websocket

sys.path.append(os.pardir)
from database import config
from database import gpu_database

logger = logging.getLogger(__name__)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

    def data_received(self, chunk):
        pass


class GPUStatusHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.payload_cache = {}
        logger.info("Connection with {} is opened.".format(self.request.remote_ip))
        tornado.ioloop.IOLoop.current().add_timeout(time.time() + 1, self.send_initial_data)

    def on_close(self):
        self.payload_cache = {}
        logger.info("Connection with {} is closed.".format(self.request.remote_ip))

    def on_message(self, message):
        pass

    def data_received(self, chunk):
        pass

    def send_initial_data(self):
        # calc the reference timestamp
        reference_time_stamp = (datetime.now() - timedelta(hours=1)).strftime('%s')
        # create records for each server
        payload = {"status": "initial"}
        # acquire the database
        with closing(sqlite3.connect(cfg.fp_gpu_db)) as gpu_db:
            # acquire the cursor
            cursor = gpu_db.cursor()
            for ssh_cfg in cfg.ssh_cfgs.values():
                # acquire the latest GPU status
                acquire = "SELECT * FROM {} WHERE {} <= local_time_stamp".format(ssh_cfg.host, reference_time_stamp)
                cursor.execute(acquire)
                rows = cursor.fetchall()
                # create a payload
                payload[ssh_cfg.host] = {}
                for row in rows:
                    gpu_info = gpu_database.gpu_info_parser(row)
                    if gpu_info.gpu_index not in payload[ssh_cfg.host].keys():
                        payload[ssh_cfg.host][gpu_info.gpu_index] = {}
                        payload[ssh_cfg.host][gpu_info.gpu_index]["gpu_name"] = gpu_info.gpu_name
                        payload[ssh_cfg.host][gpu_info.gpu_index]["memory_free"] = []
                        payload[ssh_cfg.host][gpu_info.gpu_index]["memory_used"] = []
                        payload[ssh_cfg.host][gpu_info.gpu_index]["memory_total"] = []
                        payload[ssh_cfg.host][gpu_info.gpu_index]["utilization_gpu"] = []
                        payload[ssh_cfg.host][gpu_info.gpu_index]["utilization_memory"] = []
                        payload[ssh_cfg.host][gpu_info.gpu_index]["time_stamp"] = []
                    payload[ssh_cfg.host][gpu_info.gpu_index]["memory_free"].append(gpu_info.memory_free)
                    payload[ssh_cfg.host][gpu_info.gpu_index]["memory_used"].append(gpu_info.memory_used)
                    payload[ssh_cfg.host][gpu_info.gpu_index]["memory_total"].append(gpu_info.memory_total)
                    payload[ssh_cfg.host][gpu_info.gpu_index]["utilization_gpu"].append(gpu_info.utilization_gpu)
                    payload[ssh_cfg.host][gpu_info.gpu_index]["utilization_memory"].append(gpu_info.utilization_memory)
                    payload[ssh_cfg.host][gpu_info.gpu_index]["time_stamp"].append(gpu_info.local_time_stamp)

        self.write_message(json.dumps(payload))
        logger.debug(payload)

        self.payload_cache = self.create_latest_payload()

        tornado.ioloop.IOLoop.current().add_timeout(time.time() + 1, self.send_gpu_status)

    def send_gpu_status(self):
        payload = self.create_latest_payload()

        # check if the payload is updated or not
        if self.payload_cache == payload:
            logger.debug("Not updated.")
        else:
            self.payload_cache = payload
            self.write_message(json.dumps(payload))
            logger.debug("{}".format(payload))

        tornado.ioloop.IOLoop.current().add_timeout(time.time() + 1, self.send_gpu_status)

    def create_latest_payload(self):
        # create records for each server
        payload = {"status": "latest"}
        # acquire the database
        with closing(sqlite3.connect(cfg.fp_gpu_db)) as gpu_db:
            # acquire the cursor
            cursor = gpu_db.cursor()
            for ssh_cfg in cfg.ssh_cfgs.values():
                # acquire the latest GPU status
                acquire = "SELECT * FROM {} " \
                          "ORDER BY local_time_stamp DESC LIMIT {}".format(ssh_cfg.host, ssh_cfg.num_gpu)
                cursor.execute(acquire)
                rows = cursor.fetchall()
                # create a payload
                payload[ssh_cfg.host] = {}
                for row in rows:
                    gpu_info = gpu_database.gpu_info_parser(row)
                    if gpu_info.gpu_index not in payload[ssh_cfg.host].keys():
                        payload[ssh_cfg.host][gpu_info.gpu_index] = {}
                    payload[ssh_cfg.host][gpu_info.gpu_index]["gpu_name"] = gpu_info.gpu_name
                    payload[ssh_cfg.host][gpu_info.gpu_index]["memory_free"] = gpu_info.memory_free
                    payload[ssh_cfg.host][gpu_info.gpu_index]["memory_used"] = gpu_info.memory_used
                    payload[ssh_cfg.host][gpu_info.gpu_index]["memory_total"] = gpu_info.memory_total
                    payload[ssh_cfg.host][gpu_info.gpu_index]["utilization_gpu"] = gpu_info.utilization_gpu
                    payload[ssh_cfg.host][gpu_info.gpu_index]["utilization_memory"] = gpu_info.utilization_memory
                    payload[ssh_cfg.host][gpu_info.gpu_index]["time_stamp"] = gpu_info.local_time_stamp

        return payload


application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/gpu_status", GPUStatusHandler)],
    template_path=os.path.join(os.getcwd(), "templates"),
    static_path=os.path.join(os.getcwd(), "static"),
)

if __name__ == "__main__":
    # format the logger output
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                        format="%(asctime)s: [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser()
    parser.add_argument(help="config file path (config.yaml)", dest="fp_config", type=str)
    args = parser.parse_args()

    # parse the config file
    cfg = config.ConfigParser(args.fp_config)

    local_ip = 8000
    application.listen(local_ip)
    logger.info("Server is up on port {}.".format(local_ip))
    tornado.ioloop.IOLoop.current().start()
