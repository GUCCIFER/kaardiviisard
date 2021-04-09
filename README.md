# Kaardiviisard
This python code will extract the contents of standalone ISIC card, Tartu bus card and Tallinn Public Transportation card with ACR1252 NFC Reader device

# Hardware
ACR1252 NFC Reader

You may need drivers for the ACR1252: : https://www.acs.com.hk/en/products/342/acr1252u-usb-nfcreader-iii-nfc-forum-certified-reader/

You may have to put the tag directly on the reader, on some devices the waitforcard() function does not work properly

# pip requirements (pip install):
smartcard

pyscard


