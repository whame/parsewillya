ParseWillya
===========

ParseWillya parses a digital receipt from the Swedish grocery store
[Willys](https://www.willys.se). It parses each item in the receipt and its
total price. It even handles price adjustments as discounts, pawn or similar
items in the receipt!

## Example

A PDF receipt can be downloaded from Willys website. You can give it as input
directly to ParseWillya and print it as raw text:

```
> ./parsewillya.py receipt.pdf --dump

 Willys Hemma Malmö
               Willy:s Hemma
------------------------------------------
GRILLOST               2st*15,50       31,00
  2 * Rabatt:GRILLOST                  -9,20
VISPGRÄDDE 36%                         21,90
RASKER 1,1KG           2st*27,90       55,80
  2 * Rabatt:BRÖD                     -24,00
NATURGODIS LV
             0,365kg*119,00kr/kg       43,44
------------------------------------------
  Totalt 6 varor
 Totalt     118,94 SEK
==========================================
Låga priser på allt. Alltid.
Willys Plus registrerat
Willys Plus-nummer: 1234567891234567
==========================================
Mottaget Kontokort                    118,94
Debit MasterCard     ************1234
KÖP                  118,94 SEK
Butik: 8606386       K/1 6 000 SWE 607752
Ref:000052833185     Term:2 / 00005283
TVR:0000048001       AID:A0000000041010
2021-02-02 17:41     TSI:E800
KONTAKTLÖS
 Moms%       Moms          Netto      Brutto
12,00       12,74         106,20      118,94
------------------------------------------
     SPARA KVITTOT
    Välkommen åter
             Du betjänades av
            Självcheckout Kassör
Kassa: 2/137              2021-02-02   17:42
```

The items in the receipt can be parsed by:

```
> ./parsewillya.py receipt.pdf

GRILLOST 2st*15,50 (2 * Rabatt:GRILLOST)	 21.80
VISPGRÄDDE 36%	 21.90
RASKER 1,1KG 2st*27,90 (2 * Rabatt:BRÖD)	 31.80
NATURGODIS LV (0,365kg*119,00kr/kg)	 43.44
```

As one can see, each item will be printed on a new line, with additional
information inside parentheses, and finally the total price separated by a tab.

You can also print the total with the option `--total`. Please see the help text
for more information (`--help`).

## Dependencies

To parse a PDF into raw text, ParseWillya needs
[pdftotext](https://pypi.org/project/pdftotext/). Install that with:

```
python3 -m pip install pdftotext
```
