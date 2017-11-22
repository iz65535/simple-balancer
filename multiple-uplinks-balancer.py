# encoding: utf-8

import operator
import time
import subprocess
import logging
import sys
import os

from threading import Thread


class Channel(Thread):
    def __init__(self, defaultRoute, name, fileName):
        Thread.__init__(self)
        self.defaultRoute = defaultRoute
        self.name = name
        self.fileName = fileName
        self.available = False

        self._enabled = None
        self.enabled = False

    def run(self):
        while True:
            start = time.time()
            ping = subprocess.Popen(
                ["ping", "-c", '5', self.defaultRoute, '-W', '10'],
                stdout=subprocess.PIPE,
                preexec_fn=os.setpgrp
            )
            ping.communicate()

            if time.time() - start < 5:
                time.sleep(5)

            self.available = ping.returncode == 0
            if self.available:
                continue

            logging.getLogger().warning(
                "channel {channel}: ping result: {result}".format(channel=self, result=ping.returncode)
            )

    def __str__(self):
        return "{ip} {name}".format(ip=self.defaultRoute, name=self.name)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        if self.enabled == value:
            logging.getLogger().info(
                "not changing channel {channel} to {enabled} since already".format(channel=self, enabled=value)
            )
            return
        logging.getLogger().info(
            "changing channel {channel} to {enabled}".format(channel=self, enabled=value)
        )

        self._enabled = value

        if not value:
            return

        commands = [
            ['unlink', '/etc/sysconfig/iptables'],
            ['ln', '-s', self.fileName, '/etc/sysconfig/iptables'],
            ['ip', 'r', 'del', 'default'],
            ['ip', 'r', 'add', 'default', 'via', self.defaultRoute],
            ['systemctl', 'restart', 'iptables.service'],
        ]

        for i in commands:
            result = subprocess.call(i)
            command = " ".join(i)
            logging.getLogger().info("Command [%s]: return code %i" % (command, result))


class ChannelContainer:
    def __init__(self, channels):
        self.channels = channels
        [i.start() for i in channels]
        self.active_channel = None

    def start_analyzer(self):
        logging.getLogger().info("Analyzer Started")
        while True:
            self._analyzer()
            time.sleep(5)

    def _analyzer(self):
        if self.active_channel and self.active_channel.available:
            return

        self.change_channel()

    def change_channel(self):
        self.active_channel = None
        for i in self.channels:
            i.enabled = False

        active_channel = self.get_first_active_channel()

        if not active_channel:
            logging.getLogger().info("No channels Available")
            return

        self.active_channel = active_channel
        self.active_channel.enabled = True
        logging.getLogger().info(
            "Active channel was set to {active_channel}".format(active_channel=active_channel)
        )

    def get_first_active_channel(self):
        possible = [i for i in self.channels if i.available]
        if len(possible):
            return possible[0]


if __name__ == '__main__':
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

    container = ChannelContainer([
        Channel('1.1.1.1', 'channel1', '/etc/sysconfig/iptables-channel-1'),
        Channel('2.2.2.2', 'channel2', '/etc/sysconfig/iptables-channel-2'),
    ])
    container.start_analyzer()
