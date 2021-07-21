import re
import singer
import backoff
import requests
import csv
import codecs
from datetime import datetime, timedelta
from singer import Transformer, utils


LOGGER = singer.get_logger()

API_DATE_TIME_FORMAT = '%m/%d/%Y %H:%M'
REQUIRED_CONFIG_KEYS = ['accessToken', 'dateRange', 'baseUrl']
WORD_REGEX = re.compile("[^A-Za-z]+")


class FormAssemblyService:
    def __init__(self, stream, schema, config):
        self.config = config
        self.stream = stream
        self.form_id = stream.split("_")[1]
        self.schema = schema
        self.access_token = config['accessToken']
        self.session = requests.Session()

    @backoff.on_exception(
        backoff.expo,
        requests.exceptions.RequestException,
        max_tries=5,
        giveup=lambda e: e.response is not None and 400 <= e.response.status_code < 500,
        factor=2
    )
    def request(self, url, params=None, as_csv=False):
        params = params or {}
        headers = {"Accept": "application/json"}
        params['access_token'] = self.access_token

        if as_csv:
            download = requests.get(url, params=params, headers=headers)
            LOGGER.info("GET {}".format(url))
            csv_reader = csv.DictReader(codecs.iterdecode(download.content.splitlines(), 'utf-8'))

            return csv_reader

        req = requests.Request("GET", url=url, params=params, headers=headers).prepare()
        LOGGER.info("GET {}".format(req.url))
        resp = self.session.send(req)
        resp.raise_for_status()

        return resp.json()

    def get_url(self, endpoint):
        """ Get endpoint URL """
        return self.config.get('baseUrl') + endpoint

    def get_form_responses(self):
        """ Sync form data """
        url = self.get_url(f"/api_v1/responses/export/{self.form_id}.csv")
        date_range = self.parse_range(self.config.get('dateRange'))
        LOGGER.info('Date range: ' + str(date_range))

        params = {
            "date_from": date_range['start'],
            "date_to": date_range['end']
        }

        form_responses = self.request(url, params, as_csv=True)

        with Transformer() as transformer:
            time_extracted = utils.now()

            for row in form_responses:
                row = {self.camel(k): v for k, v in row.items()}

                if row['accountName']:
                    item = transformer.transform(row, self.schema)
                    singer.write_record(self.stream, item, time_extracted=time_extracted)

    def parse_range(self, date_range):
        if date_range == 'YESTERDAY':
            yesterday_date = datetime.today() - timedelta(days=1)
            return self.format_range(yesterday_date, yesterday_date)
        else:
            range_parts = date_range.split(',')
            date_format = "%Y%m%d"
            start = datetime.strptime(range_parts[0], date_format)
            end = datetime.strptime(range_parts[1], date_format)
            return self.format_range(start, end)

    @staticmethod
    def format_range(start, end):
        return {
            'start': start.replace(
                microsecond=0, second=0, minute=0, hour=0
            ).strftime(API_DATE_TIME_FORMAT),
            'end': end.replace(
                microsecond=0, second=59, minute=59, hour=23
            ).strftime(API_DATE_TIME_FORMAT)
        }

    @staticmethod
    def camel(chars):
        """ String to camel case """
        words = WORD_REGEX.split(chars)
        return "".join(w.lower() if i is 0 else w.title() for i, w in enumerate(words))
