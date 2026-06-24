import scrapy
import re
from scrapy.http import Response, Request
from ..utils.paperlist import paper_list
from ..utils.researchr import extract_form_params


class PaperSpider(scrapy.Spider):
    name = "paper_spider"

    def start_requests(self):
        for p in paper_list:
            yield Request(url=p["url"], callback=self.parse, cb_kwargs=p)

    def parse(self, response: Response, **kwargs):
        conf = kwargs["conf"]

        # Parse the event-overview table (Accepted Papers)
        table = response.xpath('//*[@id="event-overview"]/table')
        papers = table.xpath("tr/td[2]")

        # Extract form parameters for modal AJAX (used by researchr enrichment)
        form_params = extract_form_params(response.text)

        for paper in papers:
            title = paper.xpath("a[1]/text()").get()
            if not title:
                continue

            title = title.strip()

            author_list = paper.xpath('.//div[@class="performers"]/a')
            author = ", ".join([a.xpath("text()").get() for a in author_list])

            uuid = paper.xpath("a[1]/@data-event-modal").get() or ""

            yield {
                "conf": conf,
                "title": title,
                "author": author,
                "uuid": uuid,
                "form_params": form_params,
                "listing_url": response.url,
                "abstract": "",
                "full_version_url": "",
                "arxiv_url": "",
                "arxiv_pdf_url": "",
                "keywords": "",
                "title_cn": "",
                "abstract_cn": "",
                "arxiv_id": "",
                "doi": "",
                "dblp_url": "",
            }