# NETTOOLS_TODO2.md

## 1. Overview

This TODO list defines a second NETTOOLS implementation wave focused on discovering, reconstructing, and explaining local-network topology. The goal is to add topology-oriented skills that answer questions such as:

- what is connected to what
- where a client is attached right now
- how traffic likely reaches the gateway or service target
- which VLAN, AP uplink, switch path, or L2 neighbor relationships are involved
- where the evidence is incomplete or contradictory

This phase should stay consistent with the existing NETTOOLS architecture in `docs/NETTOOLS_SPECS.md` and the implementation style established in `docs/NETTOOLS_TODO.md`.

Implementation assumptions for this phase:

- New user-facing capabilities live under `skills/` as OpenClaw skill folders.
- Shared reusable code should extend `skills/nettools-core/` rather than duplicating logic in each skill.
- Outputs should continue using the shared `SkillResult` contract plus structured evidence payloads.
- Topology inference must be evidence-first and confidence-scored; inferred links must never be presented as certain unless backed by direct data.
- The initial version should support fixture-backed development without requiring live controllers or switches.

---

## 2. Proposed skill set

### 2.1 Priority topology skills
- [x] Add `net-l2-neighbor-discovery`
- [x] Add `net-topology-map`
- [x] Add `net-mac-path-trace`
- [x] Add `net-subnet-inventory`
- [x] Add `net-mdns-service-discovery`

### 2.2 Recommended follow-on skills
- [x] Add `net-gateway-health`
- [x] Add `net-rf-interference-scan`
- [x] Add `net-site-baseline-compare`
- [x] Add `net-local-route-anomaly`

### 2.3 Supporting principle
- [x] Keep each skill narrow enough to be useful on its own and composable under `net-diagnose-incident`

---

## 3. Phase 0 - Requirements and architecture extension

### 3.1 Define the topology problem scope
- [ ] Define the exact operator questions these skills must answer
	- [ ] "What switch port or AP is this client on?"
	- [ ] "What is the likely client-to-gateway path?"
	- [ ] "What VLAN / subnet / default gateway is in use?"
	- [ ] "What neighbors are attached to this AP, switch, or router?"
	- [ ] "Which parts of the graph are inferred versus directly observed?"
- [ ] Define supported scopes
	- [ ] client
	- [ ] AP
	- [ ] switch
	- [ ] switch port
	- [ ] VLAN
	- [ ] subnet
	- [ ] site
	- [ ] path
- [ ] Define non-goals for v1 of topology mapping
	- [ ] no full enterprise CMDB replacement
	- [ ] no automated remediation or topology changes
	- [ ] no guarantee of full graph completeness when only partial telemetry is available
	- [ ] no uncontrolled active scanning outside explicit scope

### 3.2 Extend architecture docs
- [x] Update `docs/NETTOOLS_SPECS.md` with a topology-discovery section
	- [x] describe neighbor evidence sources
	- [x] describe topology graph outputs
	- [x] describe confidence and uncertainty handling
	- [x] describe active versus passive discovery modes
- [x] Add a topology-specific section to `skills/nettools-core/ARCHITECTURE.md`
	- [x] graph-building layer
	- [x] evidence-merging layer
	- [x] confidence scoring for inferred links
	- [x] path reconstruction rules
- [x] Add a design note describing when to recommend topology skills from existing incident skills

### 3.3 Define implementation order
- [ ] Lock the delivery order as:
	- [ ] `net-l2-neighbor-discovery`
	- [ ] `net-topology-map`
	- [ ] `net-mac-path-trace`
	- [ ] `net-subnet-inventory`
	- [ ] `net-mdns-service-discovery`
	- [ ] follow-on skills after the topology core is stable

---

## 4. Phase 1 - Shared contracts, graph models, and evidence types

### 4.1 Extend common enums and scope types
- [x] Add scope types if needed for:
	- [x] `subnet`
	- [x] `gateway`
	- [x] `neighbor_graph`
	- [x] `service_discovery`
- [x] Confirm the shared `SkillResult` contract can represent topology outputs without incompatible changes

