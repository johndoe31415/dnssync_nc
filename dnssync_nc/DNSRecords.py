#	dnssync_nc - DNS API interface for the ISP netcup
#	Copyright (C) 2020-2025 Johannes Bauer
#
#	This file is part of dnssync_nc.
#
#	dnssync_nc is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	dnssync_nc is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with dnssync_nc; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import re
import sys
import enum
import collections
import dataclasses
import ipaddress
import functools
from .Exceptions import ConfigurationSyntaxError

@functools.total_ordering
class RecordType(enum.Enum):
	A = "A"
	AAAA = "AAAA"
	CNAME = "CNAME"
	MX = "MX"
	NS = "NS"
	TXT = "TXT"
	CAA = "CAA"

	def __lt__(self, other: "RecordType"):
		return self._ORDER[self] < self._ORDER[other]

RecordType._ORDER = { value: index for (index, value) in enumerate(RecordType) }


@dataclasses.dataclass(order = True, frozen = True, slots = True)
class DNSRecord():
	record_type: RecordType
	hostname: str
	destination: str
	priority: int | None = None	# Only used for MX
	record_id: int | None = dataclasses.field(repr = None, default = None, compare = False)

	@classmethod
	def deserialize(cls, data: dict):
		record_type = RecordType(data["type"])
		priority = int(data["priority"]) if (record_type == RecordType.MX) else None
		return cls(record_type = record_type, hostname = data["hostname"], destination = data["destination"], priority = priority, record_id = int(data["id"]))

	def serialize(self, delete_record: bool = False):
		serialized = {
			"type":				self.record_type.value,
			"hostname":			self.hostname,
			"destination":		self.destination,
			"deleterecord":		delete_record,
			"state":			None,
			"id":				self.record_id,
		}
		if self.priority is not None:
			serialized["priority"] = self.priority
		return serialized

	def __post_init__(self):
		if (self.priority is not None) and (self.record_type != RecordType.MX):
			raise ValueError(f"Priority only makes sense for MX records, this is a {self.record_type} record.")
		if self.record_type == RecordType.A:
			if ipaddress.ip_address(self.destination).version != 4:
				raise ValueError(f"A record requires an IPv4 address, but got: {self.destination}")
		if self.record_type == RecordType.AAAA:
			if ipaddress.ip_address(self.destination).version != 6:
				raise ValueError(f"AAAA record requires an IPv6 address, but got: {self.destination}")

	def __format__(self, fmt_str: str):
		if self.priority is None:
			return f"{self.record_type.value}	{self.hostname}	{self.destination}"
		else:
			return f"{self.record_type.value}	{self.hostname}	{self.destination}	{self.priority}"


@dataclasses.dataclass(order = True, slots = True)
class DNSZone():
	domainname: str
	ttl: int = 86400
	refresh: int = 28800
	retry: int = 7200
	expire: int = 1209600
	dnssec: bool = False
	serial: int | None = dataclasses.field(repr = None, default = None, compare = False)
	entries: list[DNSRecord] = dataclasses.field(default_factory = list, compare = False)

	@property
	def zone_values(self):
		result = dataclasses.asdict(self)
		del result["domainname"]
		del result["entries"]
		del result["serial"]
		return result

	@classmethod
	def deserialize(cls, data: dict):
		return cls(domainname = data["name"], ttl = int(data["ttl"]), serial = int(data["serial"]), refresh = int(data["refresh"]), retry = int(data["retry"]), expire = int(data["expire"]), dnssec = data["dnssecstatus"])

	def serialize(self):
		return {
			"name":				self.domainname,
			"ttl":				self.ttl,
			"refresh":			self.refresh,
			"retry":			self.retry,
			"expire":			self.expire,
			"dnssecstatus":		self.dnssec,
		}

	def print(self, f: "io.TextIOWrapper" = sys.stdout, sort_records: bool = False):
		default = DNSZone("")
		if self.serial is not None:
			print(f"# {self.domainname} serial {self.serial}")
		print(f"{self.domainname}")
		if self.ttl != default.ttl:
			print(f"	.ttl	{self.ttl}")
		if self.refresh != default.refresh:
			print(f"	.refresh	{self.refresh}")
		if self.retry != default.retry:
			print(f"	.retry	{self.retry}")
		if self.expire != default.expire:
			print(f"	.expire	{self.expire}")
		if self.dnssec != default.dnssec:
			print(f"	.dnssec	{self.dnssec}")
		seen = set()
		iterator = sorted(self.entries) if sort_records else self.entries
		for record in iterator:
			if record in seen:
				continue
			seen.add(record)
			print(f"	{record}")

	@staticmethod
	def _tobool(str_bool: str):
		if str_bool.lower() in set([ "y", "yes", "true", "on", "1" ]):
			return True
		elif str_bool.lower() in set([ "n", "no", "false", "off", "0" ]):
			return False
		else:
			raise ValueError(f"Not a valid boolean value: {str_bool}")

	def set_from_string(self, key: str, value: str):
		if key in set([ "ttl", "refresh", "retry", "expire" ]):
			setattr(self, key, int(value))
		if key == "dnssec":
			setattr(self, key, self._tobool(value))

	def __str__(self):
		return "DNSZone<%s, TTL %d, Refresh %d, Retry %d, Expire %d, DNSSec %s>" % (self.domainname, self.ttl, self.refresh, self.retry, self.expire, [ "off", "on" ][self.dnssec])


