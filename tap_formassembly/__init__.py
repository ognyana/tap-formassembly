#!/usr/bin/env python3
import os
from singer.catalog import Catalog, CatalogEntry
from singer.schema import Schema
from .service import * 

LOGGER = singer.get_logger()

def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def load_schema(entity):
    """ Load schema by name """
    return utils.load_json(get_abs_path("schemas/{}.json".format(entity)))


def load_schemas():
    """ Load schemas from schemas folder """
    schemas = {}

    for filename in os.listdir(get_abs_path('schemas')):
        schemas['filename'] = Schema.from_dict(utils.load_json(filename))

    return schemas

def sync(config, state, catalog):
    """ Sync data from tap source """
    # Loop over selected streams in catalog
    for stream in catalog.get_selected_streams(state):
        LOGGER.info("Syncing stream:" + stream.tap_stream_id)

        full_path = "schemas/{}.json".format(stream.tap_stream_id.lower())
        schema = utils.load_json(get_abs_path(full_path))

        singer.write_schema(
            stream_name=stream.tap_stream_id,
            schema=schema,
            key_properties=stream.key_properties,
        )

        svc = FormAssemblyService(stream, schema, config)
        svc.get_form_responses()

        singer.write_state({
            "last_updated_at": str(datetime.now().isoformat()),
            "stream": stream.tap_stream_id
        })
    return

def discover():
    raw_schemas = load_schemas()
    streams = []

    for stream_id, schema in raw_schemas.items():
        stream_metadata = []
        key_properties = []
        streams.append(
            CatalogEntry(
                tap_stream_id=stream_id,
                stream=stream_id,
                schema=schema,
                key_properties=key_properties,
                metadata=stream_metadata,
                replication_key=None,
                is_view=None,
                database=None,
                table=None,
                row_count=None,
                stream_alias=None
            )
        )

    return Catalog(streams)

@utils.handle_top_exception(LOGGER)
def main():
    # Parse command line arguments
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)

    # If discover flag was passed, run discovery mode and dump output to stdout
    if args.discover:
        catalog = discover()
        catalog.dump()
    # Otherwise run in sync mode
    else:
        if args.catalog:
            catalog = args.catalog
        else:
            catalog = discover()

        sync(args.config, args.state, catalog)


if __name__ == "__main__":
    main()
