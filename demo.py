#!/usr/bin/env python3
"""Demo file showing how to use the mikettle library."""

import argparse
import re

import sys

from mikettle.mikettle import MiKettle


def valid_mikettle_mac(mac, pat=re.compile(r"[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}")):
    """Check for valid mac adresses."""
    if not pat.match(mac.upper()):
        raise argparse.ArgumentTypeError('The MAC address "{}" seems to be in the wrong format'.format(mac))
    return mac


def valid_product_id(product_id):
    try:
        product_id = int(product_id)
    except Exception:
        raise argparse.ArgumentTypeError('The Product Id "{}" seems to be in the wrong format'.format(product_id))
    return product_id


def connect(args):
    """Connect to Mi Kettle."""
    kettle = MiKettle(args.mac, args.product_id)
    print("Authenticating")
    kettle.auth()
    print("Getting data from mi Kettle")
    print("FW: {}".format(kettle.firmware_version()))
    print("Name: {}".format(kettle.name()))
    print("Subscribing to data and receiving it once")
    kettle.subscribeToData()
    kettle._p.waitForNotifications(10.0)


def main():
    """Main function.

    Mostly parsing the command line arguments.
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='sub-command help', )

    parser_poll = subparsers.add_parser('connect', help='connect to mi kettle and receive data')
    parser_poll.add_argument('mac', type=valid_mikettle_mac)
    parser_poll.add_argument('product_id', type=valid_product_id)
    parser_poll.set_defaults(func=connect)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == '__main__':
    main()
