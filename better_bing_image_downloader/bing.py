import urllib.request
import urllib
import logging
import imghdr
import posixpath
import re
from pathlib import Path

class Bing:
    def __init__(self, query, limit, output_dir, adult, timeout, filter='', verbose=False, badsites=[], name='Image'):
        self.download_count = 0
        self.query = query
        self.output_dir = Path(output_dir)  # Ensure Path object
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

        assert type(limit) == int, "limit must be integer"
        self.limit = limit
        assert type(timeout) == int, "timeout must be integer"
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
            if not imghdr.what(None, image):
                logging.error('Invalid image, not saving %s', link)
                raise ValueError('Invalid image, not saving %s' % link)
            with open(str(file_path), 'wb') as f:
                f.write(image)

        except urllib.error.HTTPError as e:
            logging.error('HTTPError while saving image %s: %s', link, e)

        except urllib.error.URLError as e:
            logging.error('URLError while saving image %s: %s', link, e)

    def download_image(self, link):
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
                request = urllib.request.Request(request_url, None, headers=self.headers)
                response = urllib.request.urlopen(request)
                html = response.read().decode('utf8')
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
                        yield link  # Yield URL for async iteration

                self.page_counter += 1
            except urllib.error.HTTPError as e:
                logging.error('HTTPError while making request to Bing: %s', e)
            except urllib.error.URLError as e:
                logging.error('URLError while making request to Bing: %s', e)

        logging.info("\n\n[%%] Done. Downloaded %d images.", self.download_count)
