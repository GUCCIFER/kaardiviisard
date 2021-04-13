#!/usr/bin/env python3

from smartcard.CardType import AnyCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString, toBytes, toASCIIString

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
        if (data[i] < 33 or data[i] > 126):
            data[i] = 46

    return toASCIIString(data)


'''
common default A key values
NDEF Keys: A0A1A2A3A4A5, D3F7D3F7D3F7
Factory Keys: FFFFFFFFFFFF
ISIC Keys: 8c5116ae70b6, 57da46f810ea, e9b0328046cb, 687a02ece08c
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
            isicUser = getBlockInfo(32).split('.')[0] + " " + getBlockInfo(33).split('.')[0] + " " + getBlockInfo(34).split('.')[0]
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
        print("Card UID" + toHexString(send([0xFF, 0xCA, 0x00, 0x00, 0x00])))
        print("PAN: " + tartuCardPAN)

def main():
    if toHexString(current_card_ATR) == Classic1K_ATR:
        readClassic1k()
        getDataFields(toHexString(current_card_ATR))
    elif toHexString(current_card_ATR) == UltralightC_ATR:
        readUltralightC()
        getDataFields(toHexString(current_card_ATR))
    else:
        print("[!] Card type not supported")


if __name__ == '__main__':
    main()

