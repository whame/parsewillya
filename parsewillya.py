#!/usr/bin/env python3

"""
Parse receipts from the grocery store Willys.

Copyright (c) 2020 Waqar Hameed

SPDX-License-Identifier: MIT
"""

import argparse
import decimal
import re
import sys

import pdftotext


class Receipt:
    """Class representing a receipt.
    """
    class Item:
        """Class representing an item in a receipt.
        """
        def __init__(self, name, price, info="", adjustment_description="",
                     adjustment_amount=0):
            """Create a receipt item.

            :param name: Name of item.
            :param price: Price of item.
            :param info: Extra information about the item.
            :param adjustment_description: Adjustment description of item.
            :param adjustment_amount: Adjustment amount of item.
            """
            self.name = name
            self.price = decimal.Decimal(price)

            self.info = info
            self.adjustment_description = adjustment_description
            self.adjustment_amount = adjustment_amount

            self.final_price = self.price + self.adjustment_amount

        def add_adjustment(self, description, amount):
            """"Add (price) adjustment (e.g. discounts).

            :param description: Description of the adjustment.
            :param amount: Price adjustment amount.
            :raises ValueError: If amount is zero.
            """
            if amount == 0:
                raise ValueError("Discount amount must be non-zero")

            self.adjustment_description = description
            self.adjustment_amount = decimal.Decimal(amount)

            self.final_price += self.adjustment_amount

        def add_information(self, info):
            """"Add extra information.

            :param info: Information text.
            """
            if not self.info:
                self.info = info
            else:
                self.info += f" {info}"

        def get_name(self):
            """"Get name of item.

            :returns: Name of item.
            """
            return self.name

        def get_price(self):
            """"Get price of item.

            :returns: Price of item.
            """
            return self.price

        def get_final_price(self):
            """"Get final price of item (after price adjustments).

            :returns: Final price of item.
            """
            return self.final_price

        def __repr__(self):
            return f"{{{self.name}, {self.info}, {self.price}, " \
                f"{self.adjustment_description}, {self.adjustment_amount}, " \
                f"{self.final_price}}}"

        def __str__(self):
            string = f"{self.name}"
            if self.info or self.adjustment_description:
                string += " ("
                if self.info:
                    string += f"{self.info}"
                    if self.adjustment_description:
                        string += f", {self.adjustment_description}"
                else:
                    string += f"{self.adjustment_description}"

                string += ")"

            string += f"\t{self.final_price}"

            return string

    # For seperators (used at the start and end of item list).
    SEPERATOR_RE = re.compile(r"^-{31}-+")
    # Self checkout section. Sometimes the 'ä' in "självskanning" gets printed
    # as '?' or '�'. This seems to happen if you register a buy on the last day
    # of the month...
    SELF_CHECKOUT_RE = re.compile(
        r"^.*\s*[sS](tar|lu)t\s[sS]j[ä�?]lvscanning.*\s*")
    # For total item line.
    TOTAL_ITEMS_RE = re.compile(r"^\s*Totalt\s*(\d+)\s*var(?:or|a)")
    # For total cost line.
    TOTAL_RE = re.compile(r"^\s*Totalt\s*(\d+,\d+)\s*SEK")
    # For entry in item list.
    ITEM_RE = re.compile(r"^(\S.+)\s+(-?\d+,\d+)")
    # For additional adjustments in price due to discounts, pawn or similiar in
    # the item list.
    ADJUSTMENT_RE = re.compile(r"^\s+(.+)\s+(-?\d+,\d+)")
    # For indentation in item list (extra information).
    INDENT_RE = re.compile(r"^\s+.+")

    # Sometimes extra information lines are not indented... These are the
    # exceptional ones encountered so far.
    EXTRA_INFO_EXCEPTIONS = [
        "extrapris",
        "halva priset",
        "kort datum",
        "lågpris",
        "svinnsmart",
    ]

    @staticmethod
    def str_to_decimal(string):
        """Convert string to decimal.

        :returns: Converted decimal value from string.
        """
        return decimal.Decimal(string.replace(",", "."))

    @staticmethod
    def trim_spaces(string):
        """Trim and replace two or more spaces with just one.

        :returns: Trimmed string.
        """
        return re.sub(r"\s+", " ", string.strip())

    def __init__(self, text):
        """Create and parse a receipt.

        :param text: Text representation of a receipt.
        """
        self.raw_text = text.splitlines()

        # Search for start of item list.
        raw_text_it = iter(self.raw_text)
        for line in raw_text_it:
            if self.SEPERATOR_RE.fullmatch(line):
                break

        # Start of item list.
        self.items = []
        for line in raw_text_it:
            if self.SEPERATOR_RE.fullmatch(line):
                # End of item list.
                break

            if self.SELF_CHECKOUT_RE.fullmatch(line):
                # Self checkout section.
                continue

            if self.INDENT_RE.fullmatch(line):
                adjustment_match = self.ADJUSTMENT_RE.fullmatch(line)
                if adjustment_match:
                    # Discount item.
                    adjustment_name = self.trim_spaces(
                        adjustment_match.group(1))
                    adjustment_amount = self.str_to_decimal(
                        adjustment_match.group(2))
                    self.items[-1].add_adjustment(adjustment_name,
                                                  adjustment_amount)
                else:
                    # Just information.
                    self.items[-1].add_information(self.trim_spaces(line))

                continue

            item_match = self.ITEM_RE.fullmatch(line)
            if not item_match:
                # Sometimes extra information lines are not indented... Check
                # if line contains any of the exceptions.
                if line.lower() in self.EXTRA_INFO_EXCEPTIONS:
                    self.items[-1].add_information(self.trim_spaces(line))

                    continue

                # Stuff in bulk (e.g. candy) have an indented price on the next
                # line instead (similiar to additional adjustments). Let's
                # check if this is the case here.
                next_line = next(raw_text_it)

                # However, they may contain extra information before the
                # adjustment...
                info = ""
                if not self.ADJUSTMENT_RE.fullmatch(next_line) and \
                   self.INDENT_RE.fullmatch(next_line):
                    info = self.trim_spaces(next_line)
                    next_line = next(raw_text_it)

                bulk_match = self.ADJUSTMENT_RE.fullmatch(next_line)
                if bulk_match:
                    price = self.str_to_decimal(bulk_match.group(2))
                    item = self.Item(self.trim_spaces(line), price)
                    if info:
                        # Add extra information from previous line first.
                        item.add_information(info)

                    info = self.trim_spaces(bulk_match.group(1))
                    item.add_information(info)

                    self.items.append(item)

                    continue

                raise ValueError(f"Could not parse item: \"{line}\"")

            name = self.trim_spaces(item_match.group(1))
            price = self.str_to_decimal(item_match.group(2))

            self.items.append(self.Item(name, price))

        # Start of total section.
        try:
            total_items_line = next(raw_text_it)
            total_line = next(raw_text_it)
        except StopIteration:
            raise ValueError("Input receipt has invalid format")

        total_items_match = self.TOTAL_ITEMS_RE.fullmatch(total_items_line)
        if not total_items_match:
            raise ValueError("Could not parse total items line: "
                             f"\"{total_items_line}\"")

        self.total_items = int(total_items_match.group(1))

        total_match = self.TOTAL_RE.fullmatch(total_line)
        if not total_match:
            raise ValueError(f"Could not parse total line: \"{total_line}\"")

        self.total = self.str_to_decimal(total_match.group(1))

        # Sanity check that the parsed total amount equals the total amount of
        # the items.
        assert self.total == sum(
            [item.get_final_price() for item in self.items])

    def get_items(self):
        """Get items in receipt.
        """
        return self.items

    def get_total(self):
        """Get total in receipt.
        """
        return self.total


