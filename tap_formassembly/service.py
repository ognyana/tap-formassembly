import re
import singer
import backoff
import requests
import json
from datetime import datetime, timedelta
from singer import Transformer, utils
import xmltodict
from nested_lookup import nested_lookup

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
        self.fault_tolerance = config['fault_tolerance']
        self.props = schema["properties"]
        self.session = requests.Session()

    # @backoff.on_exception(
    #     backoff.expo,
    #     requests.exceptions.RequestException,
    #     max_tries=5,
    #     giveup=lambda e: e.response is not None and 400 <= e.response.status_code < 500,
    #     factor=2
    # )
    def request(self, url, params=None, is_xml=False):
        params = params or {}
        headers = {"Accept": "application/json"}
        params['access_token'] = self.access_token
        result = None
        if is_xml:
            try:
                data = requests.get(url, params=params, headers=headers)
                LOGGER.info("GET {}".format(url))
                LOGGER.info("Params")
                LOGGER.info(params)
                if data.status_code < 300:
                    resultJson = json.dumps(xmltodict.parse(data.text.replace("\n"," ")))
                    result = self.map_result(json.loads(resultJson))
            except:
                LOGGER.error("XML Failed")
                if not self.fault_tolerance:
                    LOGGER.error("Not fault tolerant FAIL.")
                    raise
        else:
            req = requests.Request("GET", url=url, params=params, headers=headers).prepare()
            LOGGER.info("GET {}".format(req.url))
            resp = self.session.send(req)
            resp.raise_for_status()
            result = resp.json()
        return result
    def map_result(self, result):
        """ Change response structure """
        responses = []
        for response in result['responses'].items():
            field_values = {}
            res = nested_lookup('field', response[1])
            flat_list = [item for sublist in res for item in sublist]

            for field in flat_list:
                if isinstance(field, dict):
                    field_values[self.find_schema_key_by_id(field['@id'])] = field['value']

            responses.append(field_values)

        return responses

    def find_schema_key_by_id(self, id):
        for key, value in self.schema['properties'].items():
            if value['id'] == id:
                return key

    def get_url(self, endpoint):
        """ Get endpoint URL """
        return self.config.get('baseUrl') + endpoint

    def get_form_responses(self):
        """ Sync form data """
        url = self.get_url(f"/api_v1/responses/export/{self.form_id}.xml")
        date_ranges = self.parse_range(self.config.get('dateRange'))
        prop_list = list(map(lambda x: x[0], self.props.items()))
        for date_range in date_ranges:
            params = {
                "date_from": date_range['start'],
                "date_to": date_range['end']
            }

            form_responses = self.request(url, params, is_xml=True)
            if form_responses:
                with Transformer() as transformer:
                    time_extracted = utils.now()
                    for row in form_responses:
                        record = {}
                        item = transformer.transform(row, self.schema)
                        record = {}
                        for field in prop_list:
                            if field in item:
                                record[field] = item[field]
                            else:
                                record[field] = None
                        singer.write_record(self.stream, record, time_extracted=time_extracted)


    def parse_range(self, date_range):
        output = []
        if date_range == 'YESTERDAY':
            yesterday_date = datetime.today() - timedelta(days=1)
            output.append(self.format_range(yesterday_date, yesterday_date))
        else:
            range_size = 1
            range_parts = date_range.split(',')
            date_format = "%Y%m%d"
            start = datetime.strptime(range_parts[0], date_format)
            end = datetime.strptime(range_parts[1], date_format)
            while (end - start).days >= (range_size - 1):
                new_start = start + timedelta(days=range_size - 1)
                output.append(self.format_range(start, new_start))
                start = new_start + timedelta(days=1)

        return output

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