### 4.2 Add topology-specific finding codes
- [x] Create finding codes for neighbor and path discovery
	- [x] `NEIGHBOR_DISCOVERY_PARTIAL`
	- [x] `NO_NEIGHBOR_DATA_AVAILABLE`
	- [x] `TOPOLOGY_EDGE_INFERRED`
	- [x] `TOPOLOGY_EDGE_CONFLICT`
	- [x] `CLIENT_ATTACHMENT_RESOLVED`
	- [x] `CLIENT_ATTACHMENT_AMBIGUOUS`
	- [x] `MAC_PATH_PARTIAL`
	- [x] `MAC_NOT_OBSERVED`
	- [ ] `VLAN_MEMBERSHIP_CONFLICT`
	- [x] `GATEWAY_PATH_INCOMPLETE`
	- [x] `MDNS_SERVICES_DISCOVERED`
	- [x] `ACTIVE_SCAN_DISABLED`

### 4.3 Define normalized topology models
- [x] Create `NetworkNode`
	- [ ] node ID
	- [ ] node type
	- [ ] hostname / label
	- [ ] management IP if known
	- [ ] MAC if known
	- [ ] vendor / platform if known
	- [ ] site / location metadata
	- [ ] source metadata
- [x] Create `NetworkEdge`
	- [ ] local node ID
	- [ ] remote node ID
	- [ ] edge type
	- [ ] observation source
	- [ ] first seen / last seen
	- [ ] confidence
	- [ ] directly observed boolean
	- [ ] supporting evidence refs
- [x] Create `TopologyGraph`
	- [ ] nodes
	- [ ] edges
	- [ ] unresolved references
	- [ ] confidence summary
	- [ ] graph build timestamp
- [x] Create `NeighborRecord`
	- [ ] protocol (`lldp`, `cdp`, `stp`, `controller_map`, `arp`, `nd`, `bridge_fdb`)
	- [ ] local device / interface
	- [ ] remote device / interface
	- [ ] VLAN or segment context
	- [ ] evidence refs
- [x] Create `MacLocationObservation`
	- [ ] MAC address
	- [ ] device
	- [ ] interface
	- [ ] VLAN
	- [ ] learned type / source
	- [ ] timestamp
- [x] Create `GatewayPathSummary`
	- [ ] origin scope
	- [ ] resolved gateway
	- [ ] path hops / segments
	- [ ] missing segments
	- [ ] confidence
- [x] Create `SubnetInventorySummary`
	- [ ] subnet CIDR
	- [ ] observed hosts
	- [ ] gateways
	- [ ] DHCP scope hints
	- [ ] DNS / mDNS-discovered services
	- [ ] active-scan coverage metadata
- [x] Create `ServiceAdvertisement`
	- [ ] service type
	- [ ] instance name
	- [ ] hostname
	- [ ] IPs
	- [ ] port
	- [ ] TXT metadata
	- [ ] observed_at

### 4.4 Add graph serialization support
- [x] Define machine-readable evidence payloads for graph outputs
- [x] Decide whether graph output should be JSON-only in v1 or support Mermaid export hints
- [x] Add a compact adjacency-list representation for token-efficient agent use
- [x] Add a human-readable path summary format for operator output

### 4.5 Add shared model tests
- [x] Add validation tests for every topology model
- [x] Add round-trip serialization tests
- [x] Add partial-data tolerance tests
- [x] Add confidence-boundary tests
- [x] Add ambiguity and conflict representation tests

---

## 5. Phase 2 - Adapter interfaces for discovery and topology evidence

### 5.1 Add neighbor discovery adapter interface
- [ ] Define methods for:
	- [ ] LLDP neighbors
	- [ ] CDP neighbors
	- [ ] bridge forwarding database / MAC table lookups
	- [ ] interface descriptions and aliases
	- [ ] STP role/state summaries relevant to pathing
- [ ] Define filtering by device, site, and time window
- [ ] Define timeout and partial-result semantics

### 5.2 Extend switch adapter interface
- [ ] Add methods for:
	- [ ] lookup MAC location by address
	- [ ] list learned MACs on interface
	- [ ] resolve VLAN membership on interface
	- [ ] get ARP or neighbor cache if supported
	- [ ] identify trunk versus access interfaces

### 5.3 Extend wireless/controller adapter interface
- [ ] Add methods for:
	- [ ] AP Ethernet uplink identity
	- [ ] AP-to-switch-port mapping evidence
	- [ ] connected client MAC inventory per AP
	- [ ] SSID-to-VLAN mapping evidence
	- [ ] controller-known topology hints if the platform exposes them

### 5.4 Add gateway/router adapter interface
- [ ] Define methods for:
	- [ ] routing table summary for local networks
	- [ ] interface-to-subnet mapping
	- [ ] ARP / neighbor cache
	- [ ] VRRP / HSRP / gateway redundancy hints if relevant
	- [ ] local gateway health counters if available

