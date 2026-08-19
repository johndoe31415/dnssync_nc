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

import subprocess
import base64
from .Exceptions import ConfigurationSyntaxError

class EntryHelper():
	def dmarc(self, mailto: str):
		return f"TXT	_dmarc	v=DMARC1;p=none;adkim=r;aspf=r;pct=100;rua=mailto:{mailto};ruf=mailto:{mailto}"

	def dkim(self, keyname: str, pubkey: str, hashfnc: str | None = None):
		fields = [ ("v", "DKIM1") ]

		textkey = subprocess.check_output([ "openssl", "pkey", "-pubin", "-text", "-noout" ], input = pubkey.encode())
		if b"ED25519 Public-Key:" in textkey:
			# ED25519
			fields.append(("k", "ed25519"))

			pubkey = subprocess.check_output([ "openssl", "asn1parse", "-offset", "12", "-out", "-", "-noout" ], input = pubkey.encode())
			assert(len(pubkey) == 32)
			key_data = base64.b64encode(pubkey).decode("ascii")
			fields.append(("p", key_data))
		elif (b"RSA Public-Key:" in textkey) or (b"Exponent: 65537 (0x10001)" in textkey):
			# RSA in early OpenSSL versions uses the former syntax; on latter
			# versions this isn't obvious anymore and so we're looking for the
			# 65537 exponent, which should be a dead giveaway (but it's not a
			# clean implementation).
			fields.append(("k", "rsa"))
			if hashfnc is None:
				raise ConfigurationSyntaxError("RSA public key requires 'hashfnc' option to be set in the 'dkim' helper function.")
			fields.append(("h", hashfnc))

			pubkey = subprocess.check_output([ "openssl", "pkey", "-pubin", "-outform", "der" ], input = pubkey.encode())
			key_data = base64.b64encode(pubkey).decode("ascii")
			fields.append(("p", key_data))
		else:
			raise ConfigurationSyntaxError("Cannot determine public key type in 'pubkey'. Only RSA and Ed25519 supported currently.")

		destination = ";".join("%s=%s" % (key, value) for (key, value) in fields)
		return f"TXT	{keyname}._domainkey	{destination}"
