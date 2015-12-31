# -*- coding: utf-8 -*-
import mimetypes
import os
from hashlib import md5

from lektor.publisher import Publisher
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


def public_field_names(model_fields):
    return [field['name'] for field in model_fields if field['name'][0] != '_']

def stringify(record, field_name):
    val = record[field_name]
    if isinstance(val, Markdown):
        return val.source
    return str(val)

def hit_object_ids(search_page):
    return set([hit["objectID"] for hit in search_page['hits']])

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
            print(settings)
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
            if not child.is_hidden and 'indexed' in child and child['indexed'] == True:
                model = child.datamodel
                model_json = model.to_json(pad, child)
                model_field_names = public_field_names(model_json['fields'])
                child_data = {field_name: stringify(child, field_name) for field_name in model_field_names}
                child_data['objectID'] = child['_gid']
                print(child_data)
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

    def file_md5(self, filename):
        '''Compute the md5 checksum for a file.'''
        md5sum = md5()
        with open(filename, 'rb') as f:
            data = f.read(8192)
            while len(data) > 0:
                md5sum.update(data)
                data = f.read(8192)
        return md5sum.hexdigest()

    def obj_md5(self, obj):
        """Compute the md5 checksum for an S3 object.

        MD5s can be stored in the 'ETag' field of S3 objects. The
        field doesn't store the MD5 in two cases: objects uploaded
        with Multipart Upload and objects encrypted with SSE-C or
        SSE-KMS. In those cases, we'll just return an empty string.

        """

        # Multipart-uploaded messages have etags that look like 'xxx-nnn'
        if '-' in obj.e_tag:
            return ''

        # SSE-C and SSE-KMS-encrypted objects have a few values set
        # when you call HeadObject on them
        obj_meta = self.s3.meta.client.head_object(
            Bucket=obj.bucket_name,
            Key=obj.key,
        )
        if obj_meta.get('SSECustomerAlgorithm') is not None:
            return ''
        if obj_meta.get('ServerSideEncryption') == 'aws:kms':
            return ''

        # Else, the etag stores an md5 checksum enclosed in double quotes
        return obj.e_tag.strip('"')

    def different(self, local_filename, remote_obj):
        """Return true if the local file is different than the remote object."""
        abs_filename = os.path.join(self.output_path, local_filename)
        # Check size first.
        if remote_obj.size != os.path.getsize(abs_filename):
            return True

        # check md5
        if self.file_md5(abs_filename) != self.obj_md5(remote_obj):
            return True

        # they're the same
        return False

    def compute_diff(self, local_keys, remote_keys):
        """Compute the changeset for updating remote to match local"""
        diff = {
            'add': [],
            'delete': [],
        }
        diff['delete'] = remote_keys.difference(local_keys)
        diff['add'] = local_keys
        return diff

    def add(self, filename):
        abs_filename = os.path.join(self.output_path, filename)
        key = self.key_prefix + filename

        mime, _ = mimetypes.guess_type(filename)
        if mime is None:
            mime = "text/plain"
        self.bucket.upload_file(abs_filename, key, ExtraArgs={'ContentType': mime})

    def update(self, filename):
        # Updates are just overwrites in S3
        self.add(filename)

    def delete_batch(self, filenames):
        if len(filenames) == 0:
            return
        self.bucket.delete_objects(
            Delete={'Objects': [{'Key': self.key_prefix + f} for f in filenames]}
        )

    def connect(self, credentials):
        self.algolia = algoliasearch.Client(
            credentials['app_id'], credentials['api_key']
        )

    def publish(self, target_url, credentials=None):
        credentials = self.env.algolia_credentials

        yield "credentials: {}".format(credentials)
        if 'app_id' in credentials and 'api_key' in credentials:
            self.connect(credentials)

            self.index_name = self.split_index_uri(target_url)
            self.index = self.algolia.init_index(self.index_name)
            if not self.verify_index_exists():
                raise PublishError(
                    'Algolia index "%s" does not exist, or the API key provided does not have access to it. \
                    Please create the index / verify your credentials on their website.'
                    % bucket_uri
                )

            local = self.list_local()
            local_keys = set([record['objectID'] for record in local])
            remote = self.list_remote()

            yield "listing local files to index in algolia..."
            for record in local:
                print record
            yield "printing remote files"
            print remote

            diff = self.compute_diff(local_keys, remote)
            # We will not distinguish between add and update, just add and delete.
            # for f in diff['add']:
            #     yield 'adding %s' % f
            #     self.add(f)
            #
            #
            # for f in diff['delete']:
            #     yield 'deleting %s' % f
            # self.delete_batch(diff['delete'])
            res_delete = self.index.delete_objects(list(diff['delete']))
            print "Deletion result:"
            print res_delete

            res_add = self.index.save_objects(local)
            print "Add result:"
            print res_add

        else:
            yield 'Could not connect to Algolia.'
            yield 'Make sure api_key and app_id are present in your configs/algolia.ini file.'