### 5.5 Add service discovery adapter interface
- [ ] Define methods for:
	- [ ] mDNS browse
	- [ ] mDNS resolve
	- [ ] optional NBNS / LLMNR discovery where available
	- [ ] optional DNS-SD enumeration
- [ ] Define passive-only versus active query modes

### 5.6 Add subnet inventory / probe adapter extensions
- [ ] Define methods for:
	- [ ] ICMP sweep under explicit authorization
	- [ ] ARP sweep under explicit authorization
	- [ ] TCP banner-lite checks for common infrastructure ports under explicit authorization
	- [ ] passive host enumeration from existing telemetry only
- [ ] Add a clear safety gate for active scanning

### 5.7 Stub and fixture support
- [x] Create stub adapters for every new interface
- [x] Ensure fixture-backed development can emulate:
	- [x] simple AP to switch topology
	- [x] partial LLDP visibility
	- [x] conflicting neighbor data
	- [x] MAC learned on multiple ports
	- [x] stale ARP entries
	- [x] unmanaged switch gap in the path
	- [x] mDNS-only host discovery

---

## 6. Phase 3 - Topology and inference analysis library

### 6.1 Build graph construction helpers
- [x] Create a graph builder that merges normalized nodes and edges from multiple sources
- [x] Deduplicate nodes across hostname, MAC, IP, AP ID, and switch inventory identity
- [x] Deduplicate edges across LLDP/CDP/controller/uplink evidence
- [x] Preserve source references per edge
- [x] Support incremental graph construction from partial evidence

### 6.2 Add confidence scoring for inferred topology
- [x] Define confidence rules for:
	- [x] directly observed LLDP/CDP edge
	- [x] AP-to-switch mapping from controller inventory
	- [x] MAC-table inferred client attachment
	- [x] ARP-only adjacency hints
	- [ ] subnet co-membership without direct edge evidence
- [ ] Penalize stale observations
- [x] Penalize conflicting observations
- [x] Promote confidence when multiple independent sources agree

### 6.3 Add ambiguity handling
- [x] Implement ambiguous node matching detection
- [x] Implement edge conflict detection
- [x] Implement stale-data suppression rules
- [ ] Implement loop-protection safeguards so graph assembly does not create impossible duplicate paths
- [x] Add explanations for why a path or attachment is only partially resolved

### 6.4 Add path reconstruction utilities
- [x] Build a client-to-AP path resolver
- [x] Build an AP-to-switch-uplink resolver
- [x] Build a client-to-gateway path resolver
- [ ] Build a service-to-gateway or service-to-client path summarizer when both endpoints are local
- [ ] Add path ranking when multiple candidate paths exist

### 6.5 Add subnet inventory analysis helpers
- [x] Classify hosts as likely:
	- [x] gateway
	- [x] infrastructure
	- [x] AP
	- [ ] switch-managed endpoint
	- [x] workstation / client
	- [x] unknown
- [x] Detect duplicate host identities across sources
- [ ] Detect likely silent segments where telemetry is missing
- [ ] Detect likely unmanaged-switch segments from adjacency gaps

### 6.6 Add service discovery analysis helpers
- [x] Normalize service advertisement records
- [x] Group services by host
- [ ] Group hosts by service type
- [ ] Detect service advertisements without resolvable host records
- [x] Detect local-name conflicts or duplicate instance names

### 6.7 Add recommendation builders
- [x] Recommend `net-ap-uplink-health` when an AP uplink edge is uncertain or degraded
- [x] Recommend `net-stp-loop-anomaly` when the graph is unstable or contradictory
- [ ] Recommend `net-segmentation-policy` when VLAN placement disagrees with expectations
- [ ] Recommend `net-path-probe` when the topology looks correct but latency symptoms remain
- [x] Recommend `net-local-route-anomaly` when gateway path evidence is inconsistent

---

## 7. Phase 4 - Implement priority topology skills

## 7.1 Implement `net-l2-neighbor-discovery`

### 7.1.1 Skill wrapper and CLI
- [ ] Create `skills/net-l2-neighbor-discovery/`
- [ ] Add `SKILL.md`
- [ ] Add helper script entrypoint
- [ ] Document inputs, dependencies, and safe modes

