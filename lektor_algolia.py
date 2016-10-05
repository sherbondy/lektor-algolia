# -*- coding: utf-8 -*-
import mimetypes
import os
from hashlib import md5

from lektor.publisher import Publisher, PublishError
from lektor.pluginsystem import Plugin
from lektor.project import Project
from lektor.types.formats import Markdown

from algoliasearch import algoliasearch

class AlgoliaPlugin(Plugin):
    name = u'algolia'
    description = u'Adds Algolia as a deploy target. Use algolia://<index> to deploy to an index.'

    def on_setup_env(self, **extra):
        config = self.get_config()
        self.env.algolia_credentials = {}
        self.env.algolia_credentials['app_id'] = config.get('app_id')
        self.env.algolia_credentials['api_key'] = config.get('api_key')
        # Modern Lektor stores publishers in env
        if hasattr(self.env, 'publishers'):
            self.env.publishers['algolia'] = AlgoliaPublisher
        # Older versions stored publishers in a global
        else:
            from lektor.publisher import publishers
            publishers['algolia'] = AlgoliaPublisher

def is_public_field(field):
    # ignore system fields and the indexed boolean
    name = field['name']
    return name[0] != '_' and name != "indexed"

def public_field_names(model_fields):
    return [field['name'] for field in model_fields if is_public_field(field)]

def stringify(record, field_name):
    val = record[field_name]
    if isinstance(val, Markdown):
        return val.source
    return unicode(val).encode('utf8')

def hit_object_ids(search_page):
    return set([hit["objectID"] for hit in search_page['hits']])

def is_indexable(record):
    return 'indexed' in record and record['indexed'] == True

def merge_credentials(config_creds, cli_creds):
    """merge config file credentials with command line credentials."""
    merged_creds = config_creds
    # do this second to prefer cli creds over config file
    if cli_creds:
        if cli_creds['username']:
            merged_creds['app_id'] = cli_creds['username']
        if cli_creds['password']:
            merged_creds['api_key'] = cli_creds['password']
        if cli_creds['key']:
            merged_creds['api_key'] = cli_creds['key']
    return merged_creds

class AlgoliaPublisher(Publisher):
    def __init__(self, env, output_path):
        super(AlgoliaPublisher, self).__init__(env, output_path)
        # algolia = the algolia client, index = the index object
        self.algolia = None
        self.index = None
        self.index_name = ''

    def split_index_uri(self, target_url):
        index_name = target_url.netloc
        return index_name

    def verify_index_exists(self):
        exists = True
        try:
            settings = self.index.get_settings()
        except algoliasearch.AlgoliaException as e:
            print e
            exists = False
        return exists

    def list_remote(self):
        "handle pagination eventually..."
        all_object_ids = set()
        params = {'attributesToRetrieve': 'objectID', 'hitsPerPage': 100}
        first_page = self.index.search('', params)
        first_page_hits = hit_object_ids(first_page)
        all_object_ids.update(first_page_hits)
        page_count = first_page['nbPages']
        for i in range(1, page_count):
            next_page = self.index.search('', params.extend({'page': i}))
            if next_page["nbHits"] > 0:
                next_page_hits = hit_object_ids(next_page['hits'])
                all_object_ids.update(next_page_hits)
            else:
                break
        return all_object_ids

    def add_index_children_json(self, pad, record):
        record_json = []
        for child in record.children.all():
            if is_indexable(child):
                model = child.datamodel
                model_json = model.to_json(pad, child)
                model_field_names = public_field_names(model_json['fields'])
                child_data = {field_name: stringify(child, field_name) for field_name in model_field_names}
                child_data['objectID'] = child['_gid']
                # upload path so we can send the user to the right url for a search query!
                child_data['_path'] = child['_path']
                record_json.append(child_data)
            record_json += self.add_index_children_json(pad, child)
        return record_json

    def list_local(self):
        all_records = []
        project = Project.discover()
        env = project.make_env()
        pad = env.new_pad()
        root = pad.root
        all_records = self.add_index_children_json(pad, root)
        return all_records

    def compute_diff(self, local_keys, remote_keys):
        """Compute the changeset for updating remote to match local"""
        diff = {
            'add': [],
            'delete': [],
        }
        diff['delete'] = remote_keys.difference(local_keys)
        diff['add'] = local_keys
        return diff

    def connect(self, credentials):
        self.algolia = algoliasearch.Client(
            credentials['app_id'], credentials['api_key']
        )

    def publish(self, target_url, credentials=None, **extra):
        merged_creds = merge_credentials(self.env.algolia_credentials, credentials)

        yield "Checking for Algolia credentials and index..."
        if 'app_id' in merged_creds and 'api_key' in merged_creds:
            self.connect(merged_creds)

            self.index_name = self.split_index_uri(target_url)
            self.index = self.algolia.init_index(self.index_name)
            if not self.verify_index_exists():
                raise PublishError(
'Algolia index "%s" does not exist, or the API key provided does not have access to it. \
Please create the index / verify your credentials on their website.'
% self.index_name
                )

            yield "Verified Algolia index exists and is accessible via your credentials."

            local = self.list_local()
            local_keys = set([record['objectID'] for record in local])
            remote = self.list_remote()

            yield "Found %d local records to index." % len(local)
            yield "Found %d existing remote records in the index." % len(remote)

            yield "Computing diff for index update..."
            diff = self.compute_diff(local_keys, remote)
            res_delete = self.index.delete_objects(list(diff['delete']))
            delete_count = len(res_delete['objectIDs'])
            yield "Deleted %d stale records from remote index." % delete_count

            res_add = self.index.save_objects(local)
            add_count = len(res_add['objectIDs'])
            yield "Finished submitting %d new/updated records to the index." % add_count
            yield "Processing the updated index is asynchronous, so Aloglia may take a while to reflect the changes."

        else:
            yield 'Could not connect to Algolia.'
            yield 'Make sure api_key and app_id are present in your configs/algolia.ini file.'
