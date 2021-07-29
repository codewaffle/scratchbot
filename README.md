# What is this?

A very rough first iteration of a chat bot that "imagines" images using CLIP+VQGAN, completely inspired by `BATBot`, a
bot written and maintained by BoneAmputee and running on EleutherAI's Discord server.

The CLIP/VQGAN implementation itself was heavily borrowed
from https://colab.research.google.com/drive/1ZAus_gn2RhTZWzOWUpPERNC0Q8OhZRTZ which bears the following additional
credits:
> Originally made by Katherine Crowson (https://github.com/crowsonkb, https://twitter.com/RiversHaveWings). The original BigGAN+CLIP method was by https://twitter.com/advadnoun. Added some explanations and modifications by Eleiber#8347, pooling trick by Crimeacs#8222 (https://twitter.com/EarthML1) and the GUI was made with the help of Abulafia#3734.

The bot commands are directly inspired by the command set offered by BATBot.

8GB+ of VRAM is required.

# How do I use it?

This project has not seen ANY polishing or refinement yet, so ou'll have to read the code and figure it out yourself for
the most part. Dependency information can be found in the comments at the top of `vqgan.py`, but assumes that pytorch
and cuda are already working in an Anaconda distribution...

`requirements.txt` is pending.

Roughly:

- `vqgan.py` runs a ZeroRPC server that offers `imagine(input_text)` and `stop()` commands that the other pieces connect
  to.
- `slack.py` runs a Slack bot that interacts with `imagine.py` to upload images to S3 and return CloudFront URLs.
    - Requires `secrets.py` to be present and configured with AWS and Slack credentials (see `secrets.example.py`)
- `imagine.py` can also be run as a stand-alone command-line alternative to `slack.py` that outputs images and video to
  a local subfolder and requires no external cloud accounts.

# License

MIT with assumptions that all MIT-licensed source materials are legitimately MIT (I did say this was a very rough first
iteration...).

Use at your own risk.
