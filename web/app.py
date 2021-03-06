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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import config
from database import gpu_database

logger = logging.getLogger(__name__)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        hosts = []
        for ssh_cfg in cfg.ssh_cfgs.values():
            hosts.append(ssh_cfg.host)
        self.render(
            "index.html",
            hosts=hosts,
            bind_ip_port=bind_ip_port
        )

    def data_received(self, chunk):
        pass


class GPUStatusHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

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
        payload_data = {}
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
                payload_data[ssh_cfg.host] = {}
                for row in rows:
                    gpu_info = gpu_database.gpu_info(*row)
                    if gpu_info.gpu_index not in payload_data[ssh_cfg.host].keys():
                        # initialize as a dict
                        payload_data[ssh_cfg.host][gpu_info.gpu_index] = {}
                        payload_data[ssh_cfg.host][gpu_info.gpu_index]["gpu_name"] = gpu_info.gpu_name
                        # initialize as lists
                        payload_data[ssh_cfg.host][gpu_info.gpu_index]["memory_free"] = []
                        payload_data[ssh_cfg.host][gpu_info.gpu_index]["memory_used"] = []
                        payload_data[ssh_cfg.host][gpu_info.gpu_index]["memory_total"] = []
                        payload_data[ssh_cfg.host][gpu_info.gpu_index]["utilization_gpu"] = []
                        payload_data[ssh_cfg.host][gpu_info.gpu_index]["utilization_memory"] = []
                        payload_data[ssh_cfg.host][gpu_info.gpu_index]["time_stamp"] = []
                    # append to the lists
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["memory_free"].append(gpu_info.memory_free)
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["memory_used"].append(gpu_info.memory_used)
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["memory_total"].append(gpu_info.memory_total)
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["utilization_gpu"].append(gpu_info.utilization_gpu)
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["utilization_memory"].append(gpu_info.utilization_memory)
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["time_stamp"].append(gpu_info.local_time_stamp)

        payload = {"status": "initial", "data": payload_data}

        try:
            self.write_message(json.dumps(payload))
        except tornado.websocket.WebSocketClosedError:
            pass
        logger.debug(payload)

        # cache the payload in order to check if the last record is updated or not
        self.payload_cache = self.create_latest_payload()

        tornado.ioloop.IOLoop.current().add_timeout(time.time() + 1, self.send_gpu_status)

    def send_gpu_status(self):
        payload = self.create_latest_payload()

        # check if the payload is updated or not
        if self.payload_cache == payload:
            logger.debug("Not updated.")
        else:
            self.payload_cache = payload
            try:
                self.write_message(json.dumps(payload))
            except tornado.websocket.WebSocketClosedError:
                pass
            logger.debug("{}".format(payload))

        tornado.ioloop.IOLoop.current().add_timeout(time.time() + 1, self.send_gpu_status)

    def create_latest_payload(self):
        # create records for each server
        payload_data = {}
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
                payload_data[ssh_cfg.host] = {}
                for row in rows:
                    gpu_info = gpu_database.gpu_info(*row)
                    if gpu_info.gpu_index not in payload_data[ssh_cfg.host].keys():
                        payload_data[ssh_cfg.host][gpu_info.gpu_index] = {}
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["gpu_name"] = gpu_info.gpu_name
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["memory_free"] = gpu_info.memory_free
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["memory_used"] = gpu_info.memory_used
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["memory_total"] = gpu_info.memory_total
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["utilization_gpu"] = gpu_info.utilization_gpu
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["utilization_memory"] = gpu_info.utilization_memory
                    payload_data[ssh_cfg.host][gpu_info.gpu_index]["time_stamp"] = gpu_info.local_time_stamp

        payload = {"status": "latest", "data": payload_data}

        return payload


application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/gpu_status", GPUStatusHandler)],
    template_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
    static_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
    debug=True
)

if __name__ == "__main__":
    # format the logger output
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s: [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser()
    parser.add_argument(help="config file path (config.yaml)", dest="fp_config", type=str)
    parser.add_argument("--bind_ip", "-b", help="ip address which will be embedded in index.html", dest="bind_ip", type=str, default="localhost")
    args = parser.parse_args()

    # parse the config file
    cfg = config.ConfigParser(args.fp_config)

    bind_ip = args.bind_ip
    logger.info("Server is at: {}.".format(bind_ip))

    local_port = 8000
    application.listen(local_port)

    bind_ip_port = "{0}:{1}".format(bind_ip, local_port)

    logger.info("Server is up on port {}.".format(local_port))
    tornado.ioloop.IOLoop.current().start()
