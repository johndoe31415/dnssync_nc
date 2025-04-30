import setuptools

with open("README.md") as f:
	long_description = f.read()

setuptools.setup(
	name = "dnssync_nc",
	packages = setuptools.find_packages(),
	version = "1.0.3rc0",
	license = "GPL-3.0-only",
	description = "DNS API interface for the ISP netcup",
	long_description = long_description,
	long_description_content_type = "text/markdown",
	author = "Johannes Bauer",
	author_email = "joe@johannes-bauer.com",
	url = "https://github.com/johndoe31415/dnssync_nc",
	download_url = "https://github.com/johndoe31415/dnssync_nc/archive/v1.0.3rc0.tar.gz",
	keywords = [ "netcup", "dns", "api" ],
	install_requires = [
		"mako",
	],
	entry_points = {
		"console_scripts": [
			"dnssync-cli = dnssync_nc.__main__:main"
		]
	},
	include_package_data = False,
	classifiers = [
		"Development Status :: 5 - Production/Stable",
		"Intended Audience :: Developers",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3 :: Only",
		"Programming Language :: Python :: 3.10",
		"Programming Language :: Python :: 3.11",
		"Programming Language :: Python :: 3.12",
		"Programming Language :: Python :: 3.13",
	],
)
