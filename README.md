# lektor-algolia #

lektor-algolia makes it easy to create an [Algolia](https://www.algolia.com) search index
from the data records in your [Lektor](https://github.com/lektor/lektor) project.

## Installation and Usage ##
Install with the usual Lektor toolchain. Within your project, run
```
lektor plugins add lektor-algolia
```
You should see a message saying lektor-algolia has been added to the project.

[Here's a link to the project on pypi](https://pypi.python.org/pypi/lektor-algolia) if you want to install through unconventional means.

Next, add an index and an API key with write access to that index to your
Algolia account via their website. Then, in your project file
(like `blog.lektorproject`), add the following:

```
[servers.algolia]
name = Algolia
enabled = yes
target = algolia://<YOUR-INDEX>
```

For example, if you wanted to deploy to a search index named 'books',
you'd make that last line

```
target = algolia://books
```

Now, if you call `lektor deploy algolia`, Lektor will automatically generate
search indexes *but only for discoverable data models that have a boolean field named `indexed`
that is set to `true`*.

**Important:** the index must already exist. lektor-algolia won't
automatically create the index for you. Algolia has a [quick start guide](https://www.algolia.com/doc/tutorials/getting-started-realtime-search)
for how to set up your Algolia account and create an index. We recommend making
an API key that only has access to this specific index.

## Credentials ##

You need to prove to Algolia that you have permission to upload to the
index you've chosen. To do this, create a `configs/algolia.ini` file in your project root that looks like this:

```
api_key = <YOUR-API-KEY>
app_id = <YOUR-APP-ID>
```

## Contributing ##

Pull requests are super useful and encouraged! Once accepted, changes
are published using lektor with `lektor dev publish-plugin`.

If you want to hack on the plugin and test it with a lektor project, you can clone this repo or symlink it into the folder `packages/lektor-algolia`
in your project.

Low hanging fruit:

- No intelligent diffing is done right now to see if models have actually been updated (we delete removed models, but resync existing models every time).
- Deploys probably fail for models with certain data types, because the way I am serializing record values is very naive.
- Could do more slick things with configuring what should be indexed where. Could support multiple indexes in one site,
  and mappings could be provided via config rather than the existence of an `indexed` property on models.
- Needs to be much more robust... Should find out what the maximum number of object IDs we can actually pull per request is...
- Tests. Lots and lots of tests. Setup CI server with throway algolia index...

High hanging fruit:

- Why let Algolia have all of the fun? It'd be super slick to generate and serialize a client-side index data structure that can be stored on the site and queried via JavaScript.

## Thanks ##

I basically copy-pasta'd [lektor-s3](https://github.com/spenczar/lektor-s3) to get started with writing this plugin.
[Check out this awesome guide for making custom Lektor publishers](http://spenczar.com/posts/2015/Dec/24/lektor-publisher-plugin/).
