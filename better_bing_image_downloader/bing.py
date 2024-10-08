import urllib.request
import urllib
import logging
import asyncio
import aiohttp
import imghdr
import posixpath
import re
from pathlib import Path
from PIL import Image
from io import BytesIO


class Bing:
    def __init__(self, query, limit, output_dir, adult, timeout, filter='', verbose=False, badsites=[], name='Image'):
        self.download_count = 0
        self.query = query
        self.output_dir = Path(output_dir)
        self.adult = adult
        self.filter = filter
        self.verbose = verbose
        self.seen = set()
        self.urls = []
        self.badsites = badsites
        self.image_name = name
        self.download_callback = None
        
        if self.verbose:
            logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        else:
            logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

        if self.badsites:
            logging.info("Download links will not include: %s", ', '.join(self.badsites))

        assert isinstance(limit, int), "limit must be integer"
        self.limit = limit
        assert isinstance(timeout, int), "timeout must be integer"
        self.timeout = timeout

        self.page_counter = 0
        self.headers = {
            'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) '
                           'AppleWebKit/537.11 (KHTML, like Gecko) '
                           'Chrome/23.0.1271.64 Safari/537.11'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive'
        }

    def get_filter(self, shorthand):
        filters = {
            "line": "+filterui:photo-linedrawing",
            "linedrawing": "+filterui:photo-linedrawing",
            "photo": "+filterui:photo-photo",
            "clipart": "+filterui:photo-clipart",
            "gif": "+filterui:photo-animatedgif",
            "animatedgif": "+filterui:photo-animatedgif",
            "transparent": "+filterui:photo-transparent"
        }
        return filters.get(shorthand, "")

    def save_image(self, link, file_path) -> None:
        try:
            request = urllib.request.Request(link, None, self.headers)
            image = urllib.request.urlopen(request, timeout=self.timeout).read()
            try:
                with Image.open(BytesIO(image)) as img:
                    img.verify()
            except (IOError, SyntaxError) as e:
                logging.error('Invalid image, not saving %s: %s', link, e)
                raise ValueError('Invalid image, not saving %s' % link)

            with open(str(file_path), 'wb') as f:
                f.write(image)

        except urllib.error.HTTPError as e:
            logging.error('HTTPError while saving image %s: %s', link, e)

        except urllib.error.URLError as e:
            logging.error('URLError while saving image %s: %s', link, e)
        

    def download_image(self, link):
        if self.download_count >= self.limit:
            return
        
        self.download_count += 1
        try:
            path = urllib.parse.urlsplit(link).path
            filename = posixpath.basename(path).split('?')[0]
            file_type = filename.split(".")[-1]
            if file_type.lower() not in ["jpe", "jpeg", "jfif", "exif", "tiff", "gif", "bmp", "png", "webp", "jpg"]:
                file_type = "jpg"

            if self.verbose:
                logging.info("[%] Downloading Image #{} from {}".format(self.download_count, link))

            self.save_image(link, self.output_dir.joinpath("{}_{}.{}".format(self.image_name, str(self.download_count), file_type)))

            if self.verbose:
                logging.info("[%] File Downloaded !\n")
                
            if self.download_callback:
                self.download_callback(self.download_count)

        except Exception as e:
            self.download_count -= 1
            logging.error('Issue getting: %s\nError: %s', link, e)

    async def get_image_urls(self):
        while self.download_count < self.limit:
            if self.verbose:
                logging.info('\n\n[!] Indexing page: %d\n', self.page_counter + 1)
            
            try:
                request_url = (
                    'https://www.bing.com/images/async?q='
                    + urllib.parse.quote_plus(self.query)
                    + '&first=' + str(self.page_counter)
                    + '&count=' + str(self.limit)
                    + '&adlt=' + self.adult
                    + '&qft=' + ('' if self.filter is None else self.get_filter(self.filter))
                )
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(request_url, headers=self.headers) as response:
                        html = await response.text()

                if html == "":
                    logging.info("[%] No more images are available")
                    break
                
                links = re.findall('murl&quot;:&quot;(.*?)&quot;', html)
                
                if self.verbose:
                    logging.info("[%%] Indexed %d Images on Page %d.", len(links), self.page_counter + 1)
                    logging.info("\n===============================================\n")

                for link in links:
                    if any(badsite in link for badsite in self.badsites):
                        if self.verbose:
                            logging.info("[!] Link included in badsites: %s", link)
                        continue

                    if self.download_count < self.limit and link not in self.seen:
                        self.seen.add(link)
                        yield link

                self.page_counter += 1
                await asyncio.sleep(1)
            except aiohttp.ClientError as e:
                logging.error('ClientError while making request to Bing: %s', e)

        logging.info("\n\n[%%] Done. Downloaded %d images.", self.download_count)
