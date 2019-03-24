from ..data_models.data_models import DataModel, CreateDataModel
from ..named_query import NamedQuery
from ..connectors import Connectors
from ..staging import Staging
from collections import defaultdict


class CloneTenant(object):
    def __init__(self, carol_from, carol_to):
        self.carol_from = carol_from
        self.carol_to = carol_to

    def copy_named_query(self, named_query_list=None, copy_all=False, overwrite=False):

        named = NamedQuery(self.carol_from)
        all_named = named.get_all()

        if copy_all:
            named_query_list = list(all_named.values())
        else:
            assert named_query_list is not None
            if isinstance(named_query_list, str):
                named_query_list = [named_query_list]
            else:
                assert isinstance(named_query_list, list)

        not_exist = dict()
        not_exist['None'] = []
        name_to_send = []
        for name in named_query_list:
            if all_named.get(name) is not None:
                name_to_send.append(all_named.get(name))
            else:
                not_exist['None'].append(name)

        named_to_send = NamedQuery(self.carol_to)
        named_to_send.create_named_query(name_to_send, overwrite=overwrite)

        if not not_exist['None'] == []:
            print('The following named queries in the list do not exist: {}'.format(not_exist['None']))

        return self

    def copy_data_models(self, dm_list=None, publish=True, overwrite=False, copy_all=False):

        DMsTenant = DataModel(self.carol_from)

        if copy_all:
            dm_list = list(DMsTenant.get_all().template_dict.keys())
        else:
            assert dm_list is not None
            if isinstance(dm_list, str):
                dm_list = [dm_list]
            else:
                assert isinstance(dm_list, list)

        dm_to_copy = {}
        snapshot_dict = {}
        dm_to_create = CreateDataModel(self.carol_to)

        for dm_name in dm_list:
            DMsTenant.get_by_name(dm_name)
            current_template = DMsTenant.entity_template_.get(dm_name)
            dm_to_copy.update({dm_name: {'mdmId': current_template['mdmId'],
                                         'mdmEntitySpace': current_template['mdmEntitySpace']}})

            DMsTenant.get_snapshot(dm_id=current_template['mdmId'], entity_space=current_template['mdmEntitySpace'])
            current_snap = DMsTenant.snapshot_
            snapshot_dict.update({dm_name: current_snap[dm_name]})
            dm_to_create.from_snapshot(current_snap[dm_name], publish=publish, overwrite=overwrite)

        return self

    def copy_connecto2r(self, copy_mapping=True, overwrite=False):

        conn = appl.connectorsCarol(self.carol_from)
        conn.getAll(includeMappings=True)
        conn_to_create = conn.connectors

        conn_id = {}

        stag = stg.stagingSchema(self.carol_from)
        self.stag_mapp_to_use = defaultdict(list)

        for connector in conn_to_create:

            current_connector = connector['mdmId']
            conn.connectorStats(current_connector)
            conn_stats = conn.connectorsStats_

            connectorName = connector.get('mdmName', None)
            connectorLabel = connector.get('mdmLabel', None)
            if connectorLabel:
                connectorLabel = connectorLabel['en-US']
            else:
                connectorLabel = None
            groupName = connector.get('mdmGroupName', None)

            conn_to = appl.connectorsCarol(self.carol_to)
            conn_to.createConnector(connectorName, connectorLabel, groupName, overwrite=overwrite)
            conn_id.update({connectorName: conn_to.connectorId})
            self.carol_to.newToken(connectorId=conn_to.connectorId)

            for schema_name in conn_stats.get(current_connector):
                stag.getSchema(schema_name, connector.get('mdmId'))

                aux_schema = stag.schema
                aux_schema.pop('mdmTenantId')
                # aux_schema.pop('mdmStagingApplicationId')
                aux_schema.pop('mdmId')
                aux_schema.pop('mdmCreated')
                aux_schema.pop('mdmLastUpdated')

                stg_to = stg.stagingSchema(self.carol_to)
                stg_to.sendSchema(fields_dict=aux_schema, connectorId=conn_id.get(connectorName),
                                  overwrite=overwrite)

                if copy_mapping:
                    mapping_fields = connector.get('mdmEntityMappings', None).get(schema_name)
                    if mapping_fields is not None:
                        mapping_fields.pop('mdmTenantId')
                        entityMappingsId = mapping_fields.pop('mdmId')
                        entitySpace = mapping_fields.get('mdmEntitySpace')
                        mapping_fields.pop('mdmCreated')
                        mapping_fields.pop('mdmLastUpdated')
                        connectorId = mapping_fields.pop('mdmConnectorId')
                        mappings_to_get = etm.entityMapping(self.carol_from)
                        mappings_to_get.getSnapshot(connectorId, entityMappingsId, entitySpace)
                        _, aux_map = mappings_to_get.snap.popitem()
                        mapping_to = etm.entityMapping(self.carol_to)
                        mapping_to.createFromSnapshot(aux_map, conn_id.get(connectorName), overwrite=overwrite)
                        self.stag_mapp_to_use[connectorName].append({"schema": aux_schema, "mapping": aux_map})
                    else:
                        self.stag_mapp_to_use[connectorName].append({"schema": aux_schema})
                else:
                    self.stag_mapp_to_use[connectorName].append({"schema": aux_schema})

    def copy_connectors(self, conectors_map, map_type='name', overwrite_connector=False, add_to_connector=True,
                        change_name_dict=None, copy_mapping=True, overwrite_schema=False):

        if map_type == 'connector_id':
            map_type = 'mdmId'
        elif map_type == 'name':
            map_type = 'mdmName'
        else:
            raise ('values should be connector_id or name')

        conn_id = {}
        conn = Connectors(self.carol_from)
        conn_to_create = conn.get_all(include_mappings=True)

        stag = Staging(self.carol_from)
        self.stag_mapp_to_use = defaultdict(list)

        for connector, staging in conectors_map.items():
            # for connector in conn_to_create:

            if isinstance(staging, str):
                staging = [staging]

            for list_conn in conn_to_create:
                if list_conn[map_type] == connector:
                    connector = list_conn
                    break
            else:
                raise ValueError('{} does not exist in the tenant'.format(connector))

            current_connector = connector['mdmId']
            conn.stats(connector_id=current_connector)

            if change_name_dict is not None:
                connector_name = change_name_dict.get(connector.get('mdmName', None)).get('name')
                connector_label = change_name_dict.get(connector.get('mdmName', None)).get('label')
                if connector_label is None:
                    connector_label = connector_name
            else:
                connector_name = connector.get('mdmName', None)
                connector_label = connector.get('mdmLabel', None)
                if connector_label:
                    connector_label = connector_label['en-US']
                else:
                    connector_label = None
            group_name = connector.get('mdmGroupName', None)

            conn_to = Connectors(self.carol_to)

            if add_to_connector:
                _con_id = conn_to.get_by_name(connector_name, errors='ignore').get('mdmId')
                if _con_id is None:
                    _con_id = conn_to.create(name=connector_name, label=connector_label,
                                             group_name=group_name, overwrite=overwrite_connector)
            else:
                _con_id = conn_to.create(name=connector_name, label=connector_label,
                                         group_name=group_name, overwrite=overwrite_connector)

            conn_id.update({connector_name: _con_id})

            for schema_name in staging:

                aux_schema = stag.get_schema(staging_name=schema_name, connector_id=connector.get('mdmId'))
                aux_schema.pop('mdmTenantId')

                aux_schema.pop('mdmId')
                aux_schema.pop('mdmCreated')
                aux_schema.pop('mdmLastUpdated')

                stg_to = Staging(self.carol_to)
                stg_to.send_schema(schema=aux_schema, connector_id=conn_id.get(connector_name),
                                   overwrite=overwrite_schema)


                #TODO Apping should be copied after copied all stagings.
                # Need t0 find how to copy ETLs.
                if copy_mapping:

                    mapping_fields = connector.get('mdmEntityMappings', None).get(schema_name)
                    if mapping_fields is not None:
                        mapping_fields.pop('mdmTenantId')
                        mapping_id = mapping_fields.pop('mdmId')
                        entity_space = mapping_fields.get('mdmEntitySpace')
                        mapping_fields.pop('mdmCreated')
                        mapping_fields.pop('mdmLastUpdated')
                        connector_id = mapping_fields.pop('mdmConnectorId')

                        mappings_to_get = stag.get_mapping_snapshot(connector_id=connector_id,mapping_id=mapping_id,
                                                                    entity_space=entity_space)
                        _, aux_map = mappings_to_get.popitem()
                        stg_to.mapping_from_snapshot(mapping_snapshot=aux_map, connector_id=conn_id.get(connector_name),
                                                     overwrite=overwrite_schema)
                        self.stag_mapp_to_use[connector_name].append({"schema": aux_schema, "mapping": aux_map})
                    else:
                        self.stag_mapp_to_use[connector_name].append({"schema": aux_schema})
                else:
                    self.stag_mapp_to_use[connector_name].append({"schema": aux_schema})
