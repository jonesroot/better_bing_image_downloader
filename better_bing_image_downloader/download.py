import os
import argparse
import asyncio
import shutil
import logging
from pathlib import Path
from .bing import Bing
import httpx


async def downloader(
    query,
    limit=5,
    output_dir='downloads',
    adult_filter_off=False,
    force_replace=False,
    timeout=60,
    filter="",
    verbose=False,
    badsites=[],
    name='Image'
):
    """
    Asynchronous downloader using httpx.
    """

    if adult_filter_off:
        adult = 'off'
    else:
        adult = 'on'

    image_dir = os.path.join(output_dir, query)

    if force_replace and os.path.isdir(image_dir):
        shutil.rmtree(image_dir)

    if not os.path.isdir(image_dir):
        os.makedirs(image_dir)

    if verbose:
        print(f"Downloading images to {image_dir}")

    async with httpx.AsyncClient(timeout=timeout) as client:
        bing = Bing(query, limit, image_dir, adult, timeout, filter, verbose, badsites, name)
        total_downloaded = 0

        async for url in await bing.get_image_urls():
            if total_downloaded >= limit:
                break
            
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    file_path = os.path.join(image_dir, f"{name}_{total_downloaded}.jpg")
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    total_downloaded += 1
                    if verbose:
                        print(f"Downloaded {file_path}")
            except Exception as e:
                if verbose:
                    print(f"Failed to download {url}: {e}")

    if verbose:
        print(f"Download completed: {total_downloaded} images downloaded.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download images using Bing.')
    parser.add_argument('query', type=str, help='The search query.')
    parser.add_argument('-l', '--limit', type=int, default=100, help='The maximum number of images to download.')
    parser.add_argument('-d', '--output_dir', type=str, default='dataset', help='The directory to save the images in.')
    parser.add_argument('-a', '--adult_filter_off', action='store_true', help='Whether to turn off the adult filter.')
    parser.add_argument('-F', '--force_replace', action='store_true', help='Whether to replace existing files.')
    parser.add_argument('-t', '--timeout', type=int, default=60, help='The timeout for the image download.')
    parser.add_argument('-f', '--filter', type=str, default="", help='The filter to apply to the search results.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Whether to print detailed output.')
    parser.add_argument('-b', '--bad_sites', nargs='*', default=[], help='List of bad sites to be excluded.')
    parser.add_argument('-n', '--name', type=str, default='Image', help='The name of the images.')
    
    args = parser.parse_args()
    
    asyncio.run(downloader(args.query, args.limit, args.output_dir, args.adult_filter_off,
                           args.force_replace, args.timeout, args.filter, args.verbose, args.bad_sites, args.name))
