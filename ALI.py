import json
import logging
import datetime
import oss2
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.client import AcsClient
from aliyunsdkslb.request.v20140515 import DescribeLoadBalancersRequest
from aliyunsdkvpc.request.v20160428 import DescribeEipAddressesRequest
from aliyunsdkvpc.request.v20160428 import DescribeNatGatewaysRequest
from cloud2falcon import PERIOD


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i: i + n]


def get_metric_data(period, namespace, name, id_list,
                    metricname, ak, sk, region):
    metric_data = []
    for id in list(chunks(id_list, 50)):
        data = get_metric_data_50(
            period,
            namespace,
            name,
            id,
            metricname,
            ak,
            sk,
            region)
        metric_data += data
    return metric_data


def get_metric_data_50(period, namespace, name, id_list,
                       metricname, ak, sk, region):
    metric_data = []
    clt = AcsClient(ak, sk, region['name'])
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('metrics.cn-hangzhou.aliyuncs.com')
    request.set_method('POST')
    request.set_version('2018-03-08')
    request.set_action_name('QueryMetricList')
    request.add_query_param('Metric', metricname)
    request.add_query_param('Period', period)
    request.add_query_param('Project', name)
    request.add_query_param(
        'StartTime',
        datetime.datetime.now() -
        datetime.timedelta(
            minutes=PERIOD))
    request.add_query_param('EndTime', datetime.datetime.now())
    list = []
    for instance_id in id_list:
        if (name == "acs_nat_gateway" and metricname == "SnatConnection") \
                or name == "acs_publicip"\
                or name == "acs_express_connect":
            list.append({'instanceId': str(instance_id['d'])})
        elif name == "acs_oss":
            list.append({'BucketName': str(instance_id['d'])})
        else:
            list.append({'instanceId': str(instance_id['l'])})

    request.add_query_param('Dimensions', list)
    response = clt.do_action_with_exception(request)
    response1 = str(response)
    response1 = json.loads(response1)
    try:
        data = response1['Datapoints']
        data1 = json.loads(data)
        if name == "acs_slb_dashboard":
            for record in data1:
                timeStamp = int(record['timestamp'] / 1000)
                data = {"id": record['instanceId'], "ip": record['vip'], "region": region['site'], "metric": metricname,
                        "time": timeStamp, "value": record['Average']}
                # print(data)
                metric_data.append(data)
        elif name == "acs_nat_gateway" and metricname == "SnatConnection":
            for record in data1:
                timeStamp = int(record['timestamp'] / 1000)
                data = {"id": record['instanceId'], "ip": "", "region": region['site'], "metric": metricname,
                        "time": timeStamp, "value": record['Maximum']}
                # print(data)
                metric_data.append(data)
        elif name == "acs_publicip":
            for record in data1:
                timeStamp = int(record['timestamp'] / 1000)
                data = {"id": '', "ip": record['ip'], "region": region['site'], "metric": metricname,
                        "time": timeStamp, "value": record['value']}
                # print(data)
                metric_data.append(data)
        elif name == "acs_oss":
            for record in data1:
                timeStamp = int(record['timestamp'] / 1000)
                data = {"id": record['BucketName'], "ip": '', "region": region['site'], "metric": metricname,
                        "time": timeStamp, "value": record[metricname]}
                # print(data)
                metric_data.append(data)
        else:
            for record in data1:
                timeStamp = int(record['timestamp'] / 1000)
                data = {"id": record['instanceId'], "ip": '', "region": region['site'], "metric": metricname,
                        "time": timeStamp, "value": record['Value']}
                # print(data)
                metric_data.append(data)
    except BaseException:
        logging.debug("no data responce: " + metricname)

    metric_data.sort(key=lambda x: x["time"])
    return metric_data


def get_id(resource, ak, sk, region):
    if resource == "ELB":
        return elb(ak, sk, region)
    elif resource == "EIP":
        return eip(ak, sk, region)
    elif resource == "NAT":
        return nat(ak, sk, region)
    elif resource == "connect":
        return connect(ak, sk, region)
    elif resource == "oss":
        return oss(ak, sk, region)


def elb(ak, sk, region):
    id = []
    client = AcsClient(ak, sk, region)
    request = DescribeLoadBalancersRequest.DescribeLoadBalancersRequest()
    request.set_accept_format('json')
    response = client.do_action_with_exception(request)
    response1 = str(response)
    response1 = json.loads(response1)
    for record in response1['LoadBalancers']['LoadBalancer']:
        id.append({"l": record['LoadBalancerId'], "d": record['Address']})
    return id


def eip(ak, sk, region):
    id = []
    client = AcsClient(ak, sk, region)
    request = DescribeEipAddressesRequest.DescribeEipAddressesRequest()
    request.set_accept_format('json')
    response = client.do_action_with_exception(request)
    response1 = str(response)
    response1 = json.loads(response1)
    id = []
    for record in response1['EipAddresses']['EipAddress']:
        id.append({"l": record['AllocationId'], "d": record['IpAddress']})
    return id


def nat(ak, sk, region):
    id = []
    client = AcsClient(ak, sk, region)
    request = DescribeNatGatewaysRequest.DescribeNatGatewaysRequest()
    request.set_accept_format('json')
    response = client.do_action_with_exception(request)
    response1 = str(response)
    response1 = json.loads(response1)
    for record in response1['NatGateways']['NatGateway']:
        for band in record['BandwidthPackageIds']['BandwidthPackageId']:
            id.append({"l": band, "d": record['NatGatewayId']})
    return id


def connect(ak, sk, region):
    id = []
    client = AcsClient(ak, sk, region)
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('vpc.aliyuncs.com')
    request.set_method('POST')
    request.set_version('2016-04-28')
    request.set_action_name('DescribeRouterInterfaces')
    request.add_query_param('PageSize', '50')
    response = client.do_action_with_exception(request)
    response1 = str(response)
    response1 = json.loads(response1)
    for record in response1['RouterInterfaceSet']['RouterInterfaceType']:
        id.append({"l": record['Bandwidth'],
                   "d": record['OppositeInterfaceId']})
    return id


def oss(ak, sk, region):
    id = []
    auth = oss2.Auth(ak, sk)
    service = oss2.Service(auth, 'http://oss-cn-hangzhou.aliyuncs.com')
    for b in oss2.BucketIterator(service):
        id.append({"l": "", "d": b.name})

    return id
