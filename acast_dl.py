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
from mutagen.id3 import ID3, APIC, COMM, TIT2, TPE2, TALB, TDRL, WOAS, ID3NoHeaderError


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

    def fetch(self, url, user_agent, ignore_cache=False, storage_path=None, file_prefix=None):
        if ignore_cache:
            print("Warning: ignoring RSS cache - treating feed as new")
            saved_etag = None
            saved_modified = None
            saved_path = storage_path
            saved_prefix = file_prefix
        else:
            saved_etag = self.feeds.get(url, {}).get("etag")
            saved_modified = self.feeds.get(url, {}).get("last-modified")
            saved_path = self.feeds.get(url, {}).get("storage_path")
            saved_prefix = self.feeds.get(url, {}).get("file_prefix")

        # This retrieves the RSS feed and should return the feed entries in their original order
        # (as per https://feedparser.readthedocs.io/en/latest/common-rss-elements/), e.g. newest to oldest
        feed = feedparser.parse(url, etag=saved_etag, modified=saved_modified, agent=user_agent)
   
        if not self.feeds.get(url):
            feed_title = feed.feed.get("title", "")
            print(f"New feed: {feed_title} ")
            self.feeds[url] = {
                "title": feed_title, # Store the title so it is easy to identify each entry in the JSON cache if manual editing is required
                "storage_path": storage_path,
                "file_prefix": file_prefix,
            }
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
                elif not ignore_cache:
                    print("Warning: no ETag and no Last-Modified found in feed -- updating from cache will not work!")
                print("New episode(s) available!")

        self.feeds[url].update({
            "etag": feed.get("etag", ""),
            "last-modified": feed.get("modified", ""),
            "updated": feed.get("feed", {}).get("updated", ""),
        })

        return (feed, saved_path, saved_prefix)


