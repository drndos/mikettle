""""
Read data from Mi Kettle.
"""

import logging
from bluepy.btle import UUID, Peripheral, DefaultDelegate
from datetime import datetime, timedelta
from threading import Lock

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

    def __init__(self, mac, product_id, cache_timeout=600, retries=3, iface=None, token=None):
        """
        Initialize a Mi Kettle for the given MAC address.
        """
        _LOGGER.debug('Init Mikettle with mac %s and pid %s', mac, product_id)

        self._mac = mac
        self._reversed_mac = MiKettle.reverseMac(mac)

        self._cache = None
        self._cache_timeout = timedelta(seconds=cache_timeout)
        self._last_read = None
        self.retries = retries
        self.ble_timeout = 10
        self.lock = Lock()

        self._product_id = product_id
        self._iface = iface
        # Generate token if not supplied
        if token is None:
            token = MiKettle.generateRandomToken()
        self._token = token

    def connect(self):
        self._p = Peripheral(deviceAddr=self._mac, iface=self._iface)
        self._p.setDelegate(self)

    def name(self):
        """Return the name of the device."""
        self.connect()
        self.auth()
        name = self._p.readCharacteristic(_HANDLE_READ_NAME)

        if not name:
            raise Exception("Could not read NAME using handle %s"
                            " from Mi Kettle %s" % (_HANDLE_READ_NAME, self._mac))
        return ''.join(chr(n) for n in name)

    def firmware_version(self):
        """Return the firmware version."""
        self.connect()
        self.auth()
        firmware_version = self._p.readCharacteristic(_HANDLE_READ_FIRMWARE_VERSION)

        if not firmware_version:
            raise Exception("Could not read FIRMWARE_VERSION using handle %s"
                            " from Mi Kettle %s" % (_HANDLE_READ_FIRMWARE_VERSION, self._mac))
        return ''.join(chr(n) for n in firmware_version)

    def parameter_value(self, parameter, read_cached=True):
        """Return a value of one of the monitored paramaters.
        This method will try to retrieve the data from cache and only
        request it by bluetooth if no cached value is stored or the cache is
        expired.
        This behaviour can be overwritten by the "read_cached" parameter.
        """
        # Use the lock to make sure the cache isn't updated multiple times
        with self.lock:
            if (read_cached is False) or \
                    (self._last_read is None) or \
                    (datetime.now() - self._cache_timeout > self._last_read):
                self.fill_cache()
            else:
                _LOGGER.debug("Using cache (%s < %s)",
                              datetime.now() - self._last_read,
                              self._cache_timeout)

        if self.cache_available():
            return self._cache[parameter]
        else:
            raise Exception("Could not read data from MiKettle %s" % self._mac)

    def fill_cache(self):
        """Fill the cache with new data from the sensor."""
        _LOGGER.debug('Filling cache with new sensor data.')
        try:
            _LOGGER.debug('Connect')
            self.connect()
            _LOGGER.debug('Auth')
            self.auth()
            _LOGGER.debug('Subscribe')
            self.subscribeToData()
            _LOGGER.debug('Wait for data')
            self._p.waitForNotifications(self.ble_timeout)
            # If a sensor doesn't work, wait 5 minutes before retrying
        except Exception as error:
            _LOGGER.debug('Error %s', error)
            self._last_read = datetime.now() - self._cache_timeout + \
                timedelta(seconds=300)
            return

    def clear_cache(self):
        """Manually force the cache to be cleared."""
        self._cache = None
        self._last_read = None

    def cache_available(self):
        """Check if there is data in the cache."""
        return self._cache is not None

    def _parse_data(self, data):
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

    def handleNotification(self, cHandle, data):
        if cHandle == _HANDLE_AUTH:
            if(MiKettle.cipher(MiKettle.mixB(self._reversed_mac, self._product_id),
                               MiKettle.cipher(MiKettle.mixA(self._reversed_mac,
                                                             self._product_id),
                                               data)) != self._token):
                raise Exception("Authentication failed.")
        elif cHandle == _HANDLE_STATUS:
            _LOGGER.debug("Status update:")
            if data is None:
              return

            _LOGGER.debug("Parse data: %s", data)
            self._cache = self._parse_data(data)
            _LOGGER.debug("data parsed %s", self._cache)

            if self.cache_available():
                self._last_read = datetime.now()
            else:
                # If a sensor doesn't work, wait 5 minutes before retrying
                self._last_read = datetime.now() - self._cache_timeout + \
                    timedelta(seconds=300)
        else:
            _LOGGER.error("Unknown notification from handle: %s with Data: %s", cHandle, data.hex())


