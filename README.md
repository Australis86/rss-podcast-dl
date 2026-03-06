# acast_dl.py

The purpose of this script is to easily download podcast episodes from [Acast](https://www.acast.com/) for offline listening.

It also works for other podcast platforms as long as you can get a RSS feed URL (e.g. [Ausha](https://www.ausha.co/), [Radio France](https://www.radiofrance.fr/podcasts), [Megaphone](https://megaphone.spotify.com/), [Simplecast](https://www.simplecast.com/), etc.).

## Limitations

This script: 

- is a wip and has been tested with only a very little set of podcast feeds
- only supports podcasts that use `.mp3` files
- only supports ID3v2.3 and ID3v2.4 tags

## AI Usage

Please note that parts of this script were originally written using [OpenAI](https://openai.com/) [ChatGPT](https://chatgpt.com/) (GPT-4o + GPT-5) as a teammate.

This project was initially an excuse to see how good AI was (in 2025) at helping to write small tools.

# Dependencies

The number of dependencies has been minimised where possible. Currently `acast_dl` relies on four:

- [`feedparser`](https://github.com/kurtmckee/feedparser) for retrieving and parsing the RSS XML feed
- [`mutagen`](https://github.com/quodlibet/mutagen) for updating ID3 MP3 tags
- [`tqdm`](https://github.com/tqdm/tqdm) to show a progress bar when downloading the files
- [`filetype`](https://github.com/h2non/filetype.py) to guess the mime type of cover images

You can either install them with your favorite package manager or install [`uv`](https://docs.astral.sh/uv/) and launch `acast_dl.py` right away. If you do not have `uv` installed then you will either need to modify the shebang or call the script explicitly using Python, e.g.

```
python3 ./acast_dl.py
```

It makes use of [PEP-723](https://peps.python.org/pep-0723/) that allows to add metadata:

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

When launched the first time you'll see `uv` downloading and installing the dependencies:

```
Installed 5 packages in 32ms
 ~ feedparser==6.0.11
 ~ filetype==1.2.0
 ~ mutagen==1.47.0
 ~ sgmllib3k==1.0.0
 ~ tqdm==4.67.1
```

The inspiration to use `uv` is thanks to this blog post : [Fun with uv and PEP 723](https://www.cottongeeks.com/articles/2025-06-24-fun-with-uv-and-pep-723) (related [hn post](https://news.ycombinator.com/item?id=44369388)).

# Usage

```shell
usage: acast_dl.py [-h] (--rss-url RSS_URL | --update) [-d OUTPUT_DIR] [-u USER_AGENT] [-n MAX_DOWNLOAD] [-o] [-4]

Download podcast episodes from an Acast RSS feed (or any other podcast platform that provides a compatible RSS feed) and embed metadata into MP3 files.

options:
  -h, --help            show this help message and exit
  --rss-url RSS_URL     Podcast RSS feed URL
  --update              Update podcasts from rss_cache.json
  -d, --output-dir OUTPUT_DIR
                        Directory where MP3 files will be saved (default: podcasts)
  -u, --user-agent USER_AGENT
                        Set a custom User-Agent header (default: Wget/1.25.0)
  -n, --max-download MAX_DOWNLOAD
                        Only download the N most recent podcast episodes
  -o, --overwrite       Overwrite an existing episode if it already exists
  -4, --id3v24          Write ID3v2.4 tags instead of ID3v2.3 (default)
```

ID3v2.3 has been selected as the default due to its wider support across MP3 playback devices and applications.

# TODO Wishlist

- [ ] add arguments
  - [X] `--overwrite` : overwrite an existing podcast file
  - [ ] `--ignore-rss-cache` : ignore [ETag](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/ETag) and [Last-Modified](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Last-Modified) headers
  - [X] `--max-download` : download only the latest / most recent X podcast episodes
  - [ ] `--cover-as-jpeg` : convert all cover images to JPEG
  - [ ] `--prefix` : prefix MP3 filenames with ??? (pubDate as `YYYY-MM-DD` ? season/episode as `SxEy` (if available) ?)
- [ ] Autodetect language for comments/description if possible

# Similar Projects

Here's a non-exhaustive list, in non-specific order, of similar projects to `acast_dl`, with the programming language noted:

- [acast-rss-downloader](https://github.com/duskmoon314/acast-rss-downloader) (Rust)
- [gocast](https://github.com/philippdrebes/gocast) (Go)

# Legal Notice

This project is an independent tool and is **not affiliated with, endorsed by, or connected to Acast** in any way. Acast is a registered trademark of its respective owner. All other trademarks and service marks are the property of their respective owners.

All podcasts, audio files, images, descriptions, and related metadata retrieved using this tool remain the sole property of their respective creators and copyright holders. This tool is intended for personal, non-commercial use only.

You are responsible for ensuring that your use of any downloaded content complies with applicable copyright laws and the terms of service of the source platform.

# License

The source code of this project is released under the [MIT License](./LICENSE).

This license applies **only** to the project’s code and does **not** extend to any media downloaded or processed with this tool.
