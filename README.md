# lektor-algolia #

lektor-algolia makes it easy to create an [Algolia](https://www.algolia.com) search index
from the data records in your [Lektor](https://github.com/lektor/lektor) project.

## Installation and Usage ##
Install with the usual Lektor toolchain. Within your project, run
```
lektor plugins add lektor-algolia
```
You should see a message saying lektor-algolia has been added to the project.

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
search indexes *but only for discoverable data models that have a boolean field `indexed`
set to `true`*.

**Important:** the index must already exist. lektor-algolia won't
automatically create the index bucket for you. Algolia has a [quick start guide](https://www.algolia.com/doc/tutorials/getting-started-realtime-search)
for how to set up your Algolia account and create an index. We recommend making
an API key that only has access to this specific index.

## Credentials ##

You need to prove to Algolia that you have permission to upload to the
index you've chosen. To do this, create a `configs/algolia.ini` file like so:

```
api_key = <YOUR-API-KEY>
app_id = <YOUR-APP-ID>
```

lektor-algolia uses Algolia's official Python rest API.

## Contributing ##

Pull requests are super useful and encouraged! Once accepted, changes
are published using lektor with `lektor dev publish-plugin`.

## Thanks ##

I basically copy-pasta'd lektor-s3 to get started with writing this plugin.
[Check out this awesome guide for making custom Lektor publishers](http://spenczar.com/posts/2015/Dec/24/lektor-publisher-plugin/).
