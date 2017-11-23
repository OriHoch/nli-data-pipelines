from elasticsearch import NotFoundError, helpers
import logging, datetime, time, warnings
from datapackage_pipelines.wrapper import ingest, spew
import es


class BaseProcessor(object):
    """
    Common base class for all processors
    """

    def __init__(self, parameters, datapackage, resources):
        self._parameters = parameters
        self._datapackage = datapackage
        self._resources = resources
        self._stats = {}
        self._warned_once = []
        self._db_session = None
        self._db_meta = None
        self._elasticsearch = None
        self._delay_limit = None
        self._delay_limit_reached = False
        self._start_time = None

    @classmethod
    def main(cls):
        # can be used like this in datapackage processor files:
        # if __name__ == '__main__':
        #      Processor.main()
        spew(*cls(*ingest()).spew())

    def spew(self):
        self._datapackage, self._resources = self._process(self._datapackage, self._resources)
        return self._datapackage, self._resources, self._get_stats()

    def _get_stats(self):
        return self._stats

    def _get_stat(self, stat, default=None):
        stat = self._filter_stat_key(stat)
        return self._stats.get(stat, default)

    def _incr_stat(self, stat, incr_by=1):
        stat = self._filter_stat_key(stat)
        self._stats.setdefault(stat, 0)
        self._stats[stat] += incr_by
        return self._stats[stat]

    def _set_stat(self, stat, value):
        stat = self._filter_stat_key(stat)
        self._stats[stat] = value
        return self._stats[stat]

    def _filter_stat_key(self, stat):
        # allows to add a prefix / suffix to stat titles
        return stat

    def _filter_row_value(self, resource_number, field_name, value):
        return value

    def _filter_row(self, resource_number, row):
        yield {field_name: self._filter_row_value(resource_number, field_name, value)
               for field_name, value in row.items()}

    def _filter_resource(self, resource_number, resource_data):
        for row in resource_data:
            yield from self._filter_row(resource_number, row)

    def _filter_resources(self, resources):
        for resource_number, resource_data in enumerate(resources):
            yield self._filter_resource(resource_number, resource_data)

    def _get_resource_descriptor(self, resource_number):
        return self._datapackage["resources"][resource_number]

    def _process(self, datapackage, resources):
        return self._filter_datapackage(datapackage), self._filter_resources(resources)

    def _filter_datapackage(self, datapackage):
        datapackage["resources"] = self._filter_resource_descriptors(datapackage["resources"])
        return datapackage

    def _filter_resource_descriptors(self, resource_descriptors):
        return [self._filter_resource_descriptor(resource_number, resource_descriptor)
                for resource_number, resource_descriptor
                in enumerate(resource_descriptors)]

    def _filter_resource_descriptor(self, resource_number, resource_descriptor):
        return resource_descriptor

    def _warn_once(self, msg):
        if msg not in self._warned_once:
            self._warned_once.append(msg)
            warnings.warn(msg, UserWarning)

    def _get_new_es_engine(self):
        return es.get_engine()

    @property
    def elasticsearch(self):
        if self._elasticsearch is None:
            self._elasticsearch = self._get_new_es_engine()
        return self._elasticsearch

    def _delay_limit_initialize(self):
        stop_after_seconds = self._parameters.get("stop-after-seconds")
        if stop_after_seconds:
            self._delay_limit = int(stop_after_seconds)
            self._start_time = datetime.datetime.now()

    def _delay_limit_check(self):
        if self._delay_limit_reached:
            return True
        elif self._delay_limit and self._delay_limit > 0:
            time_gap = (datetime.datetime.now() - self._start_time).total_seconds()
            if time_gap > self._delay_limit:
                self._delay_limit_reached = True
                self._warn_once("ran for {} seconds, reached delay limit".format(time_gap))
                self._stats["reached delay limit seconds"] = time_gap
                return True


class BaseResourceProcessor(BaseProcessor):
    """Base class for processing a single resource"""

    def __init__(self, *args, **kwargs):
        super(BaseResourceProcessor, self).__init__(*args, **kwargs)
        # the descriptor of the selected resource (only 1 resource is processed by this processor)
        self._resource_descriptor = None
        # the selected resource number
        self._resource_number = None

    def _get_schema(self, resource_descriptor):
        # can be extended to provide a hard-coded schema
        # or to modify the schema from the input resource descriptor
        return resource_descriptor.get("schema", {"fields": []})

    def _get_output_resource_name(self):
        return self._parameters.get("resource")

    def _get_output_resource_path(self):
        return "data/{}.csv".format(self._get_output_resource_name())

    def _is_matching_resource_descriptor(self, resource_number, resource_descriptor):
        # see the comment on _is_matching_resource_number
        return resource_descriptor["name"] == self._get_output_resource_name()

    def _is_matching_resource_number(self, resource_number, resource_descriptor=None):
        # this is called from both _filter_resource_descriptors and filter_resources
        # the first one that matches will store the resource number
        # for example, if resource_descriptor matched an input resource -
        # it will use the same nubmer for matching the output resource
        if self._resource_number is None:
            if not resource_descriptor:
                resource_descriptor = self._get_resource_descriptor(resource_number)
            if self._is_matching_resource_descriptor(resource_number, resource_descriptor):
                self._resource_number = resource_number
                return True
            else:
                return False
        else:
            return self._resource_number == resource_number

    def _filter_resource_descriptors(self, resource_descriptors):
        filtered_descriptors = []
        for resource_number, resource_descriptor in enumerate(resource_descriptors):
            if self._is_matching_resource_number(resource_number, resource_descriptor):
                resource_descriptor = self._filter_resource_descriptor(resource_number, resource_descriptor)
            filtered_descriptors.append(resource_descriptor)
        return filtered_descriptors

    def _filter_resource_descriptor(self, resource_number, resource_descriptor):
        # allows to modify the resource descriptor
        # if you just need to modify the schema - you should extend _get_schema instead
        self._schema = self._get_schema(resource_descriptor)
        resource_descriptor =  dict(resource_descriptor, **{"name": self._get_output_resource_name(),
                                                            "path": self._get_output_resource_path(),
                                                            "schema": self._schema})
        self._resource_descriptor = resource_descriptor
        return resource_descriptor

    def _filter_resources(self, resources):
        # modified to only call filter methods for the matching resource
        # other resources are yielded as-is without any processing
        for resource_number, resource_data in enumerate(resources):
            if self._is_matching_resource_number(resource_number):
                yield self._filter_resource(resource_number, resource_data)
            else:
                yield resource_data

    def _filter_resource(self, resource_number, resource_data):
        # this method is called only for the matching resource
        # it should be extended to provide code to run before or after iterating over the data
        self._delay_limit_initialize()
        yield from super(BaseResourceProcessor, self)._filter_resource(resource_number, resource_data)

    def _filter_row(self, resource_number, row):
        # this method is called only the matching resource's rows
        for row in super(BaseResourceProcessor, self)._filter_row(resource_number, row):
            if self._delay_limit_check():
                self._incr_stat("delay limit skipped rows")
            else:
                yield row