class PodcastDownloader:
    def __init__(self, rss_url, user_agent, output_dir="podcasts", episode_cnt=None, ignore_cache=False, overwrite=False, prefix=None, id3v24=False):
        self.rss_url = rss_url
        self.output_dir = output_dir
        self.user_agent = user_agent
        self.episode_cnt = episode_cnt
        self.ignore_cache = ignore_cache
        self.overwrite = overwrite
        self.prefix = prefix
        if id3v24:
            self.id3version2=4
        else:
            self.id3version2=3

    def sanitize_filename(self, name):
        name = re.sub(r':', " -", name) # Substitute colon with a hyphen to make titles more readable
        name = re.sub(r'[\\/*?:"<>|]', "", name) # Remove unsafe characters
        return re.sub(' +', ' ', name) # Remove any double spaces caused by character replacement

    def set_metadata(self, mp3_path, metadata, image_url=None):
        print(f"Tagging: {mp3_path}")

        try:
            tags = ID3(mp3_path, v2_version=self.id3version2)
        except ID3NoHeaderError:
            tags = ID3()

        # See https://mutagen.readthedocs.io/en/latest/api/id3_frames.html#id3v2-3-4-frames
        tags.add(TIT2(encoding=3, text=metadata.get("title", "")))

        # Set the album artist field (TPE2) rather than artist field (TPE1),
        # as this is more appropriate for podcast authors/RSS feed authors
        tags.add(TPE2(encoding=3, text=metadata.get("author", "")))
        tags.add(TALB(encoding=3, text=metadata.get("album", "")))

        # Set the release date field (TDRL) rather than recording date (TDRC) or year (TYER)
        # since the RSS feed provides the episode publication date
        tags.add(TDRL(encoding=3, text=metadata.get("date", "")))

        # It is easier to remove both TDRC and TYER tags if present to ensure OwnTone and similar applications
        # use the correct date field for the podcast episode publication/release date
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

        tags.save(mp3_path, v2_version=self.id3version2)

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
        (feed, storage_path, file_prefix) = rss.fetch(self.rss_url, self.user_agent, self.ignore_cache, self.output_dir, self.prefix)

        if feed is None:
            print("No new episodes.")
            return

        entries = feed.entries

        # Check if number of new episodes exceeds limit
        available = len(entries)
        if self.episode_cnt is not None and available > self.episode_cnt:
            print(f"{available} new episodes available; only downloading first {self.episode_cnt} episode(s).")
            cntr_limit = self.episode_cnt
        else:
            print(f"{available} new episode(s) available.")
            cntr_limit = available

        print()

        podcast_dir = f"{(storage_path or self.output_dir)}/{self.sanitize_filename(feed.feed.get("title", ""))}"
        podcast_dir = os.path.normpath(podcast_dir)
        os.makedirs(podcast_dir, exist_ok=True)
        print(f"Downloading to {podcast_dir} ...")

        for i, entry in enumerate(entries):
            cntr=i+1
            print(f"{cntr}/{cntr_limit}\t{entry.title}")

            published = entry.get("published", "")
            try:
                datetime = parsedate_to_datetime(published)
                # mutagen ID3TimeStamp object is a restricted ISO 8601 timestamp
                # can be full timestamp, date or just year
                date_str = datetime.strftime("%Y-%m-%d ")
                datetime_str = datetime.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                date_str = ""
                datetime_str = "unknown"
            metadata = {
                "title": entry.title,
                "author": entry.get("author", feed.feed.get("author", "")),
                "album": feed.feed.get("title", ""),
                "date": datetime_str,
                "description": entry.get("description", ""),
                "link": entry.link,
            }
            
            # Check if season/episode metadata available
            # Fallback to ISO date as string if not
            prefix_arg = file_prefix or self.prefix
            if prefix_arg == 'episode':
                try:
                    season = entry.itunes_season
                    episode = entry.itunes_episode
                    prefix = f"S{season}E{episode} "
                except Exception as e:
                    prefix = date_str
            elif prefix_arg == 'date':
                prefix = date_str
            else:
                prefix = ''

            image_url = entry.get("image", {}).get("href", None)
            audio_url = self.get_audio_url(entry)

            filename = f"{self.sanitize_filename(prefix)}{self.sanitize_filename(metadata.get("title", ""))}.mp3"
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

            write_episode = False
            if os.path.exists(file_path):
                if self.overwrite:
                    print(f"Overwriting existing file: {file_path}")
                    write_episode = True
                else:
                    print(f"File already exists: {file_path}")
            else:
                write_episode = True

            if write_episode:
                if self.download_file(audio_url, file_path):
                    self.set_metadata(file_path, metadata, image_url=image_url)
                else:
                    print(f"Skipping metadata for '{metadata.get("title", "")}' due to download failure.")

            # Check break condition
            if self.episode_cnt is not None and cntr == self.episode_cnt:
                break

        rss.save_cache()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download podcast episodes from an Acast RSS feed (or any other podcast platform that provides a compatible RSS feed) and embed metadata into MP3 files."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rss-url", help="Podcast RSS feed URL")
    group.add_argument("--update", action="store_true", help="Update podcasts from rss_cache.json")

    parser.add_argument(
        "-d","--output-dir",
        default="podcasts",
        help="Directory where MP3 files will be saved (default: podcasts in the current working directory).  If this option is specified when adding a new feed, it will be saved in the cache and applied to all new episodes when updating the feed.")
    parser.add_argument(
        "-u","--user-agent",
        default="Wget/1.25.0",
        help="Set a custom User-Agent header (default: Wget/1.25.0)")
    parser.add_argument(
        "-n","--max-download",
        type=int,
        help="Only download the N most recent podcast episodes")
    parser.add_argument(
        "-c", "--ignore-rss-cache",
        action="store_true",
        help="Ignore the cache; this treats the feed as new (ETag and Last-Modified headers are disregarded as well as any cached output directory and prefix settings)")
    parser.add_argument(
        "-o", "--overwrite",
        action="store_true",
        help="Overwrite an existing episode if a file of the same name already exists")
    parser.add_argument(
        "-p", "--prefix",
        choices=['date','episode'],
        help="Prefix the episode filename with the ISO date (YYYY-MM-DD) or season+episode number (SxEy); if 'episode' is specified but the field is not available, then the date will be used. If this option is specified when adding a new feed, it will be saved in the cache and applied to all new episodes when updating the feed.")
    parser.add_argument(
        "-4", "--id3v24",
        action="store_true",
        help="Write ID3v2.4 tags instead of ID3v2.3 (default)")

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
                episode_cnt=args.max_download,
                ignore_cache=args.ignore_rss_cache,
                overwrite=args.overwrite,
                prefix=args.prefix,
                id3v24=args.id3v24
            )
            downloader.download()
    else:
        downloader = PodcastDownloader(
            rss_url=args.rss_url, user_agent=args.user_agent, output_dir=args.output_dir, episode_cnt=args.max_download, ignore_cache=args.ignore_rss_cache, overwrite=args.overwrite, prefix=args.prefix,id3v24=args.id3v24
        )
        downloader.download()
