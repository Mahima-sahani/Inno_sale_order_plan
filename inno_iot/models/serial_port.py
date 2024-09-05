import usb.core
import usb.util


devices = usb.core.find(find_all=True)
for device in devices:
    try:
        if usb.util.get_string(device, device.iProduct) == 'HIDKeyBoard' and usb.util.get_string(device, device.iManufacturer) == 'WCM':
            endpoint = device[0][(0, 0)][0]
            # print(device.port_number, end="")
            print(endpoint.read(endpoint.wMaxPacketSize))
    except Exception as ex:
        print(ex)
