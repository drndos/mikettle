""""
Read data from Mi Kettle.
"""

import logging
from bluepy.btle import UUID, Peripheral, DefaultDelegate

_KEY1 = bytes([0x90, 0xCA, 0x85, 0xDE])
_KEY2 = bytes([0x92, 0xAB, 0x54, 0xFA])

_HANDLE_READ_FIRMWARE_VERSION = 26
_HANDLE_READ_NAME = 20
_HANDLE_AUTH_INIT = 44
_HANDLE_AUTH = 37
_HANDLE_VERSION = 42
_HANDLE_STATUS = 61

_UUID_SERVICE_KETTLE = "fe95"
_UUID_SERVICE_KETTLE_DATA = "01344736-0000-1000-8000-262837236156"

_SUBSCRIBE_TRUE = bytes([0x01, 0x00])

MI_ACTION = "action"
MI_MODE = "mode"
MI_SET_TEMPERATURE = "set temperature"
MI_CURRENT_TEMPERATURE = "current temperature"
MI_KW_TYPE = "keep warm type"
MI_KW_TIME = "keep warm time"

MI_ACTION_MAP = {
    0: "idle",
    1: "heating",
    2: "cooling",
    3: "keeping warm"
}

MI_MODE_MAP = {
    255: "none",
    1: "boil",
    3: "keep warm"
}

MI_KW_TYPE_MAP = {
    0: "warm up",
    1: "cool down"
}

_LOGGER = logging.getLogger(__name__)


class MiKettle(object):
    """"
    A class to control mi kettle device.
    """

    def __init__(self, mac, product_id, token=None):
        """
        Initialize a Mi Kettle for the given MAC address.
        """

        self._mac = mac
        self._reversed_mac = MiKettle.reverseMac(mac)
        self._p = Peripheral(mac)
        self._p.setDelegate(HandleNotificationDelegate(self))
        self._product_id = product_id
        # Generate token if not supplied
        if token is None:
            token = MiKettle.generateRandomToken()
        self._token = token

    def name(self):
        """Return the name of the device."""
        name = self._p.readCharacteristic(_HANDLE_READ_NAME)

        if not name:
            raise Exception("Could not read NAME using handle %s"
                            " from Mi Kettle %s" % (_HANDLE_READ_NAME, self._mac))
        return ''.join(chr(n) for n in name)

    def firmware_version(self):
        """Return the firmware version."""
        firmware_version = self._p.readCharacteristic(_HANDLE_READ_FIRMWARE_VERSION)

        if not firmware_version:
            raise Exception("Could not read FIRMWARE_VERSION using handle %s"
                            " from Mi Kettle %s" % (_HANDLE_READ_FIRMWARE_VERSION, self._mac))
        return ''.join(chr(n) for n in firmware_version)

    @staticmethod
    def parse_data(data):
        """Parses the byte array returned by the sensor."""

        res = dict()
        res[MI_ACTION] = MI_ACTION_MAP[int(data[0])]
        res[MI_MODE] = MI_MODE_MAP[int(data[1])]
        res[MI_SET_TEMPERATURE] = int(data[4])
        res[MI_CURRENT_TEMPERATURE] = int(data[5])
        res[MI_KW_TYPE] = MI_KW_TYPE_MAP[int(data[6])]
        res[MI_KW_TIME] = MiKettle.bytes_to_int(data[7:8])
        return res

    @staticmethod
    def bytes_to_int(bytes):
        result = 0
        for b in bytes:
            result = result * 256 + int(b)

        return result

    def auth(self):
        auth_service = self._p.getServiceByUUID(_UUID_SERVICE_KETTLE)
        auth_descriptors = auth_service.getDescriptors()

        self._p.writeCharacteristic(_HANDLE_AUTH_INIT, _KEY1, "true")

        auth_descriptors[1].write(_SUBSCRIBE_TRUE, "true")

        self._p.writeCharacteristic(_HANDLE_AUTH,
                                    MiKettle.cipher(MiKettle.mixA(self._reversed_mac, self._product_id), self._token),
                                    "true")

        self._p.waitForNotifications(10.0)

        self._p.writeCharacteristic(_HANDLE_AUTH, MiKettle.cipher(self._token, _KEY2), "true")

        self._p.readCharacteristic(_HANDLE_VERSION)

    def subscribeToData(self):
        controlService = self._p.getServiceByUUID(_UUID_SERVICE_KETTLE_DATA)
        controlDescriptors = controlService.getDescriptors()
        controlDescriptors[3].write(_SUBSCRIBE_TRUE, "true")

    # TODO: Actually generate random token instead of static one
    @staticmethod
    def generateRandomToken() -> bytes:
        return bytes([0x01, 0x5C, 0xCB, 0xA8, 0x80, 0x0A, 0xBD, 0xC1, 0x2E, 0xB8, 0xED, 0x82])

    @staticmethod
    def reverseMac(mac) -> bytes:
        parts = mac.split(":")
        reversedMac = bytearray()
        leng = len(parts)
        for i in range(1, leng + 1):
            reversedMac.extend(bytearray.fromhex(parts[leng - i]))
        return reversedMac

    @staticmethod
    def mixA(mac, productID) -> bytes:
        return bytes([mac[0], mac[2], mac[5], (productID & 0xff), (productID & 0xff), mac[4], mac[5], mac[1]])

    @staticmethod
    def mixB(mac, productID) -> bytes:
        return bytes([mac[0], mac[2], mac[5], ((productID >> 8) & 0xff), mac[4], mac[0], mac[5], (productID & 0xff)])

    @staticmethod
    def _cipherInit(key) -> bytes:
        perm = bytearray()
        for i in range(0, 256):
            perm.extend(bytes([i & 0xff]))
        keyLen = len(key)
        j = 0
        for i in range(0, 256):
            j += perm[i] + key[i % keyLen]
            j = j & 0xff
            perm[i], perm[j] = perm[j], perm[i]
        return perm

    @staticmethod
    def _cipherCrypt(input, perm) -> bytes:
        index1 = 0
        index2 = 0
        output = bytearray()
        for i in range(0, len(input)):
            index1 = index1 + 1
            index1 = index1 & 0xff
            index2 += perm[index1]
            index2 = index2 & 0xff
            perm[index1], perm[index2] = perm[index2], perm[index1]
            idx = perm[index1] + perm[index2]
            idx = idx & 0xff
            outputByte = input[i] ^ perm[idx]
            output.extend(bytes([outputByte & 0xff]))

        return output

    @staticmethod
    def cipher(key, input) -> bytes:
        perm = MiKettle._cipherInit(key)
        return MiKettle._cipherCrypt(input, perm)


class HandleNotificationDelegate(DefaultDelegate):
    def __init__(self, kettle):
        DefaultDelegate.__init__(self)
        self._kettle = kettle

    def handleNotification(self, cHandle, data):
        if cHandle == _HANDLE_AUTH:
            if(MiKettle.cipher(MiKettle.mixB(self._kettle._reversed_mac, self._kettle._product_id),
                               MiKettle.cipher(MiKettle.mixA(self._kettle._reversed_mac,
                                                             self._kettle._product_id),
                                               data)) != self._kettle._token):
                raise Exception("Authentication failed.")
        elif cHandle == _HANDLE_STATUS:
            _LOGGER.debug("Status update:")
            print(MiKettle.parse_data(data))
        else:
            print("Unknown notification from handle:")
            print(cHandle)
            print("Data:")
            print(data.hex())
