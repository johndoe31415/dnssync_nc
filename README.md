# netcupdns
netcupdns is a Python package that can interface with the (public,
non-reseller) DNS API of the [(excellent) hoster NetCup](https://www.netcup.de).
A command-line interface is provided that allows easy batch-updates of all your
domain records. You only need to create an API key in the customer control
interface, put those in a `credentials.json` file, layout your DNS in a
different JSON file and can commit that layout.

## Usage of the CLI
For the command line interface, you need a credentials file which looks like
the template in `credentials_template.json`. Then you need to specify your
domain layout in a DNS layout file. Every layout file can contain multiple
domains and multiply layout files can be used by the CLI in one pass. For
example, the layout example in `dns_layout_example.json` looks like this:

```json
[
	{
		"domain":		"my-domain.de",
		"records": [
			{
				"type":			"A",
				"hostname":		"@",
				"destination":	"12.34.42.42"
			},
			{
				"type":			"A",
				"hostname":		"*",
				"destination":	"12.34.42.42"
			},
			{
				"type":			"MX",
				"hostname":		"my-domain.de",
				"destination":	"my-domain.de"
			}
		]
	}
]
```

The CLI is fairly straightforward, the help page is as follows:

```
usage: netcupcli [-h] [-c filename] [--commit] [-v]
                 layout_file [layout_file ...]

Update DNS records using the Netcup DNS API.

positional arguments:
  layout_file           DNS layout file(s) that should be processed

optional arguments:
  -h, --help            show this help message and exit
  -c filename, --credentials filename
                        Specifies credential file to use. Defaults to
                        credentials.json.
  --commit              By default, only records are read and printed on the
                        command line. This actually puts into effect the
                        requested changes.
  -v, --verbose         Increases verbosity. Can be specified multiple times
                        to increase.
```

If you just want to see what your changes would look like, simply do:

```
$ ./netcupcli -vv dns_layout.json
Processing layout file dns_layout.json: 1 domain entries found.
Layout of domain my-domain.de consists of 3 DNS records.
Current DNS records of my-domain.de (3 records):
     1) [  12345673] A    * -> 1.2.3.4
     2) [  12345672] A    @ -> 1.2.3.4
     3) [  12345674] MX   my-domain.de -> my-domain.de priority 10

Proposed DNS update records of my-domain.de (6 records):
     1) [  12345673] A    * -> 1.2.3.4 <DELETE>
     2) [  12345672] A    @ -> 1.2.3.4 <DELETE>
     3) [  12345674] MX   my-domain.de -> my-domain.de priority 10 <DELETE>
     4)              A    @ -> 1.2.3.4
     5)              A    * -> 1.2.3.4
     6)              MX   my-domain.de -> my-domain.de priority 10

Not updating record of my-domain.de to live system (no commit requested).
```

If you want to put those changes in effect, simply add `--commit` to the
command line and your changes will be pushed to Netcup.

## Usage of the API
Usage of the API is quite straightforward and an example is provided in the
given `api_example.py` file. You can easily create a connection to the API using
the convenience classmethod `NetcupConnection.from_credentials_file`:

```python
nca = netcupdns.NetcupConnection.from_credentials_file("credentials.json")
```

Then, `login` and `logout` can be automatically performed when you use the
context manager:

```python
with nca:
    # Do something
```

You can easily retrieve data:

```python
print(nca.info_dns_zone("my-domain.de"))
print(nca.info_dns_records("my-domain.de"))
```

For DNS record display that is more verbose, you can also use the `.dump()`
method:

```python
nca.info_dns_records("my-domain.de").dump()
```

If you want to modify entries, you can simply first query the API, delete all
present entries, add new ones, then commit the changes:

```python
records = nca.info_dns_records("my-domain.de")
records.delete_all()
records.add(netcupdns.DNSRecord.new("A", "@", "123.123.123.123"))
updated_records = nca.update_dns_records(new_records)
updated_records.dump()
```

Note that the `.update_dns_records()` method will return the new effective
records.

## License
GNU GPL-3.
