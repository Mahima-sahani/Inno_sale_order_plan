from odoo import fields, models, api
import serial.tools.list_ports
import subprocess
from odoo.modules import get_resource_path


class BarcodeScanner(models.Model):
    _name = 'barcode.scanner'

    name = fields.Char(string='Name')
    device_address = fields.Char(string='Device Address')
    is_bluetooth = fields.Boolean(string='Yes')


    def check_bluetooth(self):
        path = get_resource_path('inno_iot', 'models', 'serial_port.py')
        passw = subprocess.Popen(['echo', '1234'], stdout=subprocess.PIPE)
        cmd2 = subprocess.Popen(['sudo', '-S', 'python3', path,], stdin=passw.stdout, stdout=subprocess.PIPE)
        port_no = cmd2.stdout.read().decode()
        print(port_no)
        # endpoint = device[0][(0, 0)][0]
        # data = endpoint.read(endpoint.wMaxPacketSize)
