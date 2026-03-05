# acast_dl.py

The purpose of this script is to easily download podcast episodes from [Acast](https://www.acast.com/) for offline listening.

It also works for other podcast platforms as long as you can get a RSS feed URL (e.g. [Ausha](https://www.ausha.co/), [Radio France](https://www.radiofrance.fr/podcasts), etc.).

## Limitations

- this script is currently a wip and has been tested with only a very little set of podcast feeds
- this script only support `.mp3` files

## AI usage

Please note that parts of this script has been written using [OpenAI](https://openai.com/) [ChatGPT](https://chatgpt.com/) (GPT-4o + GPT-5) as a teammate.

This project is an excuse to see how good AI is at helping to write small tools (I always have lots of ideas but don't have time to implement them).

# Dependencies

I have tried to keep the number of depencies as low as possible.

Currently `acast_dl` relies on four:

- [`feedparser`](https://github.com/kurtmckee/feedparser) for retrieving and parsing the RSS XML feed
- [`mutagen`](https://github.com/quodlibet/mutagen) for updating ID3 MP3 tags
- [`tqdm`](https://github.com/tqdm/tqdm) to show a progress bar when downloading the files
- [`filetype`](https://github.com/h2non/filetype.py) to guess the mime type of cover images

You can either install them with your favorite package manager or install [`uv`](https://docs.astral.sh/uv/) and launch `acast_dl.py` right away. If you do not have `uv` installed then you will either need to modify the shebang or call the script explicitly using Python, e.g.

```
python3 ./acast_dl.py
```

It makes use of [PEP-723](https://peps.python.org/pep-0723/) that allows to add metadata :

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "feedparser",
#     "mutagen",
#     "tqdm",
#     "filetype"
# ]
# ///
```

When launched the first time you'll see `uv` downloading and installing the dependencies :

```
Installed 5 packages in 32ms
 ~ feedparser==6.0.11
 ~ filetype==1.2.0
 ~ mutagen==1.47.0
 ~ sgmllib3k==1.0.0
 ~ tqdm==4.67.1
```

I got the inspiration to use `uv` thanks to this blog post : [Fun with uv and PEP 723](https://www.cottongeeks.com/articles/2025-06-24-fun-with-uv-and-pep-723) (related [hn post](https://news.ycombinator.com/item?id=44369388)).

# Usage

```shell
TODO
```

# TODO

- [ ] Update this `README.md` file
  - [ ] "Usage" chapter
- [ ] add arguments
  - [ ] `--overwrite` : overwrite any already downloaded podcast file
  - [ ] `--ignore-rss-cache` : ignore [ETag](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/ETag) and [Last-Modified](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Last-Modified) headers
  - [ ] `--max-download` : download only the latest / most recent X podcast episodes
  - [ ] `--cover-as-jpeg` : convert all cover images to JPEG
  - [ ] `--prefix` : prefix MP3 filenames with ??? (pubDate as `YYYY-MM-DD` ? season/episode as `SxEy` (if available) ?)
- [ ] Autodetect language for comments/description if possible

# Similar projects

Here's a non-exhaustive list, in non-specific order, of similar projects to `acast_dl` :

- [acast-rss-downloader](https://github.com/duskmoon314/acast-rss-downloader)
- [gocast](https://github.com/philippdrebes/gocast)

# Legal Notice

This project is an independent tool and is **not affiliated with, endorsed by, or connected to Acast** in any way.
Acast is a registered trademark of its respective owner. All other trademarks and service marks are the property of their respective owners.

All podcasts, audio files, images, descriptions, and related metadata retrieved using this tool remain the sole property of their respective creators and copyright holders. This tool is intended for personal, non-commercial use only.

You are responsible for ensuring that your use of any downloaded content complies with applicable copyright laws and the terms of service of the source platform.

# License

The source code of this project is released under the [MIT License](./LICENSE).

This license applies **only** to the project’s code and does **not** extend to any media downloaded or processed with this tool.
