# NETTOOLS Finding Code Registry

This document is the checked-in documentation surface for NETTOOLS finding codes.

Severity semantics:
- `warn`: actionable anomaly or degraded state that does not by itself prove a hard outage.
- `critical`: high-confidence failure or strongly disruptive condition that should be treated as an outage-grade signal.

The table below is the checked-in registry for emitted NETTOOLS finding codes.

| Code | Default Severity | Producer Skills | Summary |
| --- | --- | --- | --- |
| `NOT_IMPLEMENTED` | `warn` | `framework` | The requested skill entrypoint is still scaffolded and has no implemented runtime. |
| `BAD_INPUT` | `warn` | `framework` | The supplied input payload failed validation for the requested NETTOOLS skill. |
| `DEPENDENCY_TIMEOUT` | `warn` | `framework` | A required provider call timed out before the requested evidence could be gathered. |
| `DEPENDENCY_UNAVAILABLE` | `warn` | `framework` | A required provider integration is not configured or is currently unavailable. |
| `INSUFFICIENT_EVIDENCE` | `warn` | `framework` | The skill could not gather enough evidence to reach even a low-confidence conclusion. |
| `UNSUPPORTED_PROVIDER_OPERATION` | `warn` | `framework` | The configured provider cannot perform an operation that the requested skill needs. |
| `LOW_RSSI` | `warn` | `net.client_health` | The observed client RSSI is below the configured minimum threshold. |
| `LOW_SNR` | `warn` | `net.client_health` | The observed client SNR is below the configured minimum threshold. |
| `HIGH_RETRY_RATE` | `warn` | `net.client_health` | The observed client retry rate exceeds the configured threshold. |
| `HIGH_PACKET_LOSS` | `warn` | `net.client_health` | The observed client packet loss is materially elevated. |
| `EXCESSIVE_ROAMING` | `warn` | `net.client_health` | The client roamed excessively within the requested time window. |
| `RAPID_RECONNECTS` | `warn` | `net.client_health` | The client is rapidly disconnecting and reassociating. |
| `STICKY_CLIENT` | `warn` | `net.client_health` | The client appears stuck to a poor AP instead of roaming cleanly. |
| `HIGH_CHANNEL_UTILIZATION` | `warn` | `net.ap_rf_health` | The AP radio channel utilization exceeds the configured threshold. |
| `HIGH_AP_CLIENT_LOAD` | `warn` | `net.ap_rf_health` | The AP radio has more associated clients than the configured threshold allows. |
| `UNSUITABLE_CHANNEL_WIDTH` | `warn` | `net.ap_rf_health` | The configured channel width appears unsuitable for the observed RF conditions. |
| `RADIO_RESETS` | `warn` | `net.ap_rf_health` | The AP radio has reset often enough to indicate instability. |
| `POTENTIAL_CO_CHANNEL_INTERFERENCE` | `warn` | `net.ap_rf_health` | Neighboring AP evidence suggests likely co-channel interference. |
| `HIGH_DHCP_OFFER_LATENCY` | `warn` | `net.dhcp_path` | DHCP discover-to-offer latency is above the configured threshold. |
| `HIGH_DHCP_ACK_LATENCY` | `warn` | `net.dhcp_path` | DHCP request-to-ack latency is above the configured threshold. |
| `DHCP_TIMEOUTS` | `critical` | `net.dhcp_path` | DHCP timeouts indicate the client is not consistently completing lease acquisition. |
| `MISSING_DHCP_ACK` | `critical` | `net.dhcp_path` | DHCP requests are not receiving corresponding acknowledgements. |
| `SCOPE_UTILIZATION_HIGH` | `warn` | `net.dhcp_path` | The relevant DHCP scope is nearing exhaustion. |
| `RELAY_PATH_MISMATCH` | `warn` | `net.dhcp_path` | Observed DHCP relay-path metadata does not match the expected design. |
| `HIGH_DNS_LATENCY` | `warn` | `net.dns_latency` | Observed DNS latency is above the configured threshold. |
| `DNS_TIMEOUT_RATE` | `critical` | `net.dns_latency` | Observed DNS timeout rate exceeds the configured threshold. |
| `UPLINK_SPEED_MISMATCH` | `warn` | `net.ap_uplink_health` | The AP uplink negotiated speed is lower than the expected speed. |
| `UPLINK_ERROR_RATE` | `critical` | `net.ap_uplink_health` | The AP uplink is accumulating CRC or interface errors at a problematic rate. |
| `UPLINK_FLAPPING` | `warn` | `net.ap_uplink_health` | The AP uplink has flapped repeatedly within the observed time window. |
| `UPLINK_VLAN_MISMATCH` | `warn` | `net.ap_uplink_health` | The AP uplink VLAN or native VLAN configuration does not match expectations. |
| `POE_INSTABILITY` | `warn` | `net.ap_uplink_health` | The AP uplink shows PoE instability symptoms. |
| `TOPOLOGY_CHURN` | `warn` | `net.stp_loop_anomaly` | Topology-change churn indicates abnormal L2 convergence activity. |
| `ROOT_BRIDGE_CHANGES` | `warn` | `net.stp_loop_anomaly` | Unexpected root-bridge changes indicate unstable STP behavior. |
| `MAC_FLAP_LOOP_SIGNATURE` | `critical` | `net.stp_loop_anomaly` | MAC-flap patterns strongly suggest a switching loop or equivalent L2 instability. |
| `STORM_INDICATORS` | `critical` | `net.stp_loop_anomaly` | Broadcast or storm indicators suggest severe L2 disruption. |
| `EXCESSIVE_ROAM_COUNT` | `warn` | `net.roaming_analysis` | The client roamed more often than expected during the requested window. |
| `HIGH_ROAM_LATENCY` | `warn` | `net.roaming_analysis` | Average roam latency exceeds the configured threshold. |
| `FAILED_ROAMS` | `critical` | `net.roaming_analysis` | One or more roam attempts failed during the requested time window. |
| `STICKY_CLIENT_PATTERN` | `warn` | `net.roaming_analysis` | Roam behavior indicates a sticky-client pattern instead of healthy transitions. |
| `LOW_AUTH_SUCCESS_RATE` | `warn` | `net.auth_8021x_radius` | Observed 802.1X authentication success rate is below the expected level. |
| `AUTH_TIMEOUTS` | `critical` | `net.auth_8021x_radius` | Authentication attempts are timing out at a problematic rate. |
| `RADIUS_UNREACHABLE` | `critical` | `net.auth_8021x_radius` | The RADIUS service is unreachable from the tested path. |
| `RADIUS_HIGH_RTT` | `warn` | `net.auth_8021x_radius` | RADIUS round-trip time is elevated enough to affect authentication. |
| `AUTH_CREDENTIAL_FAILURES` | `warn` | `net.auth_8021x_radius` | Authentication failures are dominated by invalid or missing credentials. |
| `AUTH_CERTIFICATE_FAILURES` | `warn` | `net.auth_8021x_radius` | Authentication failures are dominated by certificate-related problems. |
| `SITE_WIDE_PATH_LOSS` | `critical` | `net.path_probe` | Path probes show broad packet loss across multiple internal targets. |
| `INTERNAL_SERVICE_DEGRADATION` | `warn` | `net.path_probe` | Path probes show degradation affecting internal service reachability. |
| `WAN_EXTERNAL_DEGRADATION` | `warn` | `net.path_probe` | Path probes show degradation concentrated on WAN or external reachability. |
| `VLAN_MISMATCH` | `warn` | `net.segmentation_policy` | Observed client VLAN does not match the expected policy mapping. |
| `POLICY_GROUP_MISMATCH` | `warn` | `net.segmentation_policy` | Observed policy group or DHCP scope does not match the expected mapping. |
| `GATEWAY_ALIGNMENT_MISMATCH` | `warn` | `net.segmentation_policy` | Observed gateway or relay alignment does not match the expected mapping. |
| `INTAKE_INCOMPLETE_SCOPE` | `warn` | `net.incident_intake` | Incident intake could not normalize enough scope data for a fully targeted diagnosis. |
| `CORRELATED_NETWORK_EVIDENCE` | `warn` | `net.incident_correlation` | Cross-source network evidence aligned with the incident window. |
| `CORRELATED_CHANGE_WINDOW` | `warn` | `net.incident_correlation`, `net.change_detection` | A recent infrastructure change correlates with the incident timing. |
| `RECENT_RELEVANT_CHANGE` | `warn` | `net.change_detection` | A recent configuration or infrastructure change appears relevant to the incident. |
| `RECENT_HARDWARE_OR_FIRMWARE_CHANGE` | `warn` | `net.change_detection` | A recent hardware or firmware event aligns with the affected scope and time window. |
| `CAPTURE_AUTHORIZATION_REQUIRED` | `warn` | `net.capture_trigger` | Packet-capture execution was requested without the required authorization flag. |
| `CAPTURE_SCOPE_TOO_BROAD` | `warn` | `net.capture_trigger` | The requested packet-capture scope is broader than the safety policy allows. |