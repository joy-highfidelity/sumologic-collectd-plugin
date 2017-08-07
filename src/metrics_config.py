import collectd
from metrics_util import MetricsUtil


class ConfigOptions:
    """
    Config options
    """
    types_db = 'TypesDB'
    url = 'URL'
    # Http header options
    dimension_tags = 'Dimensions'
    meta_tags = 'Metadata'
    source_name = 'SourceName'
    host_name = 'HostName'
    source_category = 'SourceCategory'
    # Metrics Batching options
    max_batch_size = 'MaxBatchSize'
    max_batch_interval = 'MaxBatchInterval'
    # Http post request frequency option
    http_post_interval = 'HttpPostInterval'
    # Http retry options
    retry_initial_delay = 'RetryInitialDelay'
    retry_max_attempts = 'RetryMaxAttempts'
    retry_max_delay = 'RetryMaxDelay'
    retry_backoff = 'RetryBackOff'
    retry_jitter_min = 'RetryJitterMin'
    retry_jitter_max = 'RetryJitterMax'
    # Memory option
    max_requests_to_buffer = 'MaxRequestsToBuffer'
    # Static options, not configurable yet
    content_type = 'ContentType'
    content_encoding = 'ContentEncoding'


class MetricsConfig:
    """
    Configuration for sumologic collectd plugin
    """

    def __init__(self):
        """
        Init MetricsConfig with default config
        """
        self.conf = self.default_config()
        self.types = {}

        collectd.info('Initialized MetricsConfig with default config %s' % self.conf)

    def parse_config(self, config):
        """
        Parse the python plugin configurations in collectd.conf
        """

        try:
            for child in config.children:
                if child.key == ConfigOptions.types_db:
                    for v in child.values:
                        self._parse_types(v)
                elif child.key == ConfigOptions.url:
                    url = child.values[0]
                    self.conf[child.key] = url
                    MetricsUtil.validate_non_empty(url, child.key)
                elif child.key in [ConfigOptions.dimension_tags, ConfigOptions.meta_tags]:
                    self._parse_tags(child)
                elif child.key in [ConfigOptions.source_name, ConfigOptions.host_name,
                                   ConfigOptions.source_category]:
                    s = child.values[0]
                    MetricsUtil.validate_non_empty(s, child.key)
                    MetricsUtil.validate_string_type(s, child.key, 'Value', 'Key')
                    self.conf[child.key] = s
                elif child.key == ConfigOptions.http_post_interval:
                    f = float(child.values[0])
                    MetricsUtil.validate_positive(f, child.key)
                    self.conf[child.key] = f
                elif child.key in [ConfigOptions.max_batch_size, ConfigOptions.max_batch_interval,
                                   ConfigOptions.retry_max_attempts, ConfigOptions.retry_max_delay,
                                   ConfigOptions.retry_backoff,
                                   ConfigOptions.max_requests_to_buffer]:
                    i = int(child.values[0])
                    MetricsUtil.validate_positive(i, child.key)
                    self.conf[child.key] = i
                elif child.key in [ConfigOptions.retry_initial_delay,
                                   ConfigOptions.retry_jitter_min, ConfigOptions.retry_jitter_max]:
                    i = int(child.values[0])
                    MetricsUtil.validate_non_negative(i, child.key)
                    self.conf[child.key] = i
                else:
                    collectd.warning('Unknown configuration %s, ignored.' % child.key)
        except Exception as e:
            collectd.error('Failed to parse configurations due to %s' % e.message)
            raise e

        if ConfigOptions.url not in self.conf:
            raise Exception('Specify URL in collectd.conf.')

        http_post_interval = self.conf[ConfigOptions.http_post_interval]
        max_batch_interval = self.conf[ConfigOptions.max_batch_interval]

        if http_post_interval > max_batch_interval:
            raise Exception('Specify HttpPostInterval %f as float between 0 and '
                            'MaxBatchInterval %d' %(http_post_interval, max_batch_interval))

        collectd.info('Updated MetricsConfig %s with config file %s ' % (self.conf, config))

    # parse types.db file
    def _parse_types(self, db):

        try:
            f = open(db, 'r')

            for line in f:
                fields = line.split()
                if len(fields) < 2:
                    continue
                type_name = fields[0]
                if type_name[0] == '#':
                    continue
                v = []
                for ds in fields[1:]:
                    ds = ds.rstrip(',')
                    ds_fields = ds.split(':')

                    if len(ds_fields) != 4:
                        collectd.warning('Cannot parse data source %s on type %s'
                                         % (ds, type_name))
                        continue
                    v.append(ds_fields)
                self.types[type_name] = v

            f.close()

            collectd.info('Parsed types %s with types_db file %s ' % (self.types, db))

        except Exception as e:
            collectd.error('Parse types %s failed with %s' %(db, e.message))
            raise e

    # parse dimension_tags/meta_tags specified in collectd.conf
    def _parse_tags(self, child):
        if len(child.values) % 2 != 0:
            raise Exception('Missing tags key/value in options %s.' % str(child.values))

        for v in child.values:
            MetricsUtil.validate_field(v, child.key, 'Value', 'Key')

        self.conf[child.key] = zip(*(iter(child.values),) * 2)

        collectd.info('Parsed %s tags %s' % (child.key, self.conf[child.key]))

    @staticmethod
    def default_config():
        return {
            ConfigOptions.http_post_interval: 0.1,
            ConfigOptions.max_batch_size: 100,
            ConfigOptions.max_batch_interval: 1,
            ConfigOptions.retry_initial_delay: 0,
            ConfigOptions.retry_max_attempts: 10,
            ConfigOptions.retry_max_delay: 100,
            ConfigOptions.retry_backoff: 2,
            ConfigOptions.retry_jitter_min: 0,
            ConfigOptions.retry_jitter_max: 10,
            ConfigOptions.max_requests_to_buffer: 1000000,
            ConfigOptions.content_type: 'application/vnd.sumologic.carbon2',
            ConfigOptions.content_encoding: 'deflate'
        }