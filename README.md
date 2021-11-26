# dnssync_nc
dnssync_nc is a Python package that can interface with the (public,
non-reseller) DNS API of the [(excellent) ISP netcup](https://www.netcup.de).
A command-line interface is provided that allows easy batch-updates of all your
domain records. You only need to create an API key in the customer control
interface, put those in a `credentials.json` file, layout your DNS in a
different JSON file and can commit that layout.

## Affiliation
I am not affiliated in any way with netcup nor have I received any money for
coding this software from anyone.

## Usage of the CLI
For the command line interface, you need a credentials file which looks like
the template in `credentials_template.json`. Then you need to specify your
domain layout in a DNS layout file. Every layout file can contain multiple
domains and multiply layout files can be used by the CLI in one pass. For
example, the layout example in `dns_layout_example.json` looks like this:

```json
{
    "domains": [
        {
            "domain":       "my-domain.de",
            "records": [
                {
                    "type":         "A",
                    "hostname":     "@",
                    "destination":  "12.34.42.42"
                },
                {
                    "type":         "A",
                    "hostname":     "*",
                    "destination":  "12.34.42.42"
                },
                {
                    "type":         "MX",
                    "hostname":     "@",
                    "destination":  "my-domain.de"
                }
            ]
        }
    ]
}
```

If you have multiple domains which are almost identically configured, you can
also use the simple but powerful templating mechanism:

```json
{
    "templates": {
        "simple-template": [
            {
                "type":         "A",
                "hostname":     "@",
                "destination":  "12.34.42.42"
            },
            {
                "type":         "A",
                "hostname":     "*",
                "destination":  "12.34.42.42"
            },
            {
                "type":         "MX",
                "hostname":     "@",
                "destination":  "${domain}"
            }
        ]
    },
    "domains": [
        {
            "domain":       "my-domain.de",
            "template":     "simple-template"
        },
        {
            "domain":       "my-other-domain.de",
            "template":     "simple-template"
        }
    ]
}
```

Here, you specify the template only once and the ${domain} variable is
substituted for each individual domain, cutting down on copy/paste work
substantially if you manage many domains.

Lasly, a "special destination" syntax supports things like putting together a
DKIM record (currently only DKIM is supported) from the root components. I.e.,
it automatically extracts the important pieces from given public keys (what
this is depends on the keytype). For example:

```json
{
    "domains": [
        {
            "domain":       "my-domain.de",
            "records": [
                {
                    "type":         "A",
                    "hostname":     "@",
                    "destination":  "12.34.42.42"
                },
                {
                    "type":         "A",
                    "hostname":     "*",
                    "destination":  "12.34.42.42"
                },
                {
                    "type":         "MX",
                    "hostname":     "@",
                    "destination":  "my-domain.de"
                },
                {
                    "type":         "TXT",
                    "hostname":     "dkim202111-ed25519._domainkey",
                    "destination":  {
                        "type": "dkim",
                        "pubkey": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAdvpXHFqOFA4gkFNoOzEfS79ZUTSy76BvN8JrhskGjLw=\n-----END PUBLIC KEY-----"
                    }
                },
                {
                    "type":         "TXT",
                    "hostname":     "dkim202111-rsa._domainkey",
                    "destination":  {
                        "type": "dkim",
                        "pubkey": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsSb1gSoKmOlZOIwehbvW\nAPWeGDqeqWvSbjKfziyIf47k4chstCscFBEeWaj7nRJ+aBVOU9Ti5bF4cCUhh6LG\nMgEymMi8TaN5gFPMHOMR30iBo/80/tNvp4vYXBNsPDo/JRIcqyuAANTxRtBWLpzH\nRUO6gHpD0jRjOBjGP011q7QQS+PDkE4azP5zyGDoai6TO/jjexiuZsMx6WGghNBN\ng9k6PUDutt/WZicvWcaOoRzVvTT2bc1g91xd8R8fMrsi42YrNnrYhfzxFqr9ouOQ\nWx6xh4J4kanotJLqvrz5oJZusqd5qe0UdckeZpeg9d2fmNNVjl0KLjMrcRwMaQjW\nvwIDAQAB\n-----END PUBLIC KEY-----",
                        "hash": "sha256"
                    }
                }
            ]
        }
    ]
}
```

Using this will create the following DNS record:

```
     1)              A    @ -> 12.34.42.42
     2)              A    * -> 12.34.42.42
     3)              MX   @ -> my-domain.de priority 10
     4)              TXT  dkim202111-ed25519._domainkey -> v=DKIM1;k=ed25519;p=dvpXHFqOFA4gkFNoOzEfS79ZUTSy76BvN8JrhskGjLw=
     5)              TXT  dkim202111-rsa._domainkey -> v=DKIM1;k=rsa;h=sha256;p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQE...
```

You can clearly see that for the RSA key, the PEM data is taken directly while
for the Ed25519 key, only the 32 bytes long pubkey is extracted into the DKIM
record.

The CLI is fairly straightforward, the help page is as follows:

```
usage: dnssync-cli [-h] [--hard-reset-all] [-d domainname] [-c filename]
                   [--commit] [-v]
                   layout_file [layout_file ...]

Update DNS records using the netcup DNS API.

positional arguments:
  layout_file           DNS layout file(s) that should be processed

optional arguments:
  -h, --help            show this help message and exit
  --hard-reset-all      Delete all existing DNS entries and re-add them one by
                        one instead of only deleting those entries which are
                        unnecessary.
  -d domainname, --domain-name domainname
                        Only affect these domain(s). Can be given multiple
                        times. By default, all domains are affected.
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
$ ./dnssync-cli -vv dns_layout.json
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
command line and your changes will be pushed to netcup.

## Usage of the API
Usage of the API is quite straightforward and an example is provided in the
given `api_example.py` file. You can easily create a connection to the API using
the convenience classmethod `NetcupConnection.from_credentials_file`:

```python
nca = dnssync_nc.NetcupConnection.from_credentials_file("credentials.json")
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
records.add(dnssync_nc.DNSRecord.new("A", "@", "123.123.123.123"))
updated_records = nca.update_dns_records(new_records)
updated_records.dump()
```

Note that the `.update_dns_records()` method will return the new effective
records.

## License
GNU GPL-3.
