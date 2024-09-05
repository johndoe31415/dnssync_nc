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

import subprocess
import base64
from .Exceptions import ConfigurationSyntaxError

class SpecialDestination():
	_HANDLERS = { }

	@classmethod
	def register(cls, handler_class):
		cls._HANDLERS[handler_class._NAME] = handler_class()
		return handler_class

	@classmethod
	def parse(cls, packet):
		if "type" not in packet:
			raise ConfigurationSyntaxError("No 'type' given in special destination packet.")
		pkttype = packet["type"]
		if pkttype not in cls._HANDLERS:
			raise ConfigurationSyntaxError("Packet type '%s' is not supported." % (pkttype))
		handler = cls._HANDLERS[pkttype]
		return handler.handle(packet)

class SpecialDestinationHandler():
	_NAME = None

	def handle(self, packet):
		raise NotImplementedError()

@SpecialDestination.register
class DKIMHandler(SpecialDestinationHandler):
	_NAME = "dkim"

	def handle(self, packet):
		if "pubkey" not in packet:
			raise ConfigurationSyntaxError("dkim special destination needs 'pubkey'.")

		fields = [ ("v", "DKIM1") ]

		pubkey = subprocess.check_output([ "openssl", "pkey", "-pubin", "-text", "-noout" ], input = packet["pubkey"].encode())
		if b"ED25519 Public-Key:" in pubkey:
			# ED25519
			fields.append(("k", "ed25519"))

			pubkey = subprocess.check_output([ "openssl", "asn1parse", "-offset", "12", "-out", "-", "-noout" ], input = packet["pubkey"].encode())
			assert(len(pubkey) == 32)
			key_data = base64.b64encode(pubkey).decode("ascii")
			fields.append(("p", key_data))
		elif (b"RSA Public-Key:" in pubkey) or (b"Exponent: 65537 (0x10001)" in pubkey):
			# RSA in early OpenSSL versions uses the former syntax; on latter
			# versions this isn't obvious anymore and so we're looking for the
			# 65537 exponent, which should be a dead giveaway (but it's not a
			# clean implementation).
			fields.append(("k", "rsa"))
			if "hash" not in packet:
				raise ConfigurationSyntaxError("RSA public key requires 'hash' field to be set.")
			fields.append(("h", packet["hash"]))

			pubkey = subprocess.check_output([ "openssl", "pkey", "-pubin", "-outform", "der" ], input = packet["pubkey"].encode())
			key_data = base64.b64encode(pubkey).decode("ascii")
			fields.append(("p", key_data))
		else:
			raise ConfigurationSyntaxError("Cannot determine public key type in 'pubkey'. Only RSA and Ed25519 supported currently.")

		return ";".join("%s=%s" % (key, value) for (key, value) in fields)
