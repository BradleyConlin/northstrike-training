# Northstrike RPAS SOPs (Transport Canada – Non-Complex Ops)

_Not legal advice. Adapt to your aircraft, pilot cert, and SFOC where applicable._

## 1. Roles
- **PIC** (pilot in command): qualified per CARs 901.64+. Owns go/no-go and safety.
- **VO** (visual observer): maintains VLOS; reports hazards.
- **Payload Op** (if used): sensor control; follows PIC commands.

## 2. Operational Limits (see `configs/safety/limits.yaml`)
- Max altitude AGL: 120 m (400 ft)
- No BVLOS unless SFOC permits.
- Min lateral distance to people not involved: 30 m (basic), see aircraft class.
- Wind: do not exceed platform or `limits.yaml`.
- Night ops: prohibited unless authorized and equipped.

## 3. Pre-Flight
- Authorizations: airspace, NOTAMs, municipal/site permissions.
- Weather brief: ceiling, visibility, winds, temp; density altitude.
- Site survey: obstacles, people/roads, RF, wildlife, emergency areas.
- Geofence loaded where supported; RTL configured; failsafes set.
- Aircraft: firmware, batteries, props, controls, compass/IMU.
- Mission review: `mission/flight_plan.yaml` validated and logged.

## 4. Flight
- Maintain VLOS; VO callouts: traffic/people/animals/obstacles.
- PIC retains manual override; Offboard/autonomy supervised.
- Abort criteria: GNSS loss, EKF errors, link loss, wind/gusts > limit.

## 5. Post-Flight
- Post-flight log, anomalies/maintenance items, data handling per privacy policy.
- Incident reporting per CARs and company policy.

## 6. Emergencies
- Loss of C2 link → RTL or land at safe site; call out location.
- Fly-away → throttle cut if safe; notify ATS if applicable.
- Injury/property damage → first aid/911; secure site; report.

## 7. Recordkeeping
- Keep: flight logs, maintenance logs, training, SFOC/permissions, checklists, incident reports.

## 8. Privacy & Data
- Minimize collection; secure storage; redact where required.

## 9. Revisions
- Changes tracked in repo.
