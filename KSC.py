from kscore.session import get_session
import json
import time
import logging
from datetime import datetime, timedelta
from cloud2falcon import PERIOD
from ks3.connection import Connection


def get_one_metric(namespace, region, metricname, period, id):
    s = get_session()
    client = s.create_client("monitor", region, use_ssl=True)
    now = datetime.now()
    start = datetime.now() - timedelta(days=2)
    ISOFORMAT = "%Y-%m-%dT%XZ"
    m = client.get_metric_statistics(
        InstanceID=id,
        Namespace=namespace,
        MetricName=metricname,
        StartTime=start.strftime(ISOFORMAT),
        EndTime=now.strftime(ISOFORMAT),
        Period='86400',
        Aggregate='Max'
    )
    return json.dumps(m, sort_keys=True, indent=4)


def get_metric_data(period, namespace, name, id_list,
                    metricname, ak, sk, region):
    metric_data = []
    ISOFORMAT = "%Y-%m-%dT%XZ"
    for id in id_list:
        if metricname == 'BandWidth':
            ts = time.time()
            t = int(ts)
            data = {"id": id['l'], "ip": id['d'], "region": region['site'], "metric": metricname,
                    "time": t, "value": id['BandWidth']}
            metric_data.append(data)
            continue
        response = json.loads(
            get_one_metric(
                name,
                region['name'],
                metricname,
                period,
                id['l']))
        try:
            metric_list = response['getMetricStatisticsResult']['datapoints']['member']
            for metric in metric_list:
                # t = int(metric['timestamp'].timestamp())
                ts = time.strptime(metric['timestamp'], ISOFORMAT)
                t = int(time.mktime(ts))
                data = {"id": id['l'], "ip": id['d'], "region": region['site'], "metric": metricname,
                        "time": t, "value": metric['max']}
                metric_data.append(data)
        except BaseException:
            logging.error('responce from ksc error')
    metric_data.sort(key=lambda x: x["time"])
    return metric_data


def get_id(resource, ak, sk, region):
    if resource == "elb":
        return elb(ak, sk, region)
    elif resource == "eip":
        return eip(ak, sk, region)
    elif resource == "nat":
        return nat(ak, sk, region)
    elif resource == "KS3":
        return s3(ak, sk, region)


def elb(ak, sk, region):
    id = []
    s = get_session()
    region = region
    slbClient = s.create_client("slb", region, use_ssl=False)
    allLB = slbClient.describe_load_balancers()
    for item in allLB['LoadBalancerDescriptions']:
        try:
            id.append({"l": item['LoadBalancerId'], "d": item['PublicIp']})
        except BaseException:
            logging.error(
                'can not get data from slb : ' +
                item['LoadBalancerId'])
    return id


def eip(ak, sk, region):
    id = []
    s = get_session()
    region = region
    eipClient = s.create_client("eip", region, use_ssl=True)
    allEips = eipClient.describe_addresses(
        **{'Filter.1.Name': 'instance-type', 'Filter.1.Value.1': 'Ipfwd'})
    for item in allEips['AddressesSet']:
        id.append({"l": item['AllocationId'], "d": item['PublicIp']})
    return id


def nat(ak, sk, region):
    s = get_session()
    id = []
    region = region
    vpcClient = s.create_client("vpc", region, use_ssl=True)
    allVpcs = vpcClient.describe_nats()
    for item in allVpcs['NatSet']:
        id.append({"l": item['NatId'],
                   "d": item['NatName'],
                   "BandWidth": item['BandWidth']})
    return id


def s3(ak, sk, region):
    id = []
    if region == "cn-beijing-6":
        endpoint = "ks3-cn-beijing.ksyun.com"
    elif region == "cn-shanghai-2":
        endpoint = "ks3-cn-shanghai.ksyun.com"
    elif region == "eu-east-1":
        endpoint = "ks3-rus.ksyun.com"
    elif region == "ap-singapore-1":
        endpoint = "ks3-sgp.ksyun.com"
    else:
        endpoint = ""
    c = Connection(ak, sk, host=endpoint, is_secure=False, domain_mode=False)
    buckets = c.get_all_buckets()
    for b in buckets:
        id.append({"l": b.name, "d": ''})
    return id
