# imagines things via zeroRPC link to vqgan, uploads results to s3 and returns cloudfront URLs :X
import io
import re
import unicodedata
from time import time

import zerorpc
import boto3

from secrets import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET_NAME, AWS_CLOUDFRONT_BASE_URL

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

_rpc_client = zerorpc.Client(heartbeat=10)


# v-- vqgan is running on a windows pc, everything else is running on linux (but all is windows compatible)


def connect(address):
    _rpc_client.connect(address)


def bind(address):
    _rpc_client.bind(address)


# slugify borrowed from stackoverflow (who borrowed it from Django)
def slugify(value, allow_unicode=False):
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')

    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def imagine_yield_iteration_urls(prompt):
    prompt_base = '{}_{}'.format(time(), slugify(prompt))[:80]

    for result in _rpc_client.imagine(prompt):
        if not isinstance(result, (tuple, list)):
            raise ValueError("Invalid Result: {}".format(result))

        iter_num, image_bytes = result
        print(f'processing iteration {iter_num}')
        im_io = io.BytesIO(image_bytes)

        filename = 'imagine/{}/{}.jpg'.format(prompt_base, iter_num)

        s3.upload_fileobj(im_io, AWS_S3_BUCKET_NAME, filename, {
            'ContentType': 'image/jpeg'
        })

        image_url = f'https://{AWS_CLOUDFRONT_BASE_URL}/{filename}'

        print('uploaded iteration {} to {}'.format(iter_num, image_url))

        yield image_url


def stop():
    _rpc_client.stop()
