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

import json
import collections
import requests
from dnssync_nc import DNSZone, DNSRecord, DNSZoneLayout
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

	def _session_action(self, action_name: str, params = None):
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
			if response["data"]["status"] == "success":
				self._session_id = response["data"]["responsedata"]["apisessionid"]
			else:
				raise ServerResponseError(f"Login to netcup failed for customer ID {self._credentials['customer']}: {response['data']['longmessage']} (status code {response['data']['statuscode']})")
		return response

	def logout(self):
		return self._session_action("logout")

	def _info_dns_records(self, domainname: str):
		response = self._session_action("infoDnsRecords", {
			"domainname":				domainname,
		})
		if response["status"] != 200:
			raise ServerResponseError("Unable to retrieve DNS records (no HTTP 200):", response)
		if response["data"]["status"] != "success":
			raise ServerResponseError("Unable to retrieve DNS records (no 'success' status): %s" % (response["data"]["longmessage"]))
		return [ DNSRecord.deserialize(record_dict) for record_dict in response["data"]["responsedata"]["dnsrecords"] ]

	def _info_dns_zone(self, domainname: str):
		response = self._session_action("infoDnsZone", {
			"domainname":				domainname,
		})
		if response["status"] != 200:
			raise ServerResponseError("Unable to retrieve DNS zone:", response)
		if response["data"]["status"] != "success":
			raise ServerResponseError(f"Unable to get DNS zone information customer ID {self._credentials['customer']}: {response['data']['longmessage']} (status code {response['data']['statuscode']})")
		return DNSZone.deserialize(response["data"]["responsedata"])

	def _get_dns_zone(self, domainname: str):
		dns_zone = self._info_dns_zone(domainname)
		dns_zone.entries += self._info_dns_records(domainname)
		return dns_zone

	def get_dns_zone_layout(self, domainnames: list[str]):
		layout = collections.OrderedDict()
		for domainname in domainnames:
			layout[domainname] = self._get_dns_zone(domainname)
		return DNSZoneLayout(layout)

	def _update_dns_records(self, domainname: str, dns_record_set: list[dict]):
		response = self._session_action("updateDnsRecords", {
			"domainname": domainname,
			"dnsrecordset": {
				"dnsrecords": dns_record_set,
			},
		})
		if response["status"] != 200:
			raise ServerResponseError(f"Unable to update DNS records of {domainname}: HTTP {response['status']}")
		if response["data"]["status"] != "success":
			raise ServerResponseError(f"Unable to update DNS records of {domainname}: {response['data']['longmessage']} (status code {response['data']['statuscode']})")

	def _update_dns_zone(self, dns_zone: DNSZone):
		assert(isinstance(dns_zone, DNSZone))
		response = self._session_action("updateDnsZone", {
			"domainname":				dns_zone.domainname,
			"dnszone":					dns_zone.serialize(),
		})
		if response["status"] == 200:
			return DNSZone.deserialize(response["data"]["responsedata"])
		else:
			raise ServerResponseError("Unable to update DNS zone:", response)

	def _push_dns_zone(self, current_zone: DNSZone, new_zone: DNSZone, show_diff: bool = False, commit: bool = False):
		if current_zone != new_zone:
			if show_diff:
				print(f"-{current_zone}")
				print(f"+{new_zone}")
			if commit:
				self._update_dns_zone(new_zone)

		added_records = [ ]
		current_records = set(current_zone.entries)
		for new_record in new_zone.entries:
			if new_record in current_records:
				# Already present, no change necessary
				current_records.remove(new_record)
			else:
				added_records.append(new_record)

		removed_records = list(sorted(current_records))

		if show_diff:
			for record in removed_records:
				print(f"-{current_zone.domainname} {record}")
			for record in added_records:
				print(f"+{current_zone.domainname} {record}")

		if commit:
			dns_record_set = [ ]
			for record in removed_records:
				dns_record_set.append(record.serialize(delete_record = True))
			for record in added_records:
				dns_record_set.append(record.serialize())
			self._update_dns_records(current_zone.domainname, dns_record_set)

	def push_dns_zone_layout(self, new_layout: DNSZoneLayout, show_diff: bool = False, commit: bool = False):
		current_layout = self.get_dns_zone_layout(new_layout.domainnames)
		for domainname in current_layout.domainnames:
			self._push_dns_zone(current_layout[domainname], new_layout[domainname], show_diff = show_diff, commit = commit)

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