def _non_empty_str(string):
    if not string:
        raise argparse.ArgumentTypeError("string is empty")

    return string


if __name__ == "__main__":
    __version__ = "0.1"
    __url__ = "https://www.github.com/whame/parsewillya"

    # Argument parsing.
    arg_parser = argparse.ArgumentParser(
        description="Parse the item list in a receipt from the grocery store "
        "Willys. Output contains the item's name and price (seperated by a "
        "tab character '\\t')", epilog=f"Report bugs to {__url__}.")
    arg_parser.add_argument("receipt_pdf", metavar="RECEIPT",
                            type=_non_empty_str,
                            help="Input PDF receipt (obtained from Willys "
                            "website).")
    arg_parser.add_argument("--total", "-t", action="store_true",
                            help="Print the total.")
    arg_parser.add_argument("--dump", "-d", action="store_true",
                            help="Dump receipt in text form and exit.")
    arg_parser.add_argument("--version", "-v", action="version",
                            version=f"%(prog)s {__version__}")

    args = arg_parser.parse_args()

    # Parse PDF.
    with open(args.receipt_pdf, "rb") as f:
        pdf = pdftotext.PDF(f, physical=True)

    # The PDF has this custom encdoing.
    encoding = {
        0x03: ' ', 0x04: '!', 0x08: '%', 0x0a: '\n', 0x0f: ",", 0x10: '-',
        0x11: '.', 0x12: '/', 0x1d: ':', 0x13: '0', 0x14: '1', 0x15: '2',
        0x16: '3', 0x17: '4', 0x18: '5', 0x19: '6', 0x1a: '7', 0x1b: '8',
        0x1c: '9', 0x20: '*', 0x21: '>', 0x24: 'A', 0x25: 'B', 0x26: 'C',
        0x27: 'D', 0x28: 'E', 0x29: 'F', 0x2a: 'G', 0x2b: 'H', 0x2c: 'I',
        0x2d: 'J', 0x2e: "K", 0x2f: 'L', 0x30: 'M', 0x31: 'N', 0x32: 'O',
        0x33: 'P', 0x34: 'Q', 0x35: 'R', 0x36: 'S', 0x37: 'T', 0x38: 'U',
        0x39: 'V', 0x3a: 'W', 0x3b: 'X', 0x3c: 'Y', 0x3d: 'Z', 0x44: 'a',
        0x45: 'b', 0x46: 'c', 0x47: 'd', 0x48: 'e', 0x49: 'f', 0x4a: 'g',
        0x4b: 'h', 0x4c: 'i', 0x4d: 'j', 0x4e: 'k', 0x4f: 'l', 0x50: 'm',
        0x51: 'n', 0x52: 'o', 0x53: 'p', 0x54: 'q', 0x55: 'r', 0x56: 's',
        0x57: 't', 0x58: 'u', 0x59: 'v', 0x5a: 'w', 0x5b: 'x', 0x5c: 'y',
        0x5d: 'z',
        0xc2: '', # Prefix byte for chars below.
        0xa6: 'ä', 0xa7: 'å', 0xb8: "ö", 0x86: "Ä", 0x87: "Å", 0x8b: "É",
        0x98: "Ö",
    }

    txt_receipt = "".join(pdf).translate(encoding)

    if args.dump:
        print(txt_receipt)

        sys.exit(0)

    # Parse receipt.
    receipt = Receipt(txt_receipt)
    for item in receipt.get_items():
        print(item)

    if args.total:
        print(f"\nTotal\t{receipt.get_total()}")
