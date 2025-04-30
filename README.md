# dnssync_nc
dnssync_nc is a Python package that can interface with the (public,
non-reseller) DNS API of the [(excellent) ISP netcup](https://www.netcup.de).
A command-line interface is provided that allows easy batch-updates of all your
domain records. You only need to create an API key in the customer control
interface, put those in a JSON file typically located in
`~/.config/dnssync_nc/credentials.json` file, layout your DNS in a TXT file and
can commit that layout.

The text file that comprises the DNS zone layout is first rendered through the
Mako preprocessor, which enables powerful templating features. This is
exceptionally useful if you are managing many domains with largely identical
DNS settings.


## Older versions
The file format in which DNS zones are implemented has radically changed from
version v0.0.1 to v1.0.1, a clear breaking change. If you do still want to use
the old JSON format, you need to make sure that you are using version v0.0.1.
To get started with the new format, however, there is a new `pull` command that
lets you pull the current DNS configuration off netcup and creates a text file
from that which can be used to push the configuration. Note that the API
documentation has been removed, it also has changed in v1.0.1 slightly but it
should be straightforward to see how it works from `__main__.py`.


## Affiliation
I am not affiliated in any way with netcup nor have I received any money for
coding this software from anyone.


## Zone format
You need to specify your domain layout in a text layout file. Every layout file
can contain multiple domains and multiple layout files can be used by the CLI
in one pass. For example, the layout example in
`01_simple.txt` looks like this:

```txt
my-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-domain.de
```

Note that as a field separator, tabs *must* be used. In the destination field,
spaces are a valid character and this makes parsing of the text files much
easier.

If you have multiple domains which are almost identically configured, you can
also use the simple but powerful templating mechanism that Mako provides, as
seen in `02_multiple.txt`:

```txt
<%
	default_ipv4_address = "12.34.42.42"
%>\
%for domainname in [ "my-domain.de", "my-other-domain.com", "my-third-domain.to" ]:
${domainname}
	A	@	${default_ipv4_address}
	A	*	${default_ipv4_address}
	MX	*	${domainname}
%endfor
```

Note that this is equivalent to writing the quite repetitive:

```txt
my-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-domain.de

my-other-domain.com
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-other-domain.com

my-third-domain.to
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-third-domain.to
```

Domains can appear multiple times in the configuration file; the semantic is
that all records are added. This allows you to easily specify a general
template for most domains, but make exceptions for some domains. For example,
consider the example `03_exception.txt`:

```txt
<%
	default_ipv4_address = "12.34.42.42"
	domainnames = [ "my-domain.de", "my-other-domain.com", "my-third-domain.to", "exceptional-domain.de", "my-fifth-domain.de" ]
%>\
%for domainname in domainnames:
${domainname}
	A	@	${default_ipv4_address}
	A	*	${default_ipv4_address}
	MX	*	${domainname}
%endfor

%for domainname in set(domainnames) - set([ "exceptional-domain.de" ]):
${domainname}
	TXT	@	v=spf1 mx -all
%endfor

exceptional-domain.de
	TXT	@	v=spf1 include:third-party-mailsite.org ~all
```

Here, there is a standard SPF record that points to the MX for all domains
exception `exceptional-domain.de`. That domain gets its own SPF entry. In other
words, that syntax is equivalent to:

```txt
my-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-domain.de
	TXT	@	v=spf1 mx -all

my-other-domain.com
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-other-domain.com
	TXT	@	v=spf1 mx -all

my-third-domain.to
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-third-domain.to
	TXT	@	v=spf1 mx -all

exceptional-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	exceptional-domain.de
	TXT	@	v=spf1 include:third-party-mailsite.org ~all

my-fifth-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-fifth-domain.de
	TXT	@	v=spf1 mx -all
```

Lasly, a "special destination" syntax supports things like putting together a
DMARC or DKIM record easily. I.e., for DKIM records it automatically extracts
the important pieces from given public keys (what those are depends on the
keytype, Ed25519 and RSA are supported). For example, see the example in
`04_special.txt`:

```txt
my-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-domain.de
	${entry.dmarc(mailto = "dmarc@my-domain.de")}
	${entry.dkim(keyname = "dkim202204", hashfnc = "sha256", pubkey = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvVMIyJGMS6JqtvF8GWny
v/tFGaMPlXz9jr8HF6ddi2HRHEplgz6bEZQjkymZiUvdutBKhQYVfHRn1j6Ml3fx
TbsuETM4vuJWkgsuWhyFGqMyYCdlm/4zDPN9r9o+yjA7vWV45Ttce9GLGPyvGjik
jfPRn0++Py3Vvh6qwOBsr3uDYoXinZ/UlN3evllIEaX7EWOY2RAdYY8P1Kuls89D
vSp/Rcngxq0Nv/puhEpVsoRErM2iW+wrRUvPjwN8lc9IBMJrRpLEnN7VmbazlL5q
vvkyBha8h2sXQc6G4RehhJ5qwNZ8KIIMJumzolFns2RK4gN61gZ5i1EjeR+WUSCc
jQIDAQAB
-----END PUBLIC KEY-----
""")}
	${entry.dkim(keyname = "dkim202504", pubkey = """
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAJo+ts7Bogx2/9R6qDZBvOjWf95FPi1hZOxpFoQW0f7k=
-----END PUBLIC KEY-----
""")}
```

This creates two DKIM entries with an RSA and Ed25519 key, respectively, as
well as a DMARC key. It is equivalent to:

```txt
my-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-domain.de
	TXT	_dmarc	v=DMARC1;p=none;adkim=r;aspf=r;pct=100;rua=mailto:dmarc@my-domain.de;ruf=mailto:dmarc@my-domain.de
	TXT	dkim202204._domainkey	v=DKIM1;k=rsa;h=sha256;p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvVMIyJGMS6JqtvF8GWnyv/tFGaMPlXz9jr8HF6ddi2HRHEplgz6bEZQjkymZiUvdutBKhQYVfHRn1j6Ml3fxTbsuETM4vuJWkgsuWhyFGqMyYCdlm/4zDPN9r9o+yjA7vWV45Ttce9GLGPyvGjikjfPRn0++Py3Vvh6qwOBsr3uDYoXinZ/UlN3evllIEaX7EWOY2RAdYY8P1Kuls89DvSp/Rcngxq0Nv/puhEpVsoRErM2iW+wrRUvPjwN8lc9IBMJrRpLEnN7VmbazlL5qvvkyBha8h2sXQc6G4RehhJ5qwNZ8KIIMJumzolFns2RK4gN61gZ5i1EjeR+WUSCcjQIDAQAB
	TXT	dkim202504._domainkey	v=DKIM1;k=ed25519;p=Jo+ts7Bogx2/9R6qDZBvOjWf95FPi1hZOxpFoQW0f7k=
```

You can clearly see that in conformance with the standard for the RSA key, the
PEM data is taken directly while for the Ed25519 key, only the 32 bytes long
pubkey is extracted into the DKIM record.

DNS zone settings can also be set, either on the root level (without
indentation) and will affect all *new* entries going forward or inside the
domain itself to override defaults. Such an example is shown in
`05_zone_settings.txt`:

```txt
# These are the default parameters for the coming domains:
.ttl 3600
.retry 1234

my-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-domain.de

my-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-domain.de

# This domain DNS zone has a special TTL
override-domain.de
	.ttl 999
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-domain.de
```




## Usage of the CLI
The CLI is fairly straightforward, the help page is as follows:

```
usage: dnssync-cli [-h] [-a {print,push,pull}] [-c filename] [-I path] [-C]
                   [-s] [-d domainname] [-v]
                   layout_file/domainname [layout_file/domainname ...]

Update DNS records using the netcup DNS API.

positional arguments:
  layout_file/domainname
                        DNS layout file(s) when printing or pushing data or
                        domainname(s) when pulling data.

options:
  -h, --help            show this help message and exit
  -a, --action {print,push,pull}
                        Defines the action to take. Can be one of print, push,
                        pull, defaults to print.
  -c, --credentials filename
                        Specifies credential file to use. Defaults to
                        ~/.config/dnssync_nc/credentials.json.
  -I, --include-dir path
                        When rendering Mako templates, include this as a
                        include directory as well. Can be specified multiple
                        times.
  -C, --commit          Actually update entries instead of the default, which
                        is to perform a dry-run.
  -s, --sort-records    Print DNS records in sorted order.
  -d, --domain-name domainname
                        Only affect these domain(s) when pushing data. Can be
                        given multiple times. By default, all domains are
                        affected.
  -v, --verbose         Increases verbosity. Can be specified multiple times
                        to increase.
```

There are three main actions:

  - `print`: Default action. Just render a template and print out what
    effectively would be set. Does not need credentials.
  - `pull`: Pull the domain zone data off netcup and create a TXT output file
    that can be used for pushing.
  - `push`: Push domain zone data to netcup.


So when we want to verify records, we can simply do so by using `print`:

```
$ dnssync-cli examples/01_simple.txt
my-domain.de
	A	@	12.34.42.42
	A	*	12.34.42.42
	MX	*	my-domain.de
```

When you want to pull data from or push data to netcup, you need a credentials
file which looks like the template in `credentials_template.json`. When you
store this file at `~/.config/dnssync_nc/credentials.json` it is automatically
used by default. When we have created that credentials file, we can pull data
off netcup:

```
$ dnssync-cli -a pull my-domain.de >current_config.txt

$ cat current_config.txt
# my-domain.de serial 2025043019
my-domain.de
	.ttl	300
	.refresh	1800
	.retry	1800
	CNAME	*	my-domain.de
	CAA	@	0 issue "letsencrypt.org"
	A	@	11.22.33.44
	AAAA	@	2a03:1111:22:333::1
	MX	@	my-domain.de	10
	TXT	@	v=spf1 mx a:my-domain.de -all
```

This file can then be used directly to push (possibly after having made
changes). For example, let us change the A record to point to `9.9.9.9` and
verify what would happen:

```
$ dnssync-cli -a push current_config.txt
-my-domain.de A	@	11.22.33.44
+my-domain.de A	@	9.9.9.9
```

Note that these changes have **not** been pushed to netcup yet. However, it has
automatically pulled the configuration off netcup and displayed the exact diff.
Similarly, if you were to modify the TTL settings, this would also be shown.
For example, let us additionally modify the TTL to be one hour:

```
$ dnssync-cli -a push current_config.txt
-DNSZone<my-domain.de, TTL 300, Refresh 1800, Retry 1800, Expire 1209600, DNSSec off>
+DNSZone<my-domain.de, TTL 3600, Refresh 1800, Retry 1800, Expire 1209600, DNSSec off>
-my-domain.de A	@	11.22.33.44
+my-domain.de A	@	9.9.9.9
```

Note that it now would also update the DNS zone data. If we actually want to
push the data to netcup, we have to commit it:

```
$ dnssync-cli -a push --commit current_config.txt
-DNSZone<my-domain.de, TTL 300, Refresh 1800, Retry 1800, Expire 1209600, DNSSec off>
+DNSZone<my-domain.de, TTL 3600, Refresh 1800, Retry 1800, Expire 1209600, DNSSec off>
-my-domain.de A	@	11.22.33.44
+my-domain.de A	@	9.9.9.9
```

## License
GNU GPL-3.
