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

import os
import re
import json
import argparse
import feedparser
import filetype
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from email.utils import parsedate_to_datetime
from tqdm import tqdm
from mutagen.id3 import ID3, APIC, COMM, TIT2, TPE1, TALB, TDRL, TDRC, WOAS, ID3NoHeaderError


class CachedRSSFeed:
    def __init__(self, rss_cache_file="rss_cache.json"):
        self.rss_cache_file = rss_cache_file
        self.feeds = self._load_cache()

    def _load_cache(self):
        if not os.path.exists(self.rss_cache_file):
            return {}
        try:
            with open(self.rss_cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {self.cache_file} is corrupted. Starting with empty cache.")
            return {}

    def save_cache(self):
        with open(self.rss_cache_file, "w", encoding="utf-8") as f:
            json.dump(self.feeds, f)

    def get_all_feeds(self):
        return list(self.feeds)

    def is_empty(self):
        return len(self.feeds) == 0

    def fetch(self, url, user_agent):
        saved_etag = self.feeds.get(url, {}).get("etag")
        saved_modified = self.feeds.get(url, {}).get("last-modified")

        feed = feedparser.parse(url, etag=saved_etag, modified=saved_modified, agent=user_agent)

        if not self.feeds.get(url):
            print("New feed!")
        else:
            if feed.get("status") == 304:
                print("Feed not modified (same ETag)")
                return None
            elif not saved_etag:
                if saved_modified:
                    current_modified = feed.get("modified", "")
                    if current_modified:
                        saved_datetime = parsedate_to_datetime(saved_modified)
                        saved_timestamp = saved_datetime.strftime("%s")
                        current_datetime = parsedate_to_datetime(current_modified)
                        current_timestamp = current_datetime.strftime("%s")
                        if saved_timestamp >= current_timestamp:
                            print("Feed not modified (same Last-Modified)")
                            return None
                else:
                    print("Warning: no ETag and no Last-Modified")
                print("New episode(s) available!")

        self.feeds[url] = {
            "etag": feed.get("etag", ""),
            "last-modified": feed.get("modified", ""),
        }

        return feed


class PodcastDownloader:
    def __init__(self, rss_url, user_agent, output_dir="podcasts"):
        self.rss_url = rss_url
        self.output_dir = output_dir
        self.user_agent = user_agent

    def sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "", name)

    def set_metadata(self, mp3_path, metadata, image_url=None):
        print(f"Tagging: {mp3_path}")

        try:
            tags = ID3(mp3_path)
        except ID3NoHeaderError:
            tags = ID3()

        # See https://mutagen.readthedocs.io/en/latest/api/id3_frames.html#id3v2-3-4-frames
        tags.add(TIT2(encoding=3, text=metadata.get("title", "")))
        tags.add(TPE1(encoding=3, text=metadata.get("author", "")))
        tags.add(TALB(encoding=3, text=metadata.get("album", "")))
        tags.add(TDRL(encoding=3, text=metadata.get("date", ""))) # TDRL is release date
 
        # TDRC is recording date and sometimes confused with TYER (which should not be used for an ISO standard date)
        # Easier to remove both tags if present to ensure OwnTone and similar platforms use the correct field for podcast dates
        try:
            tags.pop('TDRC')
        except:
            # Recording date tag not found
            pass
        try:
            tags.pop('TYER')
        except:
            # Year tag not found
            pass

        if "description" in metadata:
            tags.add(
                COMM(
                    encoding=3,
                    lang="eng",
                    desc="desc",
                    text=metadata.get("description", ""),
                )
            )

        if "link" in metadata:
            tags.add(WOAS(url=metadata["link"]))

        if image_url:
            try:
                image_data = urlopen(image_url).read()
                image_mime_type = filetype.guess_mime(image_data)
                if image_mime_type is None:
                    print(f"Warning: can't guess image mime type for {image_url}")
                tags.add(
                    APIC(
                        encoding=3,
                        mime=image_mime_type,
                        type=3,  # cover (front)
                        desc="Cover",
                        data=image_data,
                    )
                )
            except Exception as e:
                print(f"Failed to download or embed image: {e}")

        tags.save(mp3_path)

    def get_audio_url(self, entry):
        for link in entry.links:
            if link.type == "audio/mpeg":
                return link.href
        return None

    def download_file(self, url, dest_path):
        print(f"Downloading: {url}")

        req = Request(url, headers={"User-Agent": self.user_agent})

        try:
            with urlopen(req) as response:
                if response.status != 200:
                    print(f"Failed to download (HTTP {response.status})")
                    return False

                total_size = int(response.getheader("Content-Length", 0))
                block_size = 8192
                with open(dest_path, "wb") as out_file, tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    bar_format="{desc} |{bar}| {percentage:3.0f}% {n_fmt}/{total_fmt}",
                    initial=0,
                ) as bar:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        out_file.write(buffer)
                        bar.update(len(buffer))
                return True

        except HTTPError as e:
            print(f"HTTP Error {e.code}")
        except URLError as e:
            print(f"URL Error: {e.reason}")
        except Exception as e:
            print(f"Download failed: {e}")

        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

    def download(self):
        rss = CachedRSSFeed()
        feed = rss.fetch(self.rss_url, self.user_agent)

        if feed is None:
            print("No new episodes.")
            return

        entries = feed.entries
        print(f"{len(entries)} new episode(s) available.")

        podcast_dir = f"{self.output_dir}/{feed.feed.get("title", "")}"
        os.makedirs(podcast_dir, exist_ok=True)

        for entry in entries:
            published = entry.get("published", "")
            try:
                datetime = parsedate_to_datetime(published)
                date = datetime.strftime("%F")
            except Exception:
                date = "unknown"
            metadata = {
                "title": entry.title,
                "author": entry.get("author", feed.feed.get("author", "")),
                "album": feed.feed.get("title", ""),
                "date": date,
                "description": entry.get("description", ""),
                "link": entry.link,
            }

            image_url = entry.get("image", {}).get("href", None)
            audio_url = self.get_audio_url(entry)

            filename = f"{self.sanitize_filename(metadata.get("title", ""))}.mp3"
            if filename == ".mp3":
                guid = entry.get("guid", None)
                if guid is not None:
                    print("No title found, use GUID as filename")
                    filename = f"{guid}.mp3"
                else:
                    print("No title and no episodeId, skip this episode")
                    continue
            file_path = os.path.join(podcast_dir, filename)

            if not audio_url:
                print(f"Skipping '{metadata.get("link")}' (no MP3 link found)")
                continue

            if not os.path.exists(file_path):
                if self.download_file(audio_url, file_path):
                    self.set_metadata(file_path, metadata, image_url=image_url)
                else:
                    print(f"Skipping metadata for '{metadata.get("title", "")}' due to download failure.")
            else:
                print(f"Already exists: {file_path}")

        rss.save_cache()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download podcast episodes from an Acast RSS feed (or any other podcast platform) and embed metadata into MP3 files."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rss-url", help="Podcast RSS feed URL")
    group.add_argument("--update", action="store_true", help="Update podcasts from rss_cache.json")

    parser.add_argument(
        "--output-dir",
        default="podcasts",
        help="Directory where MP3 files will be saved (default: podcasts)",
    )
    parser.add_argument(
        "--user-agent",
        default="Wget/1.25.0",
        help="Custom User-Agent header (default: Wget/1.25.0)",
    )

    args = parser.parse_args()

    if args.update:
        rss = CachedRSSFeed()
        if rss.is_empty():
            print("Error: rss_cache.json not found or empty. Cannot update.")
            exit(1)
        for feed_url in rss.get_all_feeds():
            print(f"Updating feed: {feed_url}")
            downloader = PodcastDownloader(
                rss_url=feed_url,
                user_agent=args.user_agent,
                output_dir=args.output_dir,
            )
            downloader.download()
    else:
        downloader = PodcastDownloader(
            rss_url=args.rss_url, user_agent=args.user_agent, output_dir=args.output_dir
        )
        downloader.download()
