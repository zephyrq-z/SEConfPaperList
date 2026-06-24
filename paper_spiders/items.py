import scrapy


class PaperSpidersItem(scrapy.Item):
    conf = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    abstract = scrapy.Field()
    full_version_url = scrapy.Field()
    arxiv_url = scrapy.Field()
    arxiv_pdf_url = scrapy.Field()
    keywords = scrapy.Field()
    title_cn = scrapy.Field()
    abstract_cn = scrapy.Field()
    arxiv_id = scrapy.Field()
    doi = scrapy.Field()
    dblp_url = scrapy.Field()
    # Internal fields (not written to output)
    uuid = scrapy.Field()
    form_params = scrapy.Field()
    listing_url = scrapy.Field()