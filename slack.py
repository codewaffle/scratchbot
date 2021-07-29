import argparse
import logging
import re

from slack_bolt.async_app import AsyncApp

import imagine_s3
from secrets import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

logging.basicConfig(level=logging.DEBUG)

app = AsyncApp(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

is_working = False


@app.message(re.compile(r'^\.stop'))
async def on_stop(say):
    global is_working

    if is_working:
        is_working = False
        imagine_s3.stop()
        await say('Imagination stopped!')


@app.message(re.compile(r'^\.imagine'))
async def on_imagine(say, message, client):
    global is_working
    text = message['text'].split('.imagine', 2)[-1].strip()

    if is_working:
        await say('Busy! Try again later.')
        return

    is_working = True

    try:
        result = await say(f'Imagining `{text}`, please wait!')
        print(result)

        response = result.data

        last_image_url = ''

        completion_status = 'COMPLETE'

        for image_url in imagine_s3.imagine_yield_iteration_urls(text):
            last_image_url = image_url
            await client.chat_update(
                channel=response['channel'],
                ts=response['ts'],
                blocks=[{
                    "type": "image",
                    "title": {
                        "type": "plain_text",
                        "text": f'WORKING (type `.stop` to abort): {text}'
                    },
                    "image_url": image_url,
                    "alt_text": text
                }]
            )

            if not is_working:
                completion_status = 'STOPPED'
                break

        # send one final message with completion status
        is_working = False
        await client.chat_update(
            channel=response['channel'],
            ts=response['ts'],
            blocks=[{
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": f'{completion_status}: {text}'
                },
                "image_url": last_image_url,
                "alt_text": text
            }]
        )
    except Exception as exc:
        is_working = False
        await say(f'EXCEPTION:\n```{str(exc)}```')
        return


@app.event('message')
async def handle_unhandled_message():
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', dest='bind', action='store_true')
    args = parser.parse_args()

    if args.bind:
        imagine_s3.bind('tcp://0.0.0.0:4242')
    else:
        # connect to VQGAN service running on another machine (adjust if running on a single machine)
        imagine_s3.connect('tcp://192.168.1.178:4242')

    app.start(3433)
