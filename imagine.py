# imagines things via zeroRPC link to vqgan, uploads results to s3 and returns cloudfront URLs :X
import io
import os.path
import re
import sys
import tempfile
from time import time

import unicodedata
import zerorpc

from config import VQGAN_ZERORPC_ADDRESS, VIDEO_FRAME_RATE

client = zerorpc.Client(heartbeat=10)


def connect(address):
    client.connect(address)


def bind(address='tcp://0.0.0.0:424'):
    client.bind(address)


# slugify borrowed from stackoverflow (who borrowed it from Django)
def slugify(value, allow_unicode=False):
    value = str(value)

    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')

    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def yield_images_for_prompt(prompt):
    for packed_result in client.imagine(prompt):
        if not isinstance(packed_result, (tuple, list)):
            raise ValueError(f'{packed_result}')

        _, image_bytes = packed_result

        yield image_bytes


def yield_s3_urls_for_prompt(prompt, image_every=25, compile_video=False, compile_gif=False):
    import boto3
    from secrets import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET_NAME, AWS_CLOUDFRONT_BASE_URL

    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    prompt_base = f'{time()}_{slugify(prompt)}'[:80]

    if compile_video or compile_gif:
        temp_dir = tempfile.mkdtemp()
    else:
        temp_dir = None

    for idx, image_bytes in enumerate(yield_images_for_prompt(prompt)):
        if temp_dir:
            with open(os.path.join(temp_dir, f'{idx:05d}.jpg'), 'wb') as fp:
                fp.write(image_bytes)

        if idx % image_every == 0:
            # upload an image
            im_io = io.BytesIO(image_bytes)
            filename = f'imagine/{prompt_base}/{idx}.jpg'

            s3.upload_fileobj(im_io, AWS_S3_BUCKET_NAME, filename, {
                'ContentType': 'image/jpeg'
            })

            image_url = f'https://{AWS_CLOUDFRONT_BASE_URL}/{filename}'

            yield image_url

    # done, compile video if requested
    if compile_video:
        # meh would be easier for me to use ffmpeg here but..
        # fine just use ffmpeg (with system no less, too lazy right now)
        tmp_filename = os.path.join(temp_dir, prompt_base + ".mp4")

        # convert jpgs to mp4 with ffmpeg
        os.system(f'ffmpeg -r {VIDEO_FRAME_RATE} -i {os.path.join(temp_dir, "%05d.jpg")} -vcodec libx264 -y {tmp_filename}')

        # upload mp4 to s3
        s3.upload_file(tmp_filename, AWS_S3_BUCKET_NAME, f'imagine/{prompt_base}.mp4', {
            'ContentType': 'video/mp4'
        })

        # yield it
        yield f'https://{AWS_CLOUDFRONT_BASE_URL}/imagine/{prompt_base}.mp4'

    # ugh Slack doesn't inline videos... i guess try gifs, lots of duplication here
    if compile_gif:
        tmp_filename = os.path.join(temp_dir, prompt_base + ".gif")

        # convert jpgs to mp4 with ffmpeg
        os.system(f'ffmpeg -r 24 -i {os.path.join(temp_dir, "%05d.jpg")} -y {tmp_filename}')

        # upload mp4 to s3
        s3.upload_file(tmp_filename, AWS_S3_BUCKET_NAME, f'imagine/{prompt_base}.gif', {
            'ContentType': 'image/gif'
        })

        # yield it
        yield f'https://{AWS_CLOUDFRONT_BASE_URL}/imagine/{prompt_base}.gif'

    # TODO : clean up temp files?


def stop():
    client.stop()


def main():
    connect(VQGAN_ZERORPC_ADDRESS)

    prompt = ' '.join(sys.argv[1:])
    assert prompt, 'No prompt provided :('

    prompt_base = f'{time()}_{slugify(prompt)}'[:80]
    os.makedirs(f'imagine/{prompt_base}', exist_ok=True)

    print(f"Imagining '{prompt}'")

    for idx, image_bytes in enumerate(yield_images_for_prompt(prompt)):
        filename = f'imagine/{prompt_base}/{idx:03d}.jpg'

        with open(filename, 'wb') as output:
            output.write(image_bytes)

        print(f'saved {filename}')

    print('Compiling video')
    video_filename = os.path.join('imagine', prompt_base + '.mp4')
    # convert jpgs to mp4 with ffmpeg
    os.system(f'ffmpeg -r {VIDEO_FRAME_RATE} -i {os.path.join("imagine", prompt_base, "%03d.jpg")} -vcodec libx264 -y {video_filename}')

    print(f'Video saved at {video_filename}')


# run imagine as a CLI instead
if __name__ == '__main__':
    main()
