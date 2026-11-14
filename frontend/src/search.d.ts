export type SearchDisclosure = { scope: string; water_source: string; reported_quantity: number | null }
export type SearchStation = { station_id: string; provider?: string }
export type SearchFacility = {
  facility_id: string; facility_name: string; operator: string; street_address: string; city: string; county: string; status: string
  latitude: number | null; longitude: number | null; water_disclosures?: SearchDisclosure[]
}
export type FacilityFilters = {
  query: string; status: string; operator: string; city: string; verification: string; waterSource: string; disclosure: string
}
export function measurementDefinitionId(definition: { parameter_code: string; unit: string; vertical_datum: string | null }): string
export function filterStations<T extends SearchStation>(stations: T[], query: string): T[]
export function filterFacilities<T extends SearchFacility>(facilities: T[], filters: FacilityFilters): T[]