### 7.1.2 Inputs and scope
- [ ] Support querying by:
	- [ ] site
	- [ ] device ID
	- [ ] device name
	- [ ] AP name
	- [ ] switch ID
	- [ ] switch port
	- [ ] VLAN
	- [ ] time window
- [ ] Add optional `protocols` filter
- [ ] Add optional `include_stale` toggle

### 7.1.3 Evidence collection
- [ ] Fetch LLDP neighbors
- [ ] Fetch CDP neighbors where available
- [ ] Fetch interface descriptions
- [ ] Fetch trunk/access metadata
- [ ] Fetch STP state relevant to discovered edges

### 7.1.4 Analysis and output
- [ ] Normalize neighbor records
- [ ] Merge duplicate neighbor observations
- [ ] Flag missing or partial visibility
- [ ] Emit a concise adjacency summary
- [ ] Emit structured findings and recommended next steps

### 7.1.5 Tests
- [ ] Add unit tests for normalized neighbor output
- [ ] Add fixture-backed integration tests for:
	- [ ] clean LLDP topology
	- [ ] CDP-only topology
	- [ ] partial neighbor data
	- [ ] conflicting uplink descriptions

---

## 7.2 Implement `net-topology-map`

### 7.2.1 Skill wrapper and CLI
- [ ] Create `skills/net-topology-map/`
- [ ] Add `SKILL.md`
- [ ] Add helper script entrypoint
- [ ] Document passive-only defaults and explicit active-discovery options

### 7.2.2 Inputs and scope
- [ ] Support scopes:
	- [ ] client
	- [ ] AP
	- [ ] switch
	- [ ] VLAN
	- [ ] subnet
	- [ ] site
- [ ] Add output options:
	- [ ] summary only
	- [ ] adjacency list
	- [ ] full graph JSON
	- [ ] path-to-gateway focus

### 7.2.3 Graph assembly
- [ ] Pull neighbor evidence
- [ ] Pull AP uplink evidence
- [ ] Pull MAC-location evidence where relevant
- [ ] Pull gateway and interface mapping evidence
- [ ] Build a merged topology graph

### 7.2.4 Path explanation
- [ ] Produce the likely client-to-gateway path if a client scope is provided
- [ ] Produce the AP-to-uplink path if an AP scope is provided
- [ ] Produce the VLAN attachment context if a VLAN or subnet scope is provided
- [ ] Mark unresolved segments explicitly

### 7.2.5 Confidence and ambiguity
- [ ] Mark each edge as observed or inferred
- [ ] Include confidence per edge
- [ ] Include conflict notes where evidence disagrees
- [ ] Downgrade global confidence when critical path segments are missing

### 7.2.6 Output shape
- [ ] Emit a human-readable summary
- [ ] Emit graph evidence payload
- [ ] Emit per-edge evidence refs
- [ ] Emit follow-up skills based on missing or suspicious segments

### 7.2.7 Tests
- [ ] Add unit tests for graph assembly
- [ ] Add unit tests for confidence scoring
- [ ] Add integration tests for:
	- [ ] full resolved path
	- [ ] partially inferred path
	- [ ] conflicting edge evidence
	- [ ] unmanaged switch gap
	- [ ] missing gateway data

---

## 7.3 Implement `net-mac-path-trace`

### 7.3.1 Skill wrapper and inputs
- [ ] Create `skills/net-mac-path-trace/`
- [ ] Add `SKILL.md`
- [ ] Add helper script entrypoint
- [ ] Support input by MAC, client ID, hostname, or IP when resolvable

### 7.3.2 Resolution logic
- [ ] Resolve input to a target MAC when possible
- [ ] Query controller session data if the MAC is wireless
- [ ] Query switch MAC tables across relevant devices
- [ ] Query ARP/ND/gateway records to confirm live presence

### 7.3.3 Path trace analysis
- [ ] Determine current or latest known attachment point
- [ ] Trace learned-port progression toward distribution or gateway
- [ ] Detect multi-port ambiguity
- [ ] Detect stale or flapping MAC location evidence
- [ ] Detect apparent movement over time if history exists

### 7.3.4 Output and recommendations
- [ ] Emit the resolved attachment path
- [ ] Emit ambiguity warnings when multiple candidate locations exist
- [ ] Recommend `net-roaming-analysis` if the MAC appears to move between APs
- [ ] Recommend `net-stp-loop-anomaly` if the MAC appears on conflicting ports simultaneously