class DNSZoneLayout():
	def __init__(self, layout: collections.OrderedDict):
		self._layout = layout

	@property
	def domainnames(self):
		return iter(self._layout)

	def print(self, f: "io.TextIOWrapper" = sys.stdout, sort_records: bool = False):
		for dns_zone in self._layout.values():
			dns_zone.print(f = f, sort_records = sort_records)
			print(file = f)

	def filter_domainnames(self, domainnames: set[str]):
		domainnames = set(domainnames)
		filtered_layout = collections.OrderedDict()
		for domainname in self._layout:
			if domainname in domainnames:
				filtered_layout[domainname] = self._layout[domainname]
		return DNSZoneLayout(filtered_layout)

	def __getitem__(self, domainname: str):
		return self._layout[domainname]

	def __repr__(self):
		return repr(self._layout)


class DNSZoneParser():
	_LAYOUT_LINE_RE = re.compile("(?P<indent>\t*)(?P<content>.*)")
	_CONTENT_RE = re.compile("\t+")

	def __init__(self):
		pass

	def parse(self, dns_zone_text: str):
		layout = collections.OrderedDict()
		default_zone = DNSZone("")
		default_zone_values = default_zone.zone_values
		current_zone = None

		for (lineno, line) in enumerate(dns_zone_text.split("\n"), 1):
			if line.lstrip().startswith("#"):
				continue
			if (rematch := self._LAYOUT_LINE_RE.fullmatch(line)) is None:
				raise SyntaxError(f"Unable to parse line {lineno}: \"{line}\"")

			indent = len(rematch["indent"])
			if len(rematch["content"]) == 0:
				content = [ ]
			else:
				content = self._CONTENT_RE.split(rematch["content"])

			match (indent, content):
				case (0, (domainname, )):
					if domainname in layout:
						# Append to defined zone
						current_zone = layout[domainname]
					else:
						# New zone
						current_zone = DNSZone(domainname = domainname, **default_zone.zone_values)
						layout[current_zone.domainname] = current_zone

				case (0, (setting, value)) if setting.startswith("."):
					setting = setting[1:]
					if setting not in default_zone_values:
						raise ConfigurationSyntaxError(f"Unable to set value '{setting}' in line {lineno}. Known values are {', '.join(sorted(default_zone_values))}.")
					default_zone.set_from_string(setting, value)

				case (1, (record_type, hostname, destination)):
					if current_zone is None:
						raise ConfigurationSyntaxError(f"First need to start zone in line {lineno}.")
					try:
						record_type = RecordType(record_type)
					except ValueError:
						raise ConfigurationSyntaxError(f"Unknown record type {record_type} in line {lineno}.")
					try:
						current_zone.entries.append(DNSRecord(record_type = record_type, hostname = hostname, destination = destination))
					except ValueError as e:
						raise ConfigurationSyntaxError(f"Unable to parse DNS record in line {lineno}: {str(e)}") from e


				case (1, (record_type, hostname, destination, priority)):
					if current_zone is None:
						raise ConfigurationSyntaxError(f"First need to start zone in line {lineno}.")
					try:
						record_type = RecordType(record_type)
					except ValueError:
						raise ConfigurationSyntaxError(f"Unknown record type {record_type} in line {lineno}.")
					try:
						current_zone.entries.append(DNSRecord(record_type = record_type, hostname = hostname, destination = destination, priority = int(priority)))
					except ValueError as e:
						raise ConfigurationSyntaxError(f"Unable to parse DNS record in line {lineno}: {str(e)}") from e

				case (1, (setting, value)) if setting.startswith("."):
					setting = setting[1:]
					if setting not in default_zone_values:
						raise ConfigurationSyntaxError(f"Unable to set value '{setting}' in line {lineno}. Known values are {', '.join(sorted(default_zone_values))}.")
					try:
						current_zone.set_from_string(setting, value)
					except ValueError as e:
						raise ConfigurationSyntaxError(f"Unable to set value '{setting}' to '{value}' in line {lineno}: {str(e)}") from e

				case (0, ( )):
					pass

				case _:
					raise SyntaxError(f"Unable to parse content line {lineno}, indent {indent}: \"{content}\"")

		return DNSZoneLayout(layout)
