# -*-coding:utf-8-*-
import os
import sys
import json
import time
import random
import logging
import argparse

import tornado.autoreload
import tornado.ioloop
import tornado.web
import tornado.websocket

sys.path.append(os.pardir)
from database import config

logger = logging.getLogger(__name__)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

    def data_received(self, chunk):
        pass


class GPUStatusHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        logger.info("Connection is opened")
        tornado.ioloop.IOLoop.current().add_timeout(time.time() + 1, self.send_gpu_status)

    def on_message(self, message):
        pass

    def data_received(self, chunk):
        pass

    def send_initial_data(self):
        self.write_message(
            json.dumps(
                {
                    "Minerva": {
                        "1": {"u": [*range(60)], "m": [*range(60)]},
                        "2": {"u": [*range(60)], "m": [*range(60)]}
                    }
                }
            )
        )

    def send_gpu_status(self):
        self.write_message(
            json.dumps(
                {
                    "Minerva": {
                        "1": {"u": 15 + random.randint(1, 20), "m": 76 + random.randint(1, 20)},
                        "2": {"u": 48 + random.randint(1, 20), "m": 23 + random.randint(1, 20)}
                    }
                }
            )
        )
        tornado.ioloop.IOLoop.current().add_timeout(time.time() + 1, self.send_gpu_status)


application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/gpu_status", GPUStatusHandler)],
    template_path=os.path.join(os.getcwd(), "templates"),
    static_path=os.path.join(os.getcwd(), "static"),
)

if __name__ == "__main__":
    # format the logger output
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s: [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    parser = argparse.ArgumentParser()
    parser.add_argument(help="config file path (config.yaml)", dest="fp_config", type=str)
    args = parser.parse_args()

    # parse the config file
    cfg = config.ConfigParser(args.fp_config)

    application.listen(8000)
    logger.info("Server is up ...")
    tornado.ioloop.IOLoop.current().start()
