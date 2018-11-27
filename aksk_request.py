from xmljson import badgerfish as bf
from json import dumps
import json
import logging
import sys
import os
import base64
import datetime
import hashlib
import hmac
from xml.etree.ElementTree import fromstring
import requests


def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'aws4_request')
    return kSigning


def request_aksk(method, service, host, region, endpoint,
                 request_parameters, c_type, account):
    access = {}
    secret = {}
    access["aws"] = {"awsmicloud": "AKIAIQ54UZ2WFN73JQIQ"}
    secret["aws"] = {"awsmicloud": "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"}

    access["ksy"] = {"xiaomi": "AKLT3xjKdGxYQhus1v3GbCa53g"}
    secret["ksy"] = {
        "xiaomi": "OBQMSA9KipSaQynHEbzzaNkRfC8YQlNSXuH8ha7Lruq1r/vit8A+628adnklozd+FQ=="}

    access["ali"] = {"hw_xiaomi": "LTAIv6nfJIKfzX4G"}
    secret["ali"] = {"hw_xiaomi": "SHe8xYbvcblkjMq7qX24yB9NpccknE"}

    access_key = access[c_type][account]
    secret_key = secret[c_type][account]
    #
    # access_key = decrypt_aksk(cfg['aksk'][c_type][account]['ak'])
    # secret_key = decrypt_aksk(cfg['aksk'][c_type][account]['sk'])

    if access_key is None or secret_key is None:
        print('No access key is available.')
        sys.exit()

    # Create a date for headers and the credential string
    t = datetime.datetime.utcnow()
    amzdate = t.strftime('%Y%m%dT%H%M%SZ')
    datestamp = t.strftime('%Y%m%d')  # Date w/o time, used in credential scope

    # Step 2: Create canonical URI--the part of the URI from domain to query
    # string (use '/' if no path)
    canonical_uri = '/'

    # For this example, the query string is pre-formatted in the
    # request_parameters variable.
    canonical_querystring = request_parameters
    canonical_headers = 'host:' + host + '\n' + 'x-amz-date:' + amzdate + '\n'
    signed_headers = 'host;x-amz-date'

    # Create payload hash (hash of the request body content). For GET
    # requests, the payload is an empty string ("").
    payload_hash = hashlib.sha256("".encode("utf-8")).hexdigest()
    # payload_hash = ""
    # Combine elements to create canonical request
    canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + \
        '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash

    # Match the algorithm to the hashing algorithm you use, either SHA-1 or
    # SHA-256 (recommended)
    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = datestamp + '/' + region + \
        '/' + service + '/' + 'aws4_request'
    string_to_sign = algorithm + '\n' + amzdate + '\n' + credential_scope + \
        '\n' + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()

    # Create the signing key using the function defined above.
    signing_key = getSignatureKey(secret_key, datestamp, region, service)

    # Sign the string_to_sign using the signing_key
    signature = hmac.new(
        signing_key,
        (string_to_sign).encode('utf-8'),
        hashlib.sha256).hexdigest()
    # Create authorization header and add to request headers
    authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + \
        credential_scope + ', ' + 'SignedHeaders=' + \
        signed_headers + ', ' + 'Signature=' + signature
    headers = {'x-amz-date': amzdate, 'Authorization': authorization_header}

    # ************* SEND THE REQUEST *************
    request_url = endpoint + '?' + canonical_querystring

    logging.debug('\nBEGIN REQUEST++++++++++++++++++++++++++++++++++++')
    logging.debug('Request URL = ' + request_url)
    r = requests.get(request_url, headers=headers)

    logging.debug('\nRESPONSE++++++++++++++++++++++++++++++++++++')
    if r.status_code != 200:
        logging.debug('Response code: %d\n' % r.status_code)
        return ""

    json_str = dumps(bf.data(fromstring(r.text)))
    json1 = json.loads(json_str)
    return json1
