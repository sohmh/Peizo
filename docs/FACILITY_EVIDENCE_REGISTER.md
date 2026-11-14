# Facility evidence register

## Audit result

No teammate-provided facility list, project documents, permits, or site-specific water-use disclosure files were present in the workspace. Primary-source research expanded the register to six records: Edged Phoenix, a proposed Aligned Behrend site, Mesa's Comarch colocation facility, QTS McDowell Road, and STACK PHX01/PHX02. One record has operator-published point coordinates; one record is explicitly proposed; current operation is unknown for the remaining records. No site-specific withdrawal/consumption quantity is verified. Public-source coverage is incomplete and this is not a census of all Phoenix-area facilities.

## Register schema

Keep facility records separate from water disclosures and evidence citations.

### Facilities

`facility_id`, `facility_name`, `operator`, `owner`, `street_address`, `city`, `county`, `state`, `latitude`, `longitude`, `status` (`operating`, `under_construction`, `proposed`, `closed`, `unknown`), `facility_type`, `location_source_id`, `status_source_id`, `publication_date`, `accessed_date`, `verification_status`, `confidence_notes`, `scope_type` (`campus`, `announced_project`, `permitted_site`, `operator_entity`, `other`).

### Water disclosures

`disclosure_id`, `facility_id` (nullable when scope is regional/company-wide), `scope` (`site`, `regional`, `company_wide`), `reported_quantity`, `original_unit`, `derived_quantity`, `derived_unit`, `metric_type` (`withdrawal`, `consumption`, `recycled`, `other`), `water_source` (`municipal_potable`, `groundwater`, `surface_water`, `reclaimed_recycled`, `other`, `unspecified`), `actual_or_planned`, `direct_or_indirect`, `period_start`, `period_end`, `source_id`, `page_section_table`, `publication_date`, `interpretation_notes`.

### Evidence ledger

`source_id`, `claim_type`, `claim_target_id`, `source_title`, `publisher`, `source_url_or_path`, `publication_date`, `accessed_date`, `page_section_table`, `quoted_or_paraphrased_evidence`, `reliability`, `verification_notes`.

## Evidence rules

- A directory entry is a discovery lead, not proof of operating status. Verify the specific campus and separate campus from operator, cloud region, or headquarters.
- The coordinates, operating status, and water-source/quantity claims need source references individually.
- Do not turn missing water evidence into zero, infer source from a nearby well, allocate corporate totals to local campuses, or estimate from building/cooling/capacity.
- Preserve actual versus planned, withdrawal versus consumption, potable versus reclaimed, and site versus regional/company scope.
- Compare only metrics with matching period, scope, unit and definition. No rankings while records are incomplete or not comparable.
- The observatory reports source-published coordinates separately from independently verified operating status and water quantities, alongside the message that public coverage has not been assessed. This avoids implying zero facilities or zero use.

## Initial data-gap summary

| Coverage field | Current validated count |
|---|---:|
| Sourced facility records in register | 6 |
| Records with source-published coordinates | 1 |
| Records explicitly supported as proposed | 1 |
| Records with current operational status established | 0 |
| Site-specific withdrawal/consumption quantities | 0 |
| Public disclosure search complete | No |

## Current sourced records

### Edged Phoenix (Mesa)

The operator's July 2024 specification sheet gives an address and coordinates and states the facility uses no water for cooling. This is an operator-reported cooling claim, not an independently audited measurement of total site consumption. Its 94.8-million-gallon/year water-savings statement is comparative against an industry-average metric; it is not a measured site quantity and is not represented as one. Overall water source, withdrawal, consumption and current operational status remain unknown. Source evidence is in `data/catalog/evidence.json`.

### Aligned Behrend site (Phoenix)

The City of Phoenix March 25, 2026 Council agenda, Item 80, gives three parcel addresses and describes the proposed data center and requested waiver. The attached waiver copy is marked draft. The record supports a proposed-site address/status entry, not an operating facility claim. Coordinates are absent from the cited record, so the site is searchable but not drawn on the map. No water amount is asserted.

All quantities are intentionally absent. The application should use an explicit not-yet-assessed state until primary-source research has been completed.

### Additional Phoenix-area evidence

- **Comarch Data Center, Mesa:** City of Mesa council minutes (August 18, 2025) identify a Comarch Mesa facility as the City's primary colocation site and discuss a ten-year services contract. The cited record omits its street address and coordinates; current operation and facility water use remain unverified.
- **QTS McDowell Road, Phoenix:** The City of Phoenix's 2023 final plat identifies QTS Phoenix II, LLC and the general area east of 36th Street and south of McDowell Road. This is not point geometry and does not verify current operation or site water use.
- **STACK PHX02, Central Phoenix:** The operator identifies its five-building campus and capacity, but does not publish a street address or operating date on the cited page. Its qualitative water-design language is not treated as measured site water use.
- **STACK PHX01, Avondale:** The operator identifies the campus and capacity but does not publish a street address or operating date on the cited page.

Each record has a linked source entry in `data/catalog/evidence.json`. Facilities without verified point geometry remain searchable in the directory but are not plotted. The Edged waterless-cooling statement remains an operator claim about cooling, not a verified total-site withdrawal or consumption measurement.
