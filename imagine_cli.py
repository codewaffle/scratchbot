import os
import re
import sys
import unicodedata
from time import time

import zerorpc

_rpc_client = zerorpc.Client(heartbeat=20)

# v-- vqgan is running on a windows pc, everything else is running on linux (but all is windows compatible)
_rpc_client.connect('tcp://192.168.1.178:4242')


# slugify borrowed from stackoverflow (who borrowed it from Django)
def slugify(value, allow_unicode=False):
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')

    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


input_text = ' '.join(sys.argv[1:])
assert input_text, 'No prompt provided :('

prompt_base = '{}_{}'.format(time(), slugify(input_text))[:80]
os.makedirs(f'imagine/{prompt_base}', exist_ok=True)

print(f"Imagining '{input_text}'")

for result in _rpc_client.imagine(input_text):
    if not isinstance(result, (tuple, list)):
        raise ValueError("Invalid Result: {}".format(result))

    iter_num, image_bytes = result
    filename = 'imagine/{}/{}.jpg'.format(prompt_base, iter_num)

    with open(filename, 'wb') as output:
        output.write(image_bytes)

    print(f'saved {filename}')
