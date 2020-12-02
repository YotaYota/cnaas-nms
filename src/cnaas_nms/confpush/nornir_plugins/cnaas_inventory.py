import os
import ipaddress

from nornir.core.inventory import (
    Inventory,
    Group,
    Groups,
    Host,
    Hosts,
    Defaults,
    ConnectionOptions,
    ParentGroups,
)

from cnaas_nms.db.device import Device, DeviceType, DeviceState
from cnaas_nms.db.settings import get_groups
import cnaas_nms.db.session


class CnaasInventory:
    @staticmethod
    def _get_credentials(devicestate):
        if devicestate == 'UNKNOWN':
            return None, None
        elif devicestate in ['UNMANAGED', 'MANAGED_NOIF']:
            env_var = 'MANAGED'
        elif devicestate == 'PRE_CONFIGURED':
            env_var = 'DHCP_BOOT'
        else:
            env_var = devicestate

        try:
            username = os.environ['USERNAME_' + env_var]
            password = os.environ['PASSWORD_' + env_var]
        except Exception:
            raise ValueError('Could not find credentials for state ' + devicestate)
        return username, password

    @staticmethod
    def _get_management_ip(management_ip, dhcp_ip):
        if issubclass(management_ip.__class__, ipaddress.IPv4Address):
            return str(management_ip)
        elif issubclass(dhcp_ip.__class__, ipaddress.IPv4Address):
            return str(dhcp_ip)
        else:
            return None

    def load(self) -> Inventory:
        hosts = Hosts()
        with cnaas_nms.db.session.sqla_session() as session:
            instance: Device
            for instance in session.query(Device):
                hostname = self._get_management_ip(instance.management_ip,
                                                   instance.dhcp_ip)
                port = None
                if instance.port and isinstance(instance.port, int):
                    port = instance.port
                host_groups = [
                    Group(name='T_' + instance.device_type.name),
                    Group(name='S_' + instance.state.name)
                ]
                for member_group in get_groups(instance.hostname):
                    host_groups.append(Group(name=member_group))
                hosts[instance.hostname] = Host(
                    name=instance.hostname,
                    hostname=hostname,
                    platform=instance.platform,
                    groups=ParentGroups(host_groups),
                    port=port,
                    data={
                        'synchronized': instance.synchronized,
                        'managed': (True if instance.state == DeviceState.MANAGED else False)
                    }
                )
        groups = Groups()
        for device_type in list(DeviceType.__members__):
            group_name = 'T_'+device_type
            groups[group_name] = Group(name=group_name)
        for device_state in list(DeviceState.__members__):
            username, password = self._get_credentials(device_state)
            group_name = 'S_'+device_state
            groups[group_name] = Group(name=group_name, username=username, password=password)
        for group_name in get_groups():
            groups[group_name] = Group(name=group_name)

        defaults = Defaults(
            connection_options={'netmiko': ConnectionOptions(extras={'fast_cli': False})}
        )

        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
