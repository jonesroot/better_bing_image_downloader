import sys
import shutil
import argparse
import logging
from pathlib import Path
from .bing import Bing
from tqdm import tqdm
import asyncio
import httpx


async def downloader(query: str, limit: int, output_dir: str = 'downloads', adult_filter_off: bool = False,
                     force_replace: bool = False, timeout: int = 60, filter: str = "", verbose: bool = True,
                     badsites: list = [], name: str = 'Image'):
    """
    Download images using the Bing image scraper asynchronously.
    
    Parameters:
    query (str): The search query.
    limit (int): The maximum number of images to download.
    output_dir (str): The directory to save the images in.
    adult_filter_off (bool): Whether to turn off the adult filter.
    force_replace (bool): Whether to replace existing files.
    timeout (int): The timeout for the image download.
    filter (str): The filter to apply to the search results.
    verbose (bool): Whether to print detailed output.
    badsites (list): List of bad sites to be excluded.
    name (str): The name of the images.
    """

    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.CRITICAL)

    adult = 'off' if adult_filter_off else 'on'

    image_dir = Path(output_dir).joinpath(query).absolute()

    if force_replace and image_dir.is_dir():
        shutil.rmtree(image_dir)

    try:
        if not image_dir.is_dir():
            image_dir.mkdir(parents=True)
    except Exception as e:
        logging.error('Failed to create directory. %s', e)
        sys.exit(1)
        
    logging.info("Downloading Images to %s", str(image_dir.absolute()))

    async with httpx.AsyncClient(timeout=timeout) as client, tqdm(total=limit, unit='MB', ncols=100, colour="green",
                                                                  bar_format='{l_bar}{bar} {total_fmt} MB | '
                                                                             'Download Speed {rate_fmt} | '
                                                                             'Estimated Time: {remaining}') as pbar:
        def update_progress_bar(download_count):
            pbar.update(download_count - pbar.n)

        bing = Bing(query, limit, image_dir, adult, timeout, filter, verbose, badsites, name)
        bing.download_callback = update_progress_bar

        await bing.run(client)

    source_input = input('\n\nDo you wish to see the image sources? (Y/N): ')
    if source_input.lower() == 'y':
        i = 1
        for src in bing.seen:
            print(f'{str(i)}. {src}')
            i += 1
    else:
        print('Happy Scraping!')


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
