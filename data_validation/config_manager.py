# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from data_validation import consts

class ConfigManager(object):

    _config: dict = None
    source_client = None
    target_client = None

    def __init__(self, config, source_client, target_client, verbose=False):
        """ Initialize a ValidationBuilder client which supplies the
            source and target queries tto run.

        Args:
            config (Dict): The Validation config supplied
            source_client (IbisClient): The Ibis client for the source DB
            target_client (IbisClient): The Ibis client for the target DB
            verbose (Bool): If verbose, the Data Validation client will print queries run
        """
        self._config = config

        self.source_client = source_client
        self.target_client = target_client

        self.source_table = self.source_client.table(self.get_source_table(), database=self.get_source_schema())
        self.target_table = self.source_client.table(self.get_target_table(), database=self.get_target_schema())

        self.verbose = verbose

    def get_config(self):
        """Return config object."""
        return self._config

    def get_validation_type(self):
        """Return string validation type (Column|GroupedColumn)."""
        return self._config[consts.CONFIG_TYPE]

    def get_aggregates(self):
        """Return Aggregates from Config """
        return self._config.get(consts.CONFIG_AGGREGATES) or []

    def append_aggregates(self, aggregate_configs):
        """Append aggregate configs to existing config."""
        self._config[consts.CONFIG_AGGREGATES] = \
            self.get_aggregates() + aggregate_configs

    def get_query_groups(self):
        """ Return Query Groups from Config """
        return self._config.get(consts.CONFIG_GROUPED_COLUMNS) or []

    def append_query_groups(self, grouped_column_configs):
        """Append aggregate configs to existing config."""
        self._config[consts.CONFIG_GROUPED_COLUMNS] = \
            self.get_query_groups() + grouped_column_configs

    def get_source_schema(self):
        """Return string value of source schema."""
        return self._config[consts.CONFIG_SCHEMA_NAME]

    def get_source_table(self):
        """Return string value of source table."""
        return self._config[consts.CONFIG_TABLE_NAME]

    def get_target_schema(self):
        """Return string value of target schema."""
        return self._config.get(consts.CONFIG_TARGET_SCHEMA_NAME) or self._config[consts.CONFIG_SCHEMA_NAME]

    def get_target_table(self):
        """Return string value of target table."""
        return self._config.get(consts.CONFIG_TARGET_TABLE_NAME) or self._config[consts.CONFIG_TABLE_NAME]

    def get_query_limit(self):
        """Return int limit for query executions."""
        return self._config.get(consts.CONFIG_LIMIT)

    @staticmethod
    def build_config_manager(config_type, source_conn, target_conn, source_client, target_client, table_obj, verbose=False):
        """Return a ConfigManager instance with available config."""
        config = {
            consts.CONFIG_TYPE: config_type,
            consts.CONFIG_SOURCE_CONN: source_conn,
            consts.CONFIG_TARGET_CONN: target_conn,
            consts.CONFIG_SCHEMA_NAME: table_obj[consts.CONFIG_SCHEMA_NAME],
            consts.CONFIG_TABLE_NAME: table_obj[consts.CONFIG_TABLE_NAME],
            consts.CONFIG_TARGET_SCHEMA_NAME: table_obj.get(
                consts.CONFIG_TARGET_SCHEMA_NAME
            )
            or table_obj[consts.CONFIG_SCHEMA_NAME],
            consts.CONFIG_TARGET_TABLE_NAME: table_obj.get(consts.CONFIG_TARGET_TABLE_NAME)
            or table_obj[consts.CONFIG_TABLE_NAME],
        }

        return ConfigManager(config, source_client, target_client, verbose=verbose)

    def build_config_grouped_columns(self, grouped_columns):
        """Return list of grouped column config objects."""
        grouped_column_configs = []
        for column in grouped_columns:
            if column not in self.source_table.columns:
                raise ValueError(f"GroupedColumn DNE: {self.source_table.op().name}.{column}")
            column_config = {
                consts.CONFIG_SOURCE_COLUMN: column,
                consts.CONFIG_TARGET_COLUMN: column,
                consts.CONFIG_FIELD_ALIAS: column,
                consts.CONFIG_CAST: None,
            }
            grouped_column_configs.append(column_config)

        return grouped_column_configs

    def build_config_aggregates(self, agg_type, arg_value, supported_types):
        """Return list of aggregate objects of given agg_type."""
        aggregate_configs = []
        whitelist_columns = (
            self.source_table.columns if arg_value == "*" else json.loads(arg_value)
        )
        for column in self.source_table.columns:
            if column not in whitelist_columns:
                continue
            elif column not in self.target_table.columns:
                logging.info(f"Skipping Agg {agg_type}: {self.source_table.op().name}.{column}")
                continue
            elif (
                supported_types and str(self.source_table[column].type()) not in supported_types
            ):
                continue

            aggregate_config = {
                consts.CONFIG_SOURCE_COLUMN: column,
                consts.CONFIG_TARGET_COLUMN: column,
                consts.CONFIG_FIELD_ALIAS: f"{agg_type}__{column}",
                consts.CONFIG_TYPE: agg_type,
            }
            aggregate_configs.append(aggregate_config)

        return aggregate_configs
