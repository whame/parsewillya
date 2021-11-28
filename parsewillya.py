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
    # Self checkout section.
    SELF_CHECKOUT_RE = re.compile(r"^=+\s*\w+\s\w+\s*=+")
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
        "kort datum",
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
                bulk_match = self.ADJUSTMENT_RE.fullmatch(next_line)
                if bulk_match:
                    info = self.trim_spaces(bulk_match.group(1))
                    price = self.str_to_decimal(bulk_match.group(2))
                    item = self.Item(self.trim_spaces(line), price)
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
        pdf = pdftotext.PDF(f)

    txt_receipt = "".join(pdf)

    if args.dump:
        print(txt_receipt)

        sys.exit(0)

    # Parse receipt.
    receipt = Receipt(txt_receipt)
    for item in receipt.get_items():
        print(item)

    if args.total:
        print(f"\nTotal\t{receipt.get_total()}")
