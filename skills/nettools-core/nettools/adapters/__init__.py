"""Adapter interfaces and stub implementations for NETTOOLS shared support code."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "AdapterContext": ("nettools.adapters.base", "AdapterContext"),
    "AdapterEvent": ("nettools.adapters.base", "AdapterEvent"),
    "AuthAdapter": ("nettools.adapters.auth", "AuthAdapter"),
    "AuthFailureCategory": ("nettools.adapters.base", "AuthFailureCategory"),
    "BaseAdapter": ("nettools.adapters.base", "BaseAdapter"),
    "DhcpAdapter": ("nettools.adapters.dhcp", "DhcpAdapter"),
    "DnsAdapter": ("nettools.adapters.dns", "DnsAdapter"),
    "GatewayAdapter": ("nettools.adapters.gateway", "GatewayAdapter"),
    "InterfaceCounters": ("nettools.adapters.base", "InterfaceCounters"),
    "InventoryConfigAdapter": ("nettools.adapters.inventory", "InventoryConfigAdapter"),
    "NeighborDiscoveryAdapter": ("nettools.adapters.neighbor", "NeighborDiscoveryAdapter"),
    "PolicyMapping": ("nettools.adapters.base", "PolicyMapping"),
    "ProbeAdapter": ("nettools.adapters.probe", "ProbeAdapter"),
    "ProbeRequest": ("nettools.adapters.base", "ProbeRequest"),
    "ProbeTarget": ("nettools.adapters.base", "ProbeTarget"),
    "RelayPathMetadata": ("nettools.adapters.base", "RelayPathMetadata"),
    "StubAuthAdapter": ("nettools.adapters.stubs", "StubAuthAdapter"),
    "StubDhcpAdapter": ("nettools.adapters.stubs", "StubDhcpAdapter"),
    "StubDnsAdapter": ("nettools.adapters.stubs", "StubDnsAdapter"),
    "StubGatewayAdapter": ("nettools.adapters.stubs", "StubGatewayAdapter"),
    "StubInventoryConfigAdapter": ("nettools.adapters.stubs", "StubInventoryConfigAdapter"),
    "StubNeighborDiscoveryAdapter": ("nettools.adapters.stubs", "StubNeighborDiscoveryAdapter"),
    "StubProbeAdapter": ("nettools.adapters.stubs", "StubProbeAdapter"),
    "StubServiceDiscoveryAdapter": ("nettools.adapters.stubs", "StubServiceDiscoveryAdapter"),
    "StubSwitchAdapter": ("nettools.adapters.stubs", "StubSwitchAdapter"),
    "StubSyslogEventAdapter": ("nettools.adapters.stubs", "StubSyslogEventAdapter"),
    "StubWirelessControllerAdapter": ("nettools.adapters.stubs", "StubWirelessControllerAdapter"),
    "SwitchAdapter": ("nettools.adapters.switch", "SwitchAdapter"),
    "SyslogEventAdapter": ("nettools.adapters.syslog", "SyslogEventAdapter"),
    "UplinkExpectation": ("nettools.adapters.base", "UplinkExpectation"),
    "WirelessControllerAdapter": ("nettools.adapters.wireless", "WirelessControllerAdapter"),
    "ServiceDiscoveryAdapter": ("nettools.adapters.service_discovery", "ServiceDiscoveryAdapter"),
    "load_stub_fixture_file": ("nettools.adapters.base", "load_stub_fixture_file"),
}


def __getattr__(name: str) -> Any:
    module_name, symbol_name = _EXPORTS[name]
    module = import_module(module_name)
    return getattr(module, symbol_name)


__all__ = [
    "AdapterContext",
    "AdapterEvent",
    "AuthAdapter",
    "AuthFailureCategory",
    "BaseAdapter",
    "DhcpAdapter",
    "DnsAdapter",
    "GatewayAdapter",
    "InterfaceCounters",
    "InventoryConfigAdapter",
    "NeighborDiscoveryAdapter",
    "PolicyMapping",
    "ProbeAdapter",
    "ProbeRequest",
    "ProbeTarget",
    "RelayPathMetadata",
    "StubAuthAdapter",
    "StubDhcpAdapter",
    "StubDnsAdapter",
    "StubGatewayAdapter",
    "StubInventoryConfigAdapter",
    "StubNeighborDiscoveryAdapter",
    "StubProbeAdapter",
    "StubServiceDiscoveryAdapter",
    "StubSwitchAdapter",
    "StubSyslogEventAdapter",
    "StubWirelessControllerAdapter",
    "SwitchAdapter",
    "SyslogEventAdapter",
    "UplinkExpectation",
    "WirelessControllerAdapter",
    "ServiceDiscoveryAdapter",
    "load_stub_fixture_file",
]
