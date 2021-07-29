import argparse
import logging
import re
from traceback import format_exc

from slack_bolt.async_app import AsyncApp

import imagine
from config import VQGAN_ZERORPC_ADDRESS
from secrets import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

logging.basicConfig(level=logging.DEBUG)

app = AsyncApp(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

is_working = False


@app.message(re.compile(r'^\.stop'))
async def on_stop(say):
    global is_working

    if is_working:
        is_working = False
        imagine.stop()
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

        response = result.data

        last_url = ''

        completion_status = 'COMPLETE'

        for url in imagine.yield_s3_urls_for_prompt(text, compile_gif=True):
            if url.endswith('.gif'):  # BOOOOO slack can't do .mp4 without direct upload, try gifs
                # post videos directly
                await client.chat_postMessage(
                    channel=response['channel'],
                    blocks=[{
                        "type": "image",
                        "title": {
                            "type": "plain_text",
                            "text": f'{text}'
                        },
                        "image_url": url,
                        "alt_text": text
                    }]
                )

            else:
                # otherwise replace existing message
                # need to save this to update the message one last time
                last_url = url

                await client.chat_update(
                    channel=response['channel'],
                    ts=response['ts'],
                    blocks=[{
                        "type": "image",
                        "title": {
                            "type": "plain_text",
                            "text": f'WORKING (type `.stop` to abort): {text}'
                        },
                        "image_url": url,
                        "alt_text": text
                    }]
                )

            if not is_working:
                # allow time to stop after each tieration
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
                "image_url": last_url,
                "alt_text": text
            }]
        )
    except Exception as exc:
        is_working = False

        await say(f'EXCEPTION:\n```{format_exc()}```')
        return


@app.event('message')
async def handle_unhandled_message():
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind')
    args = parser.parse_args()

    if args.bind:
        imagine.bind(args.bind)
    else:
        # connect to VQGAN service running on another machine (adjust if running on a single machine)
        imagine.connect(VQGAN_ZERORPC_ADDRESS)

    app.start(3433)

