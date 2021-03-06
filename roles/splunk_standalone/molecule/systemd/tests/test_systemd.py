#!/usr/bin/env python
#
# These tests specifically exercise the following:
# - Splunk version 7.3.3 through rpm installation
# - Systemd-enabled, Splunk started via `enable bootstrap` command
# - Older schema of custom configs (dict)

from __future__ import absolute_import
import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

SPLUNK_HOME = "/opt/splunk"
SPLUNK_EXEC = "{}/bin/splunk".format(SPLUNK_HOME)
SPLUNK_USER = SPLUNK_GROUP = "splunk"


def test_splunk_user_group(host):
    user = host.user(SPLUNK_USER)
    assert user.name == SPLUNK_USER
    assert user.group == SPLUNK_GROUP

def test_splunk_installation(host):
    d = host.file(SPLUNK_HOME)
    assert d.is_directory
    assert d.user == SPLUNK_USER
    assert d.group == SPLUNK_GROUP
    f = host.file(SPLUNK_EXEC)
    assert f.is_file
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_splunk_running(host):
    output = host.run("{} status".format(SPLUNK_EXEC))
    assert "running" in output.stdout

def test_user_seed(host):
    f = host.file("{}/etc/system/local/user-seed.conf".format(SPLUNK_HOME))
    assert not f.exists

def test_outputs_conf(host):
    f = host.file('/opt/splunk/etc/system/local/outputs.conf')
    assert not f.exists

def test_ui_login(host):
    f = host.file("{}/etc/.ui_login".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_splunk_version(host):
    f = host.file("{}/etc/splunk.version".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("VERSION=7.3.3")

def test_splunk_pid(host):
    f = host.file("{}/var/run/splunk/splunkd.pid".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_mongod_lock(host):
    f = host.file("{}/var/lib/splunk/kvstore/mongo/mongod.lock".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_bin_splunk(host):
    f = host.file("{}".format(SPLUNK_EXEC))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_splunk_hec_inputs(host):
    f = host.file("{}/etc/apps/splunk_httpinput/local/inputs.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("[http]")
    assert f.contains("disabled = 0")
    assert f.contains("[http://splunk_hec_token]")
    assert f.contains("token = abcd1234")

def test_inputs_conf(host):
    f = host.file("{}/etc/system/local/inputs.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("[splunktcp://9997]")
    assert f.contains("disabled = 0")

def test_splunk_ports(host):
    output = host.run("netstat -tuln")
    assert "0.0.0.0:8000" in output.stdout
    assert "0.0.0.0:8089" in output.stdout
    assert "0.0.0.0:8088" in output.stdout
    assert "0.0.0.0:8191" in output.stdout
    assert "0.0.0.0:9997" in output.stdout
    assert "127.0.0.1:8065" in output.stdout

def test_splunk_hec(host):
    output = host.run('curl -k https://localhost:8088/services/collector/event \
        -H "Authorization: Splunk abcd1234" -d \'{"event": "helloworld"}\'')
    assert "Success" in output.stdout

def test_splunkd(host):
    output = host.run("curl -k https://localhost:8089/services/server/info \
        -u admin:helloworld")
    assert "Splunk" in output.stdout

def test_custom_user_prefs(host):
    f = host.file("{}/etc/users/admin/user-prefs/local/user-prefs.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("[general]")
    assert f.contains("default_namespace = appboilerplate")
    assert f.contains("search_syntax_highlighting = dark")
    assert f.contains("search_assistant")
    assert f.contains("[serverClass:secrets:app:test]")

def test_service(host):
    s = host.service('Splunkd')
    assert s.is_running
    assert s.is_enabled

def test_splunkd_systemd_file(host):
    f = host.file('/etc/systemd/system/Splunkd.service')
    assert f.is_file
    assert f.user == "root"
    assert f.group == "root"
    assert f.contains('ExecStartPost=/bin/bash -c "chown -R .* /sys/fs/cgroup/cpu/.*"$')
    assert f.contains('^ExecStartPost=/bin/bash -c "chown -R .* /sys/fs/cgroup/memory/.*"$')
