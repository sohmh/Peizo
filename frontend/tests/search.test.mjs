import test from 'node:test'
import assert from 'node:assert/strict'
import { filterFacilities, filterStations, measurementDefinitionId } from '../src/search.js'

const facilities = [
  { facility_id: 'edged-mesa', facility_name: 'Edged Phoenix', operator: 'Edged', street_address: '8811 E Warner Road', city: 'Mesa', county: 'Maricopa', status: 'unknown', latitude: 33.3, longitude: -111.6, water_disclosures: [{ scope: 'site', water_source: 'unspecified', reported_quantity: null }] },
  { facility_id: 'aligned-phx', facility_name: 'Aligned Behrend site', operator: 'Aligned', street_address: '3151 W Behrend Drive', city: 'Phoenix', county: 'Maricopa', status: 'proposed', latitude: null, longitude: null, water_disclosures: [] },
]
const defaultFilters = { query: '', status: 'all', operator: 'all', city: 'all', verification: 'all', waterSource: 'all', disclosure: 'all' }

test('station filtering is case-insensitive, trims queries, and searches provider plus ID', () => {
  const stations = [{ provider: 'USGS', station_id: 'AZ123' }, { provider: 'ADWR GWSI', station_id: 'ADWR:3321' }]
  assert.equal(filterStations(stations, '  usgs ').length, 1)
  assert.equal(filterStations(stations, '3321')[0].station_id, 'ADWR:3321')
  assert.equal(filterStations(stations, 'USGS / AZ123')[0].station_id, 'AZ123')
  assert.equal(filterStations(stations, '').length, 2)
  assert.equal(filterStations(stations, 'not-found').length, 0)
})

test('facility filtering searches address/name/operator and applies status and coordinate filters', () => {
  assert.equal(filterFacilities(facilities, { ...defaultFilters, query: 'WARNER' })[0].facility_id, 'edged-mesa')
  assert.equal(filterFacilities(facilities, { ...defaultFilters, query: 'aligned' })[0].status, 'proposed')
  assert.equal(filterFacilities(facilities, { ...defaultFilters, status: 'proposed', verification: 'missing' }).length, 1)
  assert.equal(filterFacilities(facilities, { ...defaultFilters, verification: 'published' }).length, 1)
})

test('disclosure filters count site-specific quantities only', () => {
  const rows = [{ ...facilities[0], water_disclosures: [{ scope: 'company_wide', water_source: 'groundwater', reported_quantity: 100 }] }]
  assert.equal(filterFacilities(rows, { ...defaultFilters, waterSource: 'groundwater' }).length, 0)
  assert.equal(filterFacilities(rows, { ...defaultFilters, disclosure: 'with_figure' }).length, 0)
  assert.equal(filterFacilities(rows, { ...defaultFilters, disclosure: 'no_figure' }).length, 1)
})

test('measurement IDs distinguish units and vertical datums for like parameter codes', () => {
  const a = measurementDefinitionId({ parameter_code: '62610', unit: 'ft', vertical_datum: 'NGVD29' })
  const b = measurementDefinitionId({ parameter_code: '62610', unit: 'ft', vertical_datum: 'NAVD88' })
  assert.notEqual(a, b)
  assert.equal(a, '62610|ft|NGVD29')
})
