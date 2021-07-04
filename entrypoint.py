#!/usr/bin/env python3

import boto3
import urllib.request
from urllib.parse import urlparse
from sys import argv
import os
import yaml
import time
from glob import iglob
from uuid import uuid4
from csv import DictReader

from botocore.exceptions import ClientError

start_time = int(time.time())
s3 = boto3.client('s3')
test_id = os.environ.get('TEST_ID')
worker_id = str(uuid4())

print(os.environ)


def s3_upload(file_name, bucket, object_name):
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        print('Error uploading to S3:', e)
        return False
    return True


def download(src: str, dst: str):
    if src.startswith('s3://'):
        parsed_src = urlparse(src)
        s3.download_file(parsed_src.netloc, parsed_src.path[1:], dst)
    else:
        urllib.request.urlretrieve(src, dst)


def put_stats_in_db(csvfile, dyndb_table_out):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(dyndb_table_out)
    with open(csvfile, 'rt') as f:
        for record in DictReader(f):
            if record.get('Name')[0] == '/':
                record['TestID'] = test_id
                record['WorkerID'] = worker_id
                table.put_item(
                    Item=record
                )


os.chdir(os.path.dirname(__file__))

download(argv[1], 'config.yaml')

with open('config.yaml', 'rt') as f:
    config = yaml.full_load(f)

download(config['locust_file'], 'locustfile.py')

cmd = 'locust --headless -H "%(target_url)s" -u "%(num_users)d" -r "%(spawn_rate)d" ' \
      '-t "%(run_time)s" --csv locust_out' % config

print('Running', cmd)
test_start_time = time.time()
os.system(cmd)
test_end_time = time.time()

if dyndb_table_out := config.get('dyndb_table_out'):
    put_stats_in_db('locust_out_stats.csv', dyndb_table_out)

if s3_out := config.get('s3_out'):
    parsed = urlparse(s3_out)
    prefix = parsed.path[1:]

    s3_prefix = f"{prefix}/{test_id}/{worker_id}/"
    print('Uploading csv files to', s3_prefix)
    for fn in iglob('locust_out_*.csv'):
        s3_upload(fn, parsed.netloc, s3_prefix + fn)
    print('Done uploading csv files')

print(f'Load test complete in {int(test_end_time-test_start_time):,} seconds')
