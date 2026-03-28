# NETTOOLS Finding Code Registry

This document is the checked-in documentation surface for NETTOOLS finding codes.

Severity semantics:
- `warn`: actionable anomaly or degraded state that does not by itself prove a hard outage.
- `critical`: high-confidence failure or strongly disruptive condition that should be treated as an outage-grade signal.

The table below is the checked-in registry for emitted NETTOOLS finding codes.
The Expected Operator Action column describes the first follow-up an operator should take when a code appears in a result.

| Code | Default Severity | Producer Skills | Summary | Expected Operator Action |
| --- | --- | --- | --- | --- |
| `NOT_IMPLEMENTED` | `warn` | `framework` | The requested skill entrypoint is still scaffolded and has no implemented runtime. | Use another validated skill or manual workflow; treat this as a feature gap, not an incident signal. |
| `BAD_INPUT` | `warn` | `framework` | The supplied input payload failed validation for the requested NETTOOLS skill. | Correct the identifiers, scope, or time window and rerun the skill. |
| `DEPENDENCY_TIMEOUT` | `warn` | `framework` | A required provider call timed out before the requested evidence could be gathered. | Retry once, then inspect provider latency, API health, or transport reachability. |
| `DEPENDENCY_UNAVAILABLE` | `warn` | `framework` | A required provider integration is not configured or is currently unavailable. | Restore provider configuration or connectivity before trusting the result. |
| `INSUFFICIENT_EVIDENCE` | `warn` | `framework` | The skill could not gather enough evidence to reach even a low-confidence conclusion. | Expand the scope or time window and gather another telemetry source. |
| `UNSUPPORTED_PROVIDER_OPERATION` | `warn` | `framework` | The configured provider cannot perform an operation that the requested skill needs. | Switch to a provider that supports the operation or use the documented manual fallback. |
| `LOW_RSSI` | `warn` | `net.client_health` | The observed client RSSI is below the configured minimum threshold. | Check client location, AP placement, and whether AP RF follow-up is needed. |
| `LOW_SNR` | `warn` | `net.client_health` | The observed client SNR is below the configured minimum threshold. | Check for interference or noisy RF conditions on the serving channel. |
| `HIGH_RETRY_RATE` | `warn` | `net.client_health` | The observed client retry rate exceeds the configured threshold. | Inspect AP RF health and verify whether retries correlate with poor RF or contention. |
| `HIGH_PACKET_LOSS` | `warn` | `net.client_health` | The observed client packet loss is materially elevated. | Compare loss against AP uplink and path-probe results to isolate RF versus upstream issues. |
| `EXCESSIVE_ROAMING` | `warn` | `net.client_health` | The client roamed excessively within the requested time window. | Review roaming-analysis results and confirm AP coverage overlap is not too aggressive. |
| `RAPID_RECONNECTS` | `warn` | `net.client_health` | The client is rapidly disconnecting and reassociating. | Correlate with auth, DHCP, and AP event history to find the reset trigger. |
| `STICKY_CLIENT` | `warn` | `net.client_health` | The client appears stuck to a poor AP instead of roaming cleanly. | Review roaming behavior and RF tuning for minimum-bitrate and steering issues. |
| `HIGH_CHANNEL_UTILIZATION` | `warn` | `net.ap_rf_health` | The AP radio channel utilization exceeds the configured threshold. | Check whether the AP is overloaded and whether channel planning or client redistribution is needed. |
| `HIGH_AP_CLIENT_LOAD` | `warn` | `net.ap_rf_health` | The AP radio has more associated clients than the configured threshold allows. | Rebalance clients, review AP density, or inspect load-balancing behavior. |
| `UNSUITABLE_CHANNEL_WIDTH` | `warn` | `net.ap_rf_health` | The configured channel width appears unsuitable for the observed RF conditions. | Review channel-width configuration for the site and reduce width if contention is high. |
| `RADIO_RESETS` | `warn` | `net.ap_rf_health` | The AP radio has reset often enough to indicate instability. | Inspect AP logs, firmware state, and hardware health for the affected radio. |
| `POTENTIAL_CO_CHANNEL_INTERFERENCE` | `warn` | `net.ap_rf_health` | Neighboring AP evidence suggests likely co-channel interference. | Review channel reuse and neighboring AP assignments for the affected area. |
| `HIGH_DHCP_OFFER_LATENCY` | `warn` | `net.dhcp_path` | DHCP discover-to-offer latency is above the configured threshold. | Check DHCP server response time and relay-path delay for the affected scope. |
| `HIGH_DHCP_ACK_LATENCY` | `warn` | `net.dhcp_path` | DHCP request-to-ack latency is above the configured threshold. | Inspect DHCP server processing time and upstream path latency before lease completion. |
| `DHCP_TIMEOUTS` | `critical` | `net.dhcp_path` | DHCP timeouts indicate the client is not consistently completing lease acquisition. | Treat as service-impacting; inspect DHCP server health, relay reachability, and scope exhaustion immediately. |
| `MISSING_DHCP_ACK` | `critical` | `net.dhcp_path` | DHCP requests are not receiving corresponding acknowledgements. | Verify ACKs are leaving the server and that the return path to clients is intact. |
| `SCOPE_UTILIZATION_HIGH` | `warn` | `net.dhcp_path` | The relevant DHCP scope is nearing exhaustion. | Confirm remaining lease capacity and expand or reclaim the scope before exhaustion. |
| `RELAY_PATH_MISMATCH` | `warn` | `net.dhcp_path` | Observed DHCP relay-path metadata does not match the expected design. | Validate helper addresses and L3 relay path configuration for the impacted VLAN or site. |
| `HIGH_DNS_LATENCY` | `warn` | `net.dns_latency` | Observed DNS latency is above the configured threshold. | Check resolver performance and compare with path-probe latency to the same services. |
| `DNS_TIMEOUT_RATE` | `critical` | `net.dns_latency` | Observed DNS timeout rate exceeds the configured threshold. | Treat as service-impacting; inspect resolver availability, reachability, and packet loss immediately. |
| `UPLINK_SPEED_MISMATCH` | `warn` | `net.ap_uplink_health` | The AP uplink negotiated speed is lower than the expected speed. | Check port speed, cabling, optics, and negotiated duplex on the serving switch port. |
| `UPLINK_ERROR_RATE` | `critical` | `net.ap_uplink_health` | The AP uplink is accumulating CRC or interface errors at a problematic rate. | Treat as infrastructure-impacting; inspect cabling, optics, port counters, and recent physical changes immediately. |
| `UPLINK_FLAPPING` | `warn` | `net.ap_uplink_health` | The AP uplink has flapped repeatedly within the observed time window. | Check port logs, AP power stability, and physical link state for intermittent failures. |
| `UPLINK_VLAN_MISMATCH` | `warn` | `net.ap_uplink_health` | The AP uplink VLAN or native VLAN configuration does not match expectations. | Validate trunk or access-port VLAN settings against the AP deployment standard. |
| `POE_INSTABILITY` | `warn` | `net.ap_uplink_health` | The AP uplink shows PoE instability symptoms. | Inspect PoE budget, power class, and recent switch power events for the port. |
| `TOPOLOGY_CHURN` | `warn` | `net.stp_loop_anomaly` | Topology-change churn indicates abnormal L2 convergence activity. | Review STP events and identify the ports or switches driving repeated convergence. |
| `ROOT_BRIDGE_CHANGES` | `warn` | `net.stp_loop_anomaly` | Unexpected root-bridge changes indicate unstable STP behavior. | Verify STP priorities and determine why root-bridge ownership is moving unexpectedly. |
| `MAC_FLAP_LOOP_SIGNATURE` | `critical` | `net.stp_loop_anomaly` | MAC-flap patterns strongly suggest a switching loop or equivalent L2 instability. | Treat as outage-grade; isolate the suspect segment or port and inspect for a bridging loop immediately. |
| `STORM_INDICATORS` | `critical` | `net.stp_loop_anomaly` | Broadcast or storm indicators suggest severe L2 disruption. | Treat as outage-grade; contain the storm domain and inspect the implicated interfaces immediately. |
| `EXCESSIVE_ROAM_COUNT` | `warn` | `net.roaming_analysis` | The client roamed more often than expected during the requested window. | Review AP overlap, minimum RSSI policy, and whether the user was moving through dense coverage. |
| `HIGH_ROAM_LATENCY` | `warn` | `net.roaming_analysis` | Average roam latency exceeds the configured threshold. | Check 802.11r or fast-roam support, auth latency, and AP-to-controller timing. |
| `FAILED_ROAMS` | `critical` | `net.roaming_analysis` | One or more roam attempts failed during the requested time window. | Treat as user-impacting; inspect roam failure reasons and auth dependencies immediately. |
| `STICKY_CLIENT_PATTERN` | `warn` | `net.roaming_analysis` | Roam behavior indicates a sticky-client pattern instead of healthy transitions. | Review client steering, minimum-bitrate policy, and AP edge-cell tuning. |
| `LOW_AUTH_SUCCESS_RATE` | `warn` | `net.auth_8021x_radius` | Observed 802.1X authentication success rate is below the expected level. | Inspect recent auth failures by category and compare with normal success baselines. |
| `AUTH_TIMEOUTS` | `critical` | `net.auth_8021x_radius` | Authentication attempts are timing out at a problematic rate. | Treat as service-impacting; inspect RADIUS latency, reachability, and upstream path health immediately. |
| `RADIUS_UNREACHABLE` | `critical` | `net.auth_8021x_radius` | The RADIUS service is unreachable from the tested path. | Treat as outage-grade; restore RADIUS connectivity before further auth diagnosis. |
| `RADIUS_HIGH_RTT` | `warn` | `net.auth_8021x_radius` | RADIUS round-trip time is elevated enough to affect authentication. | Check path latency to the RADIUS service and verify server-side performance. |
| `AUTH_CREDENTIAL_FAILURES` | `warn` | `net.auth_8021x_radius` | Authentication failures are dominated by invalid or missing credentials. | Route to identity or policy review rather than infrastructure remediation. |
| `AUTH_CERTIFICATE_FAILURES` | `warn` | `net.auth_8021x_radius` | Authentication failures are dominated by certificate-related problems. | Review client and server certificate validity, trust chain, and EAP policy. |
| `SITE_WIDE_PATH_LOSS` | `critical` | `net.path_probe` | Path probes show broad packet loss across multiple internal targets. | Treat as widespread infrastructure impact; inspect core switching, routing, and transport health immediately. |
| `INTERNAL_SERVICE_DEGRADATION` | `warn` | `net.path_probe` | Path probes show degradation affecting internal service reachability. | Compare degraded destinations to identify the failing service tier or segment. |
| `WAN_EXTERNAL_DEGRADATION` | `warn` | `net.path_probe` | Path probes show degradation concentrated on WAN or external reachability. | Check WAN edge health and confirm internal targets remain clean before escalating externally. |
| `VLAN_MISMATCH` | `warn` | `net.segmentation_policy` | Observed client VLAN does not match the expected policy mapping. | Verify SSID-to-VLAN policy, NAC rules, and recent segmentation changes for the user scope. |
| `POLICY_GROUP_MISMATCH` | `warn` | `net.segmentation_policy` | Observed policy group or DHCP scope does not match the expected mapping. | Validate role mapping, policy group assignment, and DHCP scope selection. |
| `GATEWAY_ALIGNMENT_MISMATCH` | `warn` | `net.segmentation_policy` | Observed gateway or relay alignment does not match the expected mapping. | Check L3 gateway placement, relay targets, and intended VLAN gateway alignment. |
| `INTAKE_INCOMPLETE_SCOPE` | `warn` | `net.incident_intake` | Incident intake could not normalize enough scope data for a fully targeted diagnosis. | Collect missing identifiers, location, or timing details before running deeper diagnostics. |
| `CORRELATED_NETWORK_EVIDENCE` | `warn` | `net.incident_correlation` | Cross-source network evidence aligned with the incident window. | Use the correlated evidence set to decide which subsystem to investigate first. |
| `CORRELATED_CHANGE_WINDOW` | `warn` | `net.incident_correlation`, `net.change_detection` | A recent infrastructure change correlates with the incident timing. | Review the correlated change for rollback, validation, or owner escalation. |
| `RECENT_RELEVANT_CHANGE` | `warn` | `net.change_detection` | A recent configuration or infrastructure change appears relevant to the incident. | Inspect the specific change details and confirm whether symptoms began after it landed. |
| `RECENT_HARDWARE_OR_FIRMWARE_CHANGE` | `warn` | `net.change_detection` | A recent hardware or firmware event aligns with the affected scope and time window. | Check maintenance history, firmware rollout status, and device stability after the change. |
| `CAPTURE_AUTHORIZATION_REQUIRED` | `warn` | `net.capture_trigger` | Packet-capture execution was requested without the required authorization flag. | Obtain the required approval ticket and authorization before any capture attempt. |
| `CAPTURE_SCOPE_TOO_BROAD` | `warn` | `net.capture_trigger` | The requested packet-capture scope is broader than the safety policy allows. | Narrow the capture scope to a specific client, AP, VLAN, or protocol before retrying. |