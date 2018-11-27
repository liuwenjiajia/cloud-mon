#!/usr/bin/env python
# -*- coding:utf-8 -*-

import log
import yaml
import time
import datetime
import threading
import jinja2
import requests
import json
import logging

from xmljson import badgerfish as bf
from json import dumps
from xml.etree.ElementTree import fromstring
from multiCloud import get_id_list, get_metric_data


with open('config.yml', 'r') as ymlfile:
    cfg = yaml.load(ymlfile)
ymlfile.close()
PERIOD = cfg['period']


def render_without_request(template_name, **context):
    """
    useage same as flask.render_template:

    render_without_request('template.html', var1='foo', var2='bar')
    """
    env = jinja2.Environment(
        loader=jinja2.PackageLoader('cloud2falcon', 'templates')
    )
    template = env.get_template(template_name)
    return template.render(**context)


def xml_to_json(xml):
    r = dumps(bf.data(fromstring(xml)))
    return r


def send_to_falcon(json_model, template_name):
    payload = render_without_request(template_name, metrics=json_model)
    # print payload
    data1 = json.loads(payload)
    r = requests.post(cfg['falcon_url'], data=json.dumps(data1))
    if r.status_code != 200:
        logging.error("send to falcon failed", r.json())


def peach_send_to_falcon(namespace, name, instance_id,
                         metric, c_type, ak, sk, region, tempalte):
    metric_data = get_metric_data(
        cfg['step'],
        namespace,
        name,
        instance_id,
        metric,
        c_type,
        ak,
        sk,
        region)
    if metric_data:
        send_to_falcon(metric_data, tempalte)


def get_metric_json(resource):
    sub_threads = []
    for region in resource['region']:
        id = get_id_list(
            resource['c_type'],
            resource['resource'],
            resource['ak'],
            resource['sk'],
            region['name'])
        for metric in resource['metric_list']:
            logging.info(
                'process start for ' +
                metric +
                "  " +
                resource['c_type'])
            namespace = resource['c_type'] + "/" + resource['resource']
            t = threading.Thread(
                target=peach_send_to_falcon,
                args=(
                    namespace,
                    resource['name'],
                    id,
                    metric,
                    resource['c_type'],
                    resource['ak'],
                    resource['sk'],
                    region,
                    resource['to_falcon_template']
                ))
            sub_threads.append(t)

    for i in range(len(sub_threads)):
        sub_threads[i].start()


if __name__ == "__main__":
    log.setup_logging("logging.yml")
    start_time = datetime.datetime.utcnow()
    threads = []
    for res in cfg['cloud']:
        logging.info('start main process to get config')
        # multiple process
        t = threading.Thread(target=get_metric_json, args=(res, ))
        threads.append(t)
    for i in range(len(threads)):
        threads[i].start()
