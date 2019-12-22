from homeassistant.components.switch import SwitchDevice
from meross_iot.cloud.devices.power_plugs import GenericPlug

from .common import DOMAIN, ENROLLED_DEVICES, MANAGER, calculate_switch_id


class SwitchEntityWrapper(SwitchDevice):
    """Wrapper class to adapt the Meross switches into the Homeassistant platform"""
    _device = None
    _channel_id = None
    _root_id = None
    _id = None
    _device_name = None

    def __init__(self, device: GenericPlug, channel: int):
        self._device = device
        self._channel_id = channel
        self._root_id = device.uuid
        self._id = calculate_switch_id(self._device.uuid, channel)
        if channel > 0:
            # This is a sub-channel within the multi-way adapter
            channelData = self._device.get_channels()[channel]
            self._device_name = channelData['devName']
        else:
            # This is the root device
            self._device_name = self._device.name

        device.register_event_callback(self.handler)

    def handler(self, evt):
        self.async_schedule_update_ha_state(False)

    @property
    def unique_id(self) -> str:
        # Since Meross plugs may have more than 1 switch, we need to provide a composed ID
        # made of uuid and channel
        return self._id

    @property
    def name(self) -> str:
        return self._device_name

    @property
    def device_info(self):
        return {
            'name': self._device_name,
            'manufacturer': 'Meross',
            'model': self._device.type + " " + self._device.hwversion,
            'sw_version': self._device.fwversion
        }

    @property
    def available(self) -> bool:
        # A device is available if it's online
        return self._device.online

    # TODO
    #@property
    #def device_state_attributes(self):
    #    """Return the state attributes of the device."""
    #    return self._emeter_params


    @property
    def today_energy_kwh(self):
        """Return the today total energy usage in kWh."""
        return None

    @property
    def should_poll(self) -> bool:
        # In general, we don't want HomeAssistant to poll this device.
        # Instead, we will notify HA when an event is received.
        return False

    @property
    def is_on(self) -> bool:
        # Note that the following method is not fetching info from the device over the network.
        # Instead, it is reading the device status from the state-dictionary that is handled by the library.
        return self._device.get_channel_status(self._channel_id)

    def turn_off(self, **kwargs) -> None:
        self._device.turn_off_channel(self._channel_id)

    def turn_on(self, **kwargs) -> None:
        self._device.turn_on_channel(self._channel_id)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    switch_devices = []
    device = hass.data[DOMAIN][MANAGER].get_device_by_uuid(discovery_info)

    for k, c in enumerate(device.get_channels()):
        w = SwitchEntityWrapper(device, k)
        switch_devices.append(w)

    async_add_entities(switch_devices)
    hass.data[DOMAIN][ENROLLED_DEVICES].add(device.uuid)