class FilterResourceBaseProcessor(BaseResourceProcessor):

    def _is_matching_resource_descriptor(self, resource_number, resource_descriptor):
        # match the name of the input resource
        return resource_descriptor["name"] == self._get_input_resource_name()

    def _get_input_resource_name(self):
        # by default - uses the same name for input and output resources
        return self._get_output_resource_name()


class BaseDumpProcessor(FilterResourceBaseProcessor):

    def _commit(self, rows):
        raise NotImplementedError()

    @property
    def _log_prefix(self):
        raise NotImplementedError()

    def _flush_rows_buffer(self):
        if len(self._rows_buffer) > 0:
            self._commit(self._rows_buffer)
            self._rows_buffer = []

    def _filter_row(self, resource_number, row):
        for row in super(BaseDumpProcessor, self)._filter_row(resource_number, row):
            self._row_num += 1
            if self._commit_buffer_length > 1:
                if self._row_num%self._commit_buffer_length == 0:
                    self._flush_rows_buffer()
            self._rows_buffer.append(row)
            if self._commit_buffer_length < 2:
                self._flush_rows_buffer()
            yield row

    def _filter_resource(self, *args):
        self._commit_buffer_length = int(self._parameters.get("commit-every", 100))
        self._set_stat("commit every rows", self._commit_buffer_length)
        self._row_num = 0
        self._rows_buffer = []
        if self._commit_buffer_length > 1:
            logging.info("{}: initialized, committing every {} rows".format(self._log_prefix,
                                                                            self._commit_buffer_length))
        else:
            logging.info("{}: initialized".format(self._log_prefix))
        yield from super(BaseDumpProcessor, self)._filter_resource(*args)
        self._flush_rows_buffer()

    def _filter_stat_key(self, stat):
        stat = "{}: {}".format(self._log_prefix, stat)
        return stat



class Processor(BaseDumpProcessor):

    def _get_mappings(self):
        mappings = {}
        for field in self._schema["fields"]:
            name = field["name"]
            type = field["type"]
            mapping = None
            if field.get("es:type"):
                mapping = {"type": field["es:type"]}
            elif name in self._update_keys:
                mapping = {"type": "keyword"}
            elif type == "string":
                mapping = {"type": "text"}
            elif type == "integer":
                mapping = {"type": "long"}
            elif type == "number":
                mapping = {"type": "double"}
            if not mapping:
                raise Exception()
            mappings[name] = mapping
        return mappings

    def _create_index(self):
        level = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        self.elasticsearch.indices.create(self._index_name,
                                          body={"mappings": {"data": {"properties": self._get_mappings()}}})
        self.elasticsearch.indices.refresh(index=self._index_name)
        logging.getLogger().setLevel(level)
        logging.info("index created: {}".format(self._index_name))

    def _get_row_id(self, row):
        if len(self._update_keys) == 1:
            return row[self._update_keys[0]]
        else:
            return "_".join([str(row[k]) for k in self._update_keys])

    def _commit(self, rows):
        actions = [{"_index": self._index_name,
                    "_type": "data",
                    "_id": self._get_row_id(row),
                    "_source": row} for row in rows]
        level = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        success, errors = helpers.bulk(self.elasticsearch, actions)
        logging.getLogger().setLevel(level)
        if not success:
            logging.info(errors)
            raise Exception("encountered errors while bulk inserting to elasticsearch")
        self._incr_stat("indexed docs", len(actions))
        logging.info("{}: commit ({} indexed)".format(self._log_prefix, self._get_stat("indexed docs")))

    def _filter_resource(self, resource_number, resource_data):
        self._update_keys = self._schema["primaryKey"]
        if not self._update_keys or len(self._update_keys) == 0:
            raise Exception("dump requires a primaryKey")
        self._index_name = self._parameters["index-name"]
        if self._parameters.get("drop-index"):
            try:
                self.elasticsearch.indices.delete(self._index_name)
            except NotFoundError:
                pass
        else:
            raise Exception("updating existing index is not supported")
        self._create_index()
        yield from super(Processor, self)._filter_resource(resource_number, resource_data)

    @property
    def _log_prefix(self):
        return self._index_name


if __name__ == "__main__":
    Processor.main()
