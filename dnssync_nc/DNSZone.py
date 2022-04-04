#	dnssync_nc - DNS API interface for the ISP netcup
#	Copyright (C) 2020-2022 Johannes Bauer
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

class DNSZone():
	def __init__(self, domainname, ttl, serial, refresh, retry, expire, dnssec):
		assert(isinstance(domainname, str))
		assert(isinstance(ttl, int))
		assert((serial is None) or isinstance(serial, int))
		assert(isinstance(refresh, int))
		assert(isinstance(retry, int))
		assert(isinstance(expire, int))
		assert(isinstance(dnssec, bool))
		self._domainname = domainname
		self._ttl = ttl
		self._serial = serial
		self._refresh = refresh
		self._retry = retry
		self._expire = expire
		self._dnssec = dnssec

	@classmethod
	def default_values(cls, domainname):
		return cls(domainname = domainname, ttl = 86400, refresh = 28800, retry = 7200, expire = 1209600, serial = None, dnssec = False)

	@classmethod
	def testing_values(cls, domainname):
		return cls(domainname = domainname, ttl = 7200, refresh = 3600, retry = 3600, expire = 1209600, serial = None, dnssec = False)

	@classmethod
	def debug_values(cls, domainname):
		return cls(domainname = domainname, ttl = 300, refresh = 1800, retry = 1800, expire = 1209600, serial = None, dnssec = False)

	@property
	def domainname(self):
		return self._domainname

	@property
	def ttl(self):
		return self._ttl

	@property
	def serial(self):
		return self._serial

	@property
	def refresh(self):
		return self._refresh

	@property
	def retry(self):
		return self._retry

	@property
	def expire(self):
		return self._expire

	@property
	def dnssec(self):
		return self._dnssec

	@classmethod
	def deserialize(cls, data):
		return cls(domainname = data["name"], ttl = int(data["ttl"]), serial = int(data["serial"]), refresh = int(data["refresh"]), retry = int(data["retry"]), expire = int(data["expire"]), dnssec = data["dnssecstatus"])

	def serialize(self):
		result = {
			"name":			self.domainname,
			"ttl":			self.ttl,
			"refresh":		self.refresh,
			"retry":		self.retry,
			"expire":		self.expire,
			"dnssecstatus":	self.dnssec,
		}
		return result

	def __eq__(self, other):
		return (self.domainname == other.domainname) and (self.ttl == other.ttl) and (self.refresh == other.refresh) and (self.retry == other.retry) and (self.expire == other.expire) and (self.dnssec == other.dnssec)

	def __neq__(self, other):
		return not (self == other)

	def __str__(self):
		return "DNSZone<%s, TTL %d, Refresh %d, Retry %d, Expire %d, DNSSec %s>" % (self.domainname, self.ttl, self.refresh, self.retry, self.expire, [ "off", "on" ][self.dnssec])