### 7.3.5 Tests
- [ ] Add unit tests for MAC resolution logic
- [ ] Add integration tests for:
	- [ ] wireless client trace
	- [ ] wired endpoint trace
	- [ ] stale MAC table data
	- [ ] multi-port conflict

---

## 7.4 Implement `net-subnet-inventory`

### 7.4.1 Skill wrapper and inputs
- [ ] Create `skills/net-subnet-inventory/`
- [ ] Add `SKILL.md`
- [ ] Add helper script entrypoint
- [ ] Support input by subnet CIDR, VLAN, SSID, gateway, or site

### 7.4.2 Safety model
- [ ] Default to passive enumeration only
- [ ] Add an explicit authorization flag for active discovery
- [ ] Log whether active probing was used
- [ ] Enforce sensible scope limits for active scans

### 7.4.3 Passive inventory sources
- [ ] Gather DHCP lease hints if available
- [ ] Gather ARP / ND entries
- [ ] Gather controller client inventories
- [ ] Gather switch interface or MAC-derived host hints
- [ ] Gather known gateway and infrastructure interfaces

### 7.4.4 Active inventory options
- [ ] Add ICMP sweep support behind authorization
- [ ] Add ARP sweep support behind authorization
- [ ] Add optional limited TCP reachability checks behind authorization

### 7.4.5 Inventory analysis
- [ ] Deduplicate hosts across passive and active sources
- [ ] Identify gateways and likely infrastructure devices
- [ ] Estimate coverage and blind spots
- [ ] Highlight unknown but active hosts
- [ ] Highlight inconsistent identity data

### 7.4.6 Tests
- [ ] Add unit tests for deduplication and classification
- [ ] Add integration tests for:
	- [ ] passive-only inventory
	- [ ] passive plus active inventory
	- [ ] duplicate identity collapse
	- [ ] sparse telemetry with unknown hosts

---

## 7.5 Implement `net-mdns-service-discovery`

### 7.5.1 Skill wrapper and inputs
- [ ] Create `skills/net-mdns-service-discovery/`
- [ ] Add `SKILL.md`
- [ ] Add helper script entrypoint
- [ ] Support input by subnet, VLAN, site, hostname pattern, or service type

### 7.5.2 Discovery logic
- [ ] Browse mDNS service types
- [ ] Resolve selected services to hostnames and addresses
- [ ] Group results by host
- [ ] Correlate results with subnet inventory if available

### 7.5.3 Output and follow-up
- [ ] Emit discovered services by host and service type
- [ ] Emit unresolved advertisements
- [ ] Recommend `net-subnet-inventory` when service discovery suggests missing inventory coverage
- [ ] Recommend `net-topology-map` when service hosts need path context

### 7.5.4 Tests
- [ ] Add unit tests for advertisement normalization
- [ ] Add integration tests for:
	- [ ] resolved host advertisements
	- [ ] duplicate service instances
	- [ ] unresolved `.local` advertisements

---

## 8. Phase 5 - Implement recommended follow-on skills

## 8.1 Implement `net-gateway-health`
- [x] Create skill wrapper and helper script
- [x] Validate ARP stability, local interface health, first-hop latency, and gateway redundancy hints
- [x] Correlate topology path information with path-probe evidence
- [x] Add tests for gateway degradation, duplicate gateway hints, and healthy baseline cases

## 8.2 Implement `net-rf-interference-scan`
- [x] Create skill wrapper and helper script
- [x] Gather channel occupancy, overlap, and interference hints from controller or local scan data
- [x] Correlate poor RF areas with topology and AP placement context
- [x] Add tests for overlapping-channel and clean-spectrum scenarios

## 8.3 Implement `net-site-baseline-compare`
- [x] Create skill wrapper and helper script
- [x] Compare topology shape, host count, gateway behavior, and service visibility against saved baseline snapshots
- [x] Add tests for expected drift versus anomalous change

## 8.4 Implement `net-local-route-anomaly`
- [x] Create skill wrapper and helper script
- [x] Detect asymmetric local routing, duplicate ARP ownership, wrong gateway choice, and inconsistent interface-to-subnet mappings
- [x] Add tests for asymmetric path, duplicate IP/MAC, and normal-path scenarios

---

## 9. Phase 6 - Orchestrator integration and cross-skill chaining

