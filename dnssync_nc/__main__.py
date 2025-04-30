#!/usr/bin/python3
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
import os
import sys
import json
import dnssync_nc
import mako.lookup
from .FriendlyArgumentParser import FriendlyArgumentParser

class NetcupCLI():
	def __init__(self, args):
		self._args = args
		self._lookup = mako.lookup.TemplateLookup([ "." ] + self._args.include_dir, strict_undefined = True)

	def _login(self):
		return dnssync_nc.NetcupConnection.from_credentials_file(os.path.expanduser(self._args.credentials))

	def _render_layout_file(self, layout_filename: str):
		# Render the layout filename as a Mako template first
		template = self._lookup.get_template(layout_filename)
		template_vars = {
			"entry": dnssync_nc.EntryHelper(),
		}
		rendered = template.render(**template_vars)
		return rendered

	def _parse_layout_file(self, layout_filename: str):
		rendered = self._render_layout_file(layout_filename)
		parser = dnssync_nc.DNSZoneParser()
		layout = parser.parse(rendered)
		return layout

	def _run_push(self):
		with self._login() as ncc:
			for layout_filename in self._args.domain_data:
				layout = self._parse_layout_file(layout_filename)
				if len(self._args.domain_name) != 0:
					layout = layout.filter_domainnames(self._args.domain_name)
				ncc.push_dns_zone_layout(layout, show_diff = True, commit = self._args.commit)

	def _run_pull(self):
		with self._login() as ncc:
			layout = ncc.get_dns_zone_layout(self._args.domain_data)
			layout.print(sort_records = self._args.sort_records)

	def _run_print(self):
		for layout_filename in self._args.domain_data:
			layout = self._parse_layout_file(layout_filename)
			if len(self._args.domain_name) != 0:
				layout = layout.filter_domainnames(self._args.domain_name)
			layout.print(sort_records = self._args.sort_records)

	def run(self):
		handler = getattr(self, f"_run_{self._args.action}")
		return handler()

def main():
	parser = FriendlyArgumentParser(description = "Update DNS records using the netcup DNS API.")
	parser.add_argument("-a", "--action", choices = [ "print", "push", "pull" ], default = "print", help = "Defines the action to take. Can be one of %(choices)s, defaults to %(default)s.")
	parser.add_argument("-c", "--credentials", metavar = "filename", default = "~/.config/dnssync_nc/credentials.json", help = "Specifies credential file to use. Defaults to %(default)s.")
	parser.add_argument("-I", "--include-dir", metavar = "path", action = "append", default = [ ], help = "When rendering Mako templates, include this as a include directory as well. Can be specified multiple times.")
	parser.add_argument("-C", "--commit", action = "store_true", help = "Actually update entries instead of the default, which is to perform a dry-run.")
	parser.add_argument("-s", "--sort-records", action = "store_true", help = "Print DNS records in sorted order.")
	parser.add_argument("-d", "--domain-name", metavar = "domainname", action = "append", default = [ ], help = "Only affect these domain(s) when pushing data. Can be given multiple times. By default, all domains are affected.")
	parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
	parser.add_argument("domain_data", metavar = "layout_file/domainname", nargs = "+", help = "DNS layout file(s) when printing or pushing data or domainname(s) when pulling data.")
	args = parser.parse_args(sys.argv[1:])

	cli = NetcupCLI(args)
	cli.run()

if __name__ == "__main__":
	main()
