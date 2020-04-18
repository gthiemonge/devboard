devboard
========

A tool to synchronize multiple development source items into a unified output.

Supported source services:
- bugzilla
- gerrit

Supported output services:
- trello

Usage
-----

Create configuration files (auth.yml and config.yml) in ~/.config/devboard/,
sample files are provided in auth.sample.yml and config.sample.yml.

Launch devboard:

```
$ devboard
```

Options
-------

* -i <interval>: Refresh source items every <interval> seconds.
* -c <config_file>: Path to a customized configuration file.
* -a <auth_file>: Path to a customized authentication file.
