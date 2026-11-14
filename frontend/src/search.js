const normalized = (value) => String(value ?? '').trim().toLocaleLowerCase()

export const measurementDefinitionId = (definition) =>
  `${definition.parameter_code}|${definition.unit}|${definition.vertical_datum ?? 'not specified in source table'}`

export function filterStations(stations, query) {
  const needle = normalized(query)
  return stations.filter((station) => normalized(`${station.provider ?? ''} / ${station.station_id}`).includes(needle))
}

export function filterFacilities(facilities, filters) {
  const needle = normalized(filters.query)
  return facilities.filter((facility) => {
    const searchMatch = normalized(`${facility.facility_id} ${facility.facility_name} ${facility.operator} ${facility.street_address} ${facility.city} ${facility.county} ${facility.status}`).includes(needle)
    const statusMatch = filters.status === 'all' || facility.status === filters.status
    const operatorMatch = filters.operator === 'all' || facility.operator === filters.operator
    const cityMatch = filters.city === 'all' || facility.city === filters.city || facility.county === filters.city
    const hasCoordinates = facility.latitude !== null && facility.longitude !== null
    const verificationMatch = filters.verification === 'all' || (filters.verification === 'published' ? hasCoordinates : !hasCoordinates)
    const disclosures = (facility.water_disclosures ?? []).filter((disclosure) => disclosure.scope === 'site')
    const sources = disclosures.map((disclosure) => disclosure.water_source)
    const sourceMatch = filters.waterSource === 'all' || (filters.waterSource === 'unknown' ? !sources.length || sources.every((source) => source === 'unspecified') : sources.includes(filters.waterSource))
    const hasFigure = disclosures.some((disclosure) => disclosure.reported_quantity !== null)
    const disclosureMatch = filters.disclosure === 'all' || (filters.disclosure === 'with_figure' ? hasFigure : !hasFigure)
    return searchMatch && statusMatch && operatorMatch && cityMatch && verificationMatch && sourceMatch && disclosureMatch
  })
}