### 9.1 Extend `net-diagnose-incident` decisioning
- [x] Add routing rules that suggest topology skills when complaints imply:
	- [x] unknown attachment point
	- [x] suspected wrong VLAN / subnet
	- [x] intermittent local-name reachability
	- [x] path uncertainty despite healthy RF metrics
	- [ ] probable unmanaged switch or hidden segment issues

### 9.2 Add new next-action recommendations from existing skills
- [x] Update `net-client-health` follow-up suggestions
- [x] Update `net-ap-uplink-health` follow-up suggestions
- [x] Update `net-segmentation-policy` follow-up suggestions
- [x] Update `net-path-probe` follow-up suggestions
- [x] Update `net-stp-loop-anomaly` follow-up suggestions

### 9.3 Add orchestration fixtures and scenarios
- [ ] Create canonical scenarios where topology skills are the correct next step
	- [ ] client attached to wrong VLAN
	- [ ] AP uplink uncertain
	- [ ] hidden unmanaged switch in path
	- [ ] mDNS-visible host with incomplete path evidence
	- [ ] MAC learned on conflicting switch ports
- [ ] Add replay scenarios showing topology enrichment in the investigation audit trail

---

## 10. Phase 7 - Fixtures, test coverage, and validation baseline

### 10.1 Add fixture datasets
- [ ] Create topology fixture sets for:
	- [ ] small single-switch office
	- [ ] AP plus managed switch plus gateway
	- [ ] multi-switch office with LLDP visibility
	- [ ] partial LLDP visibility and unmanaged gap
	- [ ] stale MAC and stale ARP data
	- [ ] duplicate or conflicting topology evidence
	- [ ] mDNS-rich lab environment

### 10.2 Add unit coverage
- [ ] Cover graph construction
- [ ] Cover edge conflict detection
- [ ] Cover path ranking
- [ ] Cover node deduplication
- [ ] Cover confidence scoring
- [ ] Cover scan authorization logic

### 10.3 Add integration coverage
- [ ] Validate each new skill against fixture-backed adapters
- [ ] Validate orchestrator-driven flows that invoke the topology skills
- [ ] Validate clean degradation under missing providers
- [ ] Validate partial-result behavior under timeout or incomplete telemetry

### 10.4 Add regression and contract coverage
- [ ] Confirm every new skill emits valid shared `SkillResult` output
- [ ] Confirm every new skill preserves raw references when `include_raw=true`
- [ ] Confirm next-action recommendations only reference registered or planned skills
- [ ] Confirm graph outputs remain stable enough for downstream agent consumption

### 10.5 Repo validation tasks
- [x] Run Ruff on all new helper and test modules
- [x] Run MyPy on all new helper and test modules
- [x] Run targeted pytest for topology-related units and integrations
- [x] Run full repo pytest before considering the phase complete

---

## 11. Phase 8 - Documentation, registration, and operator guidance

### 11.1 Register and document new skills
- [x] Add all completed topology skills to `skills/SKILL_LIST.md`
- [x] Update `skills/README.md`
- [x] Update repo `README.md`
- [x] Document any new Python or system dependencies

### 11.2 Add operator guidance
- [ ] Add a "when to use topology skills" section to docs
- [ ] Add examples for:
	- [ ] tracing a wireless client to gateway
	- [ ] identifying the switch path behind an AP
	- [ ] mapping a subnet with passive-only evidence
	- [ ] finding hosts via mDNS
- [ ] Add troubleshooting notes for incomplete or conflicting topology evidence

### 11.3 Add development guidance
- [ ] Document how to add new neighbor evidence sources
- [ ] Document graph model extension rules
- [ ] Document confidence-scoring principles for inferred edges
- [ ] Document safe scanning and authorization boundaries

---

## 12. Definition of done for the topology phase

- [x] `net-l2-neighbor-discovery` is implemented, tested, and documented
- [x] `net-topology-map` can build a partial but operator-useful graph from fixture-backed evidence
- [x] `net-mac-path-trace` can resolve at least the common wireless and wired endpoint cases
- [x] `net-subnet-inventory` supports passive mode by default and explicit active mode by authorization only
- [x] `net-mdns-service-discovery` can correlate service records to local hosts when resolvable
- [x] Inferred edges are explicitly marked and confidence-scored
- [x] Conflicting evidence is surfaced rather than hidden
- [x] Existing incident skills can recommend the topology skills where appropriate
- [x] The new skills degrade cleanly when telemetry is incomplete or providers are unavailable
- [x] Ruff, MyPy, targeted pytest, and full repo pytest all pass
