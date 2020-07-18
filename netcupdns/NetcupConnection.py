#	netcupdns - DNS API interface for the hoster Netcup
#	Copyright (C) 2020-2020 Johannes Bauer
#
#	This file is part of netcupdns.
#
#	netcupdns is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	netcupdns is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with netcupdns; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import json
import requests
from .DNSZone import DNSZone
from .DNSRecords import DNSRecord, DNSRecordSet
from .Exceptions import ServerResponseError

class NetcupConnection():
	def __init__(self, json_endpoint_uri, customer, api_key, api_password):
		self._uri = json_endpoint_uri
		self._credentials = {
			"customer":		customer,
			"api_key":		api_key,
			"api_password":	api_password,
		}
		self._session = requests.Session()
		self._session_id = None

	@property
	def logged_in(self):
		return self._session_id is not None

	def _action(self, action_name, params):
		payload = {
			"action":	action_name,
			"param":	params,
		}
		payload_data = json.dumps(payload)
		response = self._session.post(self._uri, data = payload_data)
		return {
			"status":	response.status_code,
			"data":		response.json(),
		}

	def _session_action(self, action_name, params = None):
		if self._session_id is None:
			print("Cannot execute '%s' without a valid session.", file = sys.stderr)
			return
		if params is None:
			params = { }
		params.update({
			"apikey":			self._credentials["api_key"],
			"apisessionid":		self._session_id,
			"customernumber":	str(self._credentials["customer"]),
		})
		return self._action(action_name, params)

	def login(self):
		response = self._action("login", {
			"apikey":			self._credentials["api_key"],
			"apipassword":		self._credentials["api_password"],
			"customernumber":	str(self._credentials["customer"]),
		})
		if response["status"] == 200:
			self._session_id = response["data"]["responsedata"]["apisessionid"]
		return response

	def logout(self):
		return self._session_action("logout")

	def list_all_domains(self):
		return self._session_action("listallDomains")

	def info_dns_records(self, domainname):
		response = self._session_action("infoDnsRecords", {
			"domainname":				domainname,
		})
		if response["status"] != 200:
			raise ServerResponseError("Unable to retrieve DNS records:", response)
		return DNSRecordSet.deserialize(domainname, response["data"]["responsedata"])

	def info_dns_zone(self, domainname):
		response = self._session_action("infoDnsZone", {
			"domainname":				domainname,
		})
		if response["status"] != 200:
			raise ServerResponseError("Unable to retrieve DNS zone:", response)
		return DNSZone.deserialize(response["data"]["responsedata"])

	def update_dns_records(self, dns_records):
		assert(isinstance(dns_records, DNSRecordSet))
		response = self._session_action("updateDnsRecords", {
			"domainname":				dns_records.domainname,
			"dnsrecordset":				dns_records.serialize(),
		})
		if response["status"] == 200:
			return DNSRecordSet.deserialize(dns_records.domainname, response["data"]["responsedata"])
		else:
			raise ServerResponseError("Unable to update DNS records:", response)

	def update_dns_zone(self, dns_zone):
		assert(isinstance(dns_zone, DNSZone))
		response = self._session_action("updateDnsZone", {
			"domainname":				dns_zone.domainname,
			"dnszone":					dns_zone.serialize(),
		})
		if response["status"] == 200:
			return DNSZone.deserialize(response["data"]["responsedata"])
		else:
			raise ServerResponseError("Unable to update DNS zone:", response)

	def __enter__(self):
		self.login()
		return self

	def __exit__(self, *args):
		self.logout()

	@classmethod
	def from_credentials_file(cls, filename):
		with open(filename) as f:
			config = json.load(f)
		return cls(json_endpoint_uri = config["json_endpoint"], customer = config["customer"], api_password = config["api_password"], api_key = config["api_key"])
