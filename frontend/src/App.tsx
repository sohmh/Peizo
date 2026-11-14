import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import * as echarts from 'echarts/core'
import type { EChartsOption } from 'echarts'
import { LineChart } from 'echarts/charts'
import { AriaComponent, GridComponent, TooltipComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
import 'maplibre-gl/dist/maplibre-gl.css'
import './map.css'
import { filterFacilities, filterStations, measurementDefinitionId as definitionId } from './search.js'

echarts.use([LineChart, AriaComponent, GridComponent, TooltipComponent, SVGRenderer])

type Facility = {
  facility_id: string; facility_name: string; operator: string; street_address: string; city: string; county: string; state: string
  latitude: number | null; longitude: number | null; status: string; verification_status: string; confidence_notes: string; source_id: string; publication_date?: string | null; accessed_date?: string; water_disclosures?: Disclosure[]
}
type Disclosure = { reported_quantity: number | null; metric_type: string; water_source: string; scope: string; actual_or_planned: string; original_unit?: string | null; period_start?: string | null; period_end?: string | null; page_section_table: string; interpretation_notes: string }
type Evidence = { source_title: string; source_url_or_path: string; page_section_table: string; reliability: string; publication_date?: string | null; accessed_date?: string; quoted_or_paraphrased_evidence?: string }
type Profile = Facility & { water_disclosures: Disclosure[]; evidence: Evidence[] }
type RadarChannel = { term: string; frequency: string; units?: string; available: boolean; image_url?: string; image_corners?: [number, number][]; display_stretch?: { minimum: number; maximum: number; percentiles: number[]; input_units: string } }
type RadarLayer = RadarChannel & { channel_layers?: RadarChannel[] }
type PrismLayer = { available?: boolean; image_url?: string; image_corners?: [number, number][]; regional_mean_mm?: number; display_stretch?: { minimum: number; maximum: number; input_units: string } }
type MeasurementDefinition = { parameter_code: string; unit: string; vertical_datum: string | null }
type Station = { station_id: string; provider?: string; latitude: number; longitude: number; observation_count: number; date_start: string | null; date_end: string | null; measurement_definitions: MeasurementDefinition[] }
type Observation = { date: string; value: number; parameter_code: string; parameter_description: string; unit: string; vertical_datum: string | null; reading_type: string | null; approval_status: string | null; qualifier: string | null; method: string | null }
type RegionalEvidence = { study_area?: string; observed?: string[]; modeled?: string[]; regional_estimate?: string[]; reported?: string[]; hypotheses?: string[]; limitations?: string[] }
type Section = 'Overview' | 'Explore Map' | 'NISAR Radar' | 'Groundwater' | 'Water Context' | 'Facilities' | 'Evidence & Methods'

const sections: Section[] = ['Overview', 'Explore Map', 'NISAR Radar', 'Groundwater', 'Water Context', 'Facilities', 'Evidence & Methods']
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')
const apiUrl = (path: string) => /^https?:\/\//i.test(path) ? path : `${API_BASE}${path}`
const api = (path: string) => fetch(apiUrl(`/api${path}`)).then(r => { if (!r.ok) throw new Error(`API ${r.status}`); return r.json() })

function MapView({ facilities, radar, prism, facilityStatusFilter = 'all', facilityVerificationFilter = 'all' }: { facilities: Facility[]; radar: RadarLayer | null; prism?: PrismLayer | null; facilityStatusFilter?: string; facilityVerificationFilter?: string }) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const radarRef = useRef(radar)
  const radarUrlRef = useRef<string | null>(null)
  radarRef.current = radar
  const [mapReady, setMapReady] = useState(false)
  const [showFacilities, setShowFacilities] = useState(true)
  const [showRadar, setShowRadar] = useState(true)
  const [showRainfall, setShowRainfall] = useState(false)
  const [showGroundwater, setShowGroundwater] = useState(false)
  const [showAdwr, setShowAdwr] = useState(false)
  const [showBasins, setShowBasins] = useState(false)
  const [mapError, setMapError] = useState('')
  useEffect(() => {
    if (!container.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: container.current,
      style: { version: 8, sources: { osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: 'Â© OpenStreetMap contributors' } }, layers: [{ id: 'osm', type: 'raster', source: 'osm' }] },
      center: [-112.074, 33.448], zoom: 8.2, attributionControl: { compact: true },
    })
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right')
    map.on('load', () => setMapReady(true))
    map.on('error', () => setMapError('Basemap tiles could not be reached. Facility records remain available in the directory.'))
    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [])
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    const featureCollection = { type: 'FeatureCollection' as const, features: facilities.filter(f => f.latitude !== null && f.longitude !== null && (facilityStatusFilter === 'all' || f.status === facilityStatusFilter) && facilityVerificationFilter !== 'missing').map(f => ({ type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [f.longitude!, f.latitude!] }, properties: { name: f.facility_name, status: f.status, operator: f.operator } })) }
    if (!map.getSource('facilities')) {
      map.addSource('facilities', { type: 'geojson', data: featureCollection })
      map.addLayer({ id: 'facility-dots', type: 'circle', source: 'facilities', paint: { 'circle-radius': 7, 'circle-color': '#d3a867', 'circle-stroke-width': 2, 'circle-stroke-color': '#11191a' } })
      map.on('click', 'facility-dots', e => {
        const p = e.features?.[0]?.properties
        if (p) {
          const content = document.createElement('div')
          const name = document.createElement('strong'); name.textContent = String(p.name)
          const status = document.createElement('div'); status.textContent = `Status: ${p.status}`
          const operator = document.createElement('div'); operator.textContent = String(p.operator)
          content.append(name, status, operator)
          new maplibregl.Popup().setLngLat(e.lngLat).setDOMContent(content).addTo(map)
        }
      })
    } else (map.getSource('facilities') as maplibregl.GeoJSONSource).setData(featureCollection)
    if (map.getLayer('facility-dots')) map.setLayoutProperty('facility-dots', 'visibility', showFacilities ? 'visible' : 'none')
    if (!map.getSource('groundwater')) {
      fetch(apiUrl('/api/groundwater/stations.geojson')).then(r => { if (!r.ok) throw new Error(`API ${r.status}`); return r.json() }).then(data => {
        if (!mapRef.current || !mapRef.current.isStyleLoaded()) return
        if (!map.getSource('groundwater')) {
          map.addSource('groundwater', { type: 'geojson', data })
          map.addLayer({ id: 'groundwater-dots', type: 'circle', source: 'groundwater', paint: { 'circle-radius': ['interpolate', ['linear'], ['get', 'observation_count'], 1, 2, 200, 5], 'circle-color': '#73b5a5', 'circle-opacity': 0.8, 'circle-stroke-color': '#10201f', 'circle-stroke-width': 1 } })
          map.on('click', 'groundwater-dots', e => {
            const p = e.features?.[0]?.properties
            if (p) {
              const content = document.createElement('div')
              const title = document.createElement('strong'); title.textContent = `Station ${p.station_id}`
              const count = document.createElement('div'); count.textContent = `${p.observation_count} source observations`
              const dates = document.createElement('div'); dates.textContent = `${p.date_start} to ${p.date_end}`
              content.append(title, count, dates)
              new maplibregl.Popup().setLngLat(e.lngLat).setDOMContent(content).addTo(map)
            }
          })
        }
        if (map.getLayer('groundwater-dots')) map.setLayoutProperty('groundwater-dots', 'visibility', showGroundwater ? 'visible' : 'none')
      }).catch(() => setMapError('USGS station layer could not be loaded from the API.'))
    }
    if (map.getLayer('groundwater-dots')) map.setLayoutProperty('groundwater-dots', 'visibility', showGroundwater ? 'visible' : 'none')
    if (!map.getSource('adwr-sites')) {
      fetch(apiUrl('/api/groundwater/adwr-sites.geojson')).then(r => { if (!r.ok) throw new Error(`API ${r.status}`); return r.json() }).then(data => {
        if (!mapRef.current || !mapRef.current.isStyleLoaded() || map.getSource('adwr-sites')) return
        map.addSource('adwr-sites', { type: 'geojson', data })
        map.addLayer({ id: 'adwr-site-dots', type: 'circle', source: 'adwr-sites', paint: { 'circle-radius': 2.5, 'circle-color': '#b17cce', 'circle-opacity': 0.68, 'circle-stroke-width': 0.4, 'circle-stroke-color': '#20152a' } })
        map.setLayoutProperty('adwr-site-dots', 'visibility', showAdwr ? 'visible' : 'none')
        map.on('click', 'adwr-site-dots', e => {
          const p = e.features?.[0]?.properties
          if (p) {
            const content = document.createElement('div')
            const title = document.createElement('strong'); title.textContent = `ADWR GWSI ${p.SITE_ID}`
            const type = document.createElement('div'); type.textContent = `${p.WELL_TYPE ?? 'Well type not recorded'} / ${p.WATER_USE ?? 'Water use not recorded'}`
            const level = document.createElement('div'); const depth = p.WL_DTW == null ? 'not recorded' : `${p.WL_DTW} ft (inventory source value)`; const elevation = p.WL_ELEV == null ? 'not recorded' : `${p.WL_ELEV} ft (vertical datum not stated)`; level.textContent = `Inventory date: ${p.LASTWLDATE ?? 'not stated'} / depth below land surface: ${depth} / water-level elevation: ${elevation}. Historical inventory fields are not current conditions.`
            content.append(title, type, level)
            new maplibregl.Popup().setLngLat(e.lngLat).setDOMContent(content).addTo(map)
          }
        })
      }).catch(() => setMapError('ADWR well layer could not be loaded from the API.'))
    }
    if (map.getLayer('adwr-site-dots')) map.setLayoutProperty('adwr-site-dots', 'visibility', showAdwr ? 'visible' : 'none')
    if (!map.getSource('basin-context')) {
      fetch(apiUrl('/api/context/basins.geojson')).then(r => { if (!r.ok) throw new Error(`API ${r.status}`); return r.json() }).then(data => {
        if (!mapRef.current || !mapRef.current.isStyleLoaded() || map.getSource('basin-context')) return
        map.addSource('basin-context', { type: 'geojson', data })
        map.addLayer({ id: 'basin-fill', type: 'fill', source: 'basin-context', paint: { 'fill-color': ['match', ['get', 'boundary_type'], 'basin', '#719a91', 'subbasin', '#c8a76e', '#82958b'], 'fill-opacity': 0.06 } }, 'facility-dots')
        map.addLayer({ id: 'basin-lines', type: 'line', source: 'basin-context', paint: { 'line-color': ['match', ['get', 'boundary_type'], 'basin', '#79b0a4', 'subbasin', '#d8bc80', '#a3aea3'], 'line-width': ['match', ['get', 'boundary_type'], 'basin', 1.6, 'subbasin', 0.8, 1], 'line-opacity': 0.72 } }, 'facility-dots')
        map.on('click', 'basin-fill', e => {
          const p = e.features?.[0]?.properties
          if (p) new maplibregl.Popup().setLngLat(e.lngLat).setText(`${p.boundary_type}: ${p.boundary_name}`).addTo(map)
        })
        map.setLayoutProperty('basin-fill', 'visibility', showBasins ? 'visible' : 'none')
        map.setLayoutProperty('basin-lines', 'visibility', showBasins ? 'visible' : 'none')
      }).catch(() => setMapError('ADWR basin context could not be loaded from the API.'))
    }
    if (map.getLayer('basin-fill')) map.setLayoutProperty('basin-fill', 'visibility', showBasins ? 'visible' : 'none')
    if (map.getLayer('basin-lines')) map.setLayoutProperty('basin-lines', 'visibility', showBasins ? 'visible' : 'none')
    if (prism?.available && prism.image_url && prism.image_corners) {
      if (!map.getSource('prism-image')) {
        map.addSource('prism-image', { type: 'image', url: apiUrl(prism.image_url), coordinates: prism.image_corners as [[number, number], [number, number], [number, number], [number, number]] })
        map.addLayer({ id: 'prism-image-layer', type: 'raster', source: 'prism-image', paint: { 'raster-opacity': 0.6 } }, 'facility-dots')
      }
      map.setLayoutProperty('prism-image-layer', 'visibility', showRainfall ? 'visible' : 'none')
    }
    if (radar?.available && radar.image_url && radar.image_corners) {
      if (!map.getSource('radar-image')) {
        map.addSource('radar-image', { type: 'image', url: apiUrl(radar.image_url), coordinates: radar.image_corners as [[number, number], [number, number], [number, number], [number, number]] })
        radarUrlRef.current = apiUrl(radar.image_url)
        map.addLayer({ id: 'radar-image-layer', type: 'raster', source: 'radar-image', paint: { 'raster-opacity': 0.72 } }, 'facility-dots')
        map.on('click', 'radar-image-layer', async e => {
          const channel = radarRef.current?.term ?? 'HHHH'
          const params = new URLSearchParams({ longitude: String(e.lngLat.lng), latitude: String(e.lngLat.lat), channel })
          const popup = new maplibregl.Popup().setLngLat(e.lngLat).setText('Reading source pixel...').addTo(map)
          try {
          const result = await fetch(apiUrl(`/api/nisar/sample?${params}`)).then(response => response.json())
            popup.setText(result.value === null || result.value === undefined ? result.message ?? 'No valid source pixel here.' : `${result.channel} / ${result.frequency}: ${result.value.toPrecision(6)} ${result.units} (source GCOV)`)
          } catch { popup.setText('Source pixel sample unavailable.') }
        })
        map.on('mouseenter', 'radar-image-layer', () => { map.getCanvas().style.cursor = 'crosshair' })
        map.on('mouseleave', 'radar-image-layer', () => { map.getCanvas().style.cursor = '' })
      } else if (radarUrlRef.current !== apiUrl(radar.image_url)) {
        (map.getSource('radar-image') as maplibregl.ImageSource).updateImage({ url: apiUrl(radar.image_url), coordinates: radar.image_corners as [[number, number], [number, number], [number, number], [number, number]] })
        radarUrlRef.current = apiUrl(radar.image_url)
      }
      map.setLayoutProperty('radar-image-layer', 'visibility', showRadar ? 'visible' : 'none')
    } else if (map.getLayer('radar-image-layer')) map.setLayoutProperty('radar-image-layer', 'visibility', 'none')
  }, [facilities, radar, prism, mapReady, showFacilities, showRadar, showGroundwater, showAdwr, showBasins, showRainfall, facilityStatusFilter, facilityVerificationFilter])
  return <div className="map-frame"><div className="map" ref={container} role="region" aria-label="Interactive Phoenix map with selectable source-backed evidence layers" />{mapError && <div className="map-warning">{mapError}</div>}<div className="map-controls"><label><input type="checkbox" checked={showRadar} onChange={e => setShowRadar(e.target.checked)} disabled={!radar?.available}/> NISAR {radar?.term ?? 'HHHH'} quicklook</label><label><input type="checkbox" checked={showRainfall} onChange={e => setShowRainfall(e.target.checked)} disabled={!prism?.available}/> PRISM October 2026</label><label><input type="checkbox" checked={showGroundwater} onChange={e => setShowGroundwater(e.target.checked)}/> USGS measurement stations</label><label><input type="checkbox" checked={showAdwr} onChange={e => setShowAdwr(e.target.checked)}/> ADWR GWSI wells</label><label><input type="checkbox" checked={showBasins} onChange={e => setShowBasins(e.target.checked)}/> ADWR basins / subbasins</label><label><input type="checkbox" checked={showFacilities} onChange={e => setShowFacilities(e.target.checked)}/> Facility locations</label></div><div className="map-label"><span className="legend-dot"/> Facilities&nbsp;&nbsp; <span className="well-dot"/> Well stations {radar?.display_stretch && <span className="radar-legend">NISAR p2 {radar.display_stretch.minimum.toPrecision(3)} / p98 {radar.display_stretch.maximum.toPrecision(3)} {radar.display_stretch.input_units}; masked pixels transparent</span>}{prism?.display_stretch && <span className="radar-legend">PRISM display clip {prism.display_stretch.minimum.toFixed(1)}–{prism.display_stretch.maximum.toFixed(1)} mm</span>}</div></div>
}

function App() {
  const [section, setSection] = useState<Section>('Overview')
  const [facilities, setFacilities] = useState<Facility[]>([])
  const [selected, setSelected] = useState<Profile | null>(null)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [operatorFilter, setOperatorFilter] = useState('all')
  const [cityFilter, setCityFilter] = useState('all')
  const [verificationFilter, setVerificationFilter] = useState('all')
  const [waterSourceFilter, setWaterSourceFilter] = useState('all')
  const [disclosureFilter, setDisclosureFilter] = useState('all')
  const [loadError, setLoadError] = useState('')
  const [summary, setSummary] = useState<Record<string, any>>({})
  const [regionalEvidence, setRegionalEvidence] = useState<RegionalEvidence>({})
  const [radarLayer, setRadarLayer] = useState<RadarLayer | null>(null)
  const [radarChannel, setRadarChannel] = useState('HHHH')
  const [radarFrame, setRadarFrame] = useState('71')
  const activeRadarLayer = radarFrame === '71' ? radarLayer?.channel_layers?.find(channel => channel.term === radarChannel) ?? radarLayer : null
  const [prismLayer, setPrismLayer] = useState<PrismLayer | null>(null)
  const [rainfallData, setRainfallData] = useState<{ availability?: string; aggregation?: string; dataset_version?: string; release_number?: number; dataset_create_date?: string; vintage_note?: string; series?: Array<{ date: string; period_label?: string; period_type?: string; value: number; unit: string; valid_cell_count?: number }> }>({})
  const [storageData, setStorageData] = useState<{ availability?: string; mascon_id?: number; native_support?: string; series?: Array<{ date: string; value: number; uncertainty?: number; unit: string }> }>({})
  const [facilitySummary, setFacilitySummary] = useState<Record<string, any>>({})
  const [stations, setStations] = useState<Station[]>([])
  const [stationError, setStationError] = useState('')
  const [selectedStation, setSelectedStation] = useState('')
  const [stationSearch, setStationSearch] = useState('')
  const [selectedParameter, setSelectedParameter] = useState('')
  const [observations, setObservations] = useState<Observation[]>([])
  const [observationError, setObservationError] = useState('')
  useEffect(() => {
    api('/ready').then((data: { status?: string; missing_assets?: string[]; inaccessible_r2_cogs?: string[] }) => {
      if (data.status !== 'ready') setLoadError(`Backend data is incomplete. Missing files: ${(data.missing_assets ?? []).join(', ') || 'none reported'}. Unavailable R2 COGs: ${(data.inaccessible_r2_cogs ?? []).join(', ') || 'none reported'}.`)
    }).catch(() => setLoadError('Backend readiness check failed. Some datasets or R2 radar assets may be unavailable; no substitute data is shown.'))
    api('/facilities').then(setFacilities).catch(() => setLoadError('Facility catalog request failed; facility records are unavailable.'))
    api('/facilities/summary').then(setFacilitySummary).catch(() => setLoadError('Facility coverage summary request failed.'))
    api('/project/summary').then(setSummary).catch(() => setLoadError('Project summary request failed; displayed counts are unavailable.'))
    api('/evidence/phoenix').then(setRegionalEvidence).catch(() => setLoadError('Phoenix evidence profile request failed.'))
    api('/layers').then((rows: Array<{ id: string } & RadarLayer>) => setRadarLayer(rows.find(row => row.id === 'nisar-gcov') ?? null)).catch(() => setLoadError('Map layer catalog request failed; radar availability cannot be verified.'))
    api('/groundwater/stations').then((data: { stations?: Station[]; availability?: string }) => { setStations(data.stations ?? []); if (!data.stations?.length) setStationError(data.availability === 'not_normalized' ? 'Groundwater products are not installed on the API. No station data is being substituted.' : 'No station records were returned for the Phoenix study area.') }).catch(() => setStationError('Station catalog request failed. Check the API connection and study-area data.'))
  }, [])
  useEffect(() => {
    api('/layers').then((rows: Array<{ id: string } & RadarLayer & PrismLayer>) => setPrismLayer(rows.find(row => row.id === 'prism-rainfall') ?? null)).catch(() => setLoadError('Rainfall layer metadata request failed.'))
    api('/rainfall/series').then(setRainfallData).catch(() => setLoadError('Rainfall series request failed; no rainfall chart is available.'))
    api('/water-storage/series').then(setStorageData).catch(() => setLoadError('GRACE series request failed; no water-storage chart is available.'))
  }, [])
  useEffect(() => {
    if (!selectedStation) { setObservations([]); setObservationError(''); return }
    const definition = stations.find(s => s.station_id === selectedStation)?.measurement_definitions.find(d => definitionId(d) === selectedParameter)
    const params = new URLSearchParams()
    if (definition) { params.set('parameter_code', definition.parameter_code); params.set('unit', definition.unit); params.set('vertical_datum', definition.vertical_datum ?? 'not specified in source table') }
    const suffix = params.size ? `?${params}` : ''
    setObservationError('')
    api(`/groundwater/stations/${encodeURIComponent(selectedStation)}/observations${suffix}`).then((data: { observations: Observation[]; availability?: string }) => {
      setObservations(data.observations ?? [])
      if (data.availability !== 'available') setObservationError('Observation records are unavailable for this station; no values were substituted.')
    }).catch(() => { setObservations([]); setObservationError('Observation request failed. The chart has been withheld.') })
  }, [selectedStation, selectedParameter, stations])
  const unique = (values: Array<string | undefined>) => [...new Set(values.filter((v): v is string => Boolean(v)))].sort()
  const filteredStations = filterStations(stations, stationSearch)
  const visibleStations = filteredStations.slice(0, 200)
  const operators = unique(facilities.map(f => f.operator))
  const cities = unique(facilities.map(f => f.city))
  const waterSources = ['unknown', 'municipal_potable', 'groundwater', 'surface_water', 'reclaimed_recycled', 'other', 'unspecified']
  const visibleFacilities = filterFacilities(facilities, { query, status: statusFilter, operator: operatorFilter, city: cityFilter, verification: verificationFilter, waterSource: waterSourceFilter, disclosure: disclosureFilter })
  const openFacility = async (f: Facility) => { try { setSelected(await api(`/facilities/${f.facility_id}`)) } catch { setLoadError(`Evidence profile request failed for ${f.facility_name}.`); setSelected(null) } }
  const title = section === 'Overview' ? 'Phoenix Water & Radar Observatory' : section

  return <div className="app-shell">
    <aside className="rail"><a className="brand" onClick={() => setSection('Overview')}><span className="brand-mark">P</span><span>PIEZO<small>EARTH OBSERVATORY</small></span></a><div className="rail-caption">WORKSPACE</div><nav>{sections.map((s, i) => <button key={s} className={section === s ? 'nav-item active' : 'nav-item'} onClick={() => setSection(s)}><span className="nav-index">0{i + 1}</span>{s}</button>)}</nav><div className="rail-bottom"><span className="live-dot"/>LOCAL DATA CATALOG<small>PHOENIX Â· ARIZONA</small></div></aside>
    <main className="main">
      <header className="topbar"><div><span className="eyebrow">FIELD SYSTEMS / SOUTHWEST</span><h1>{title}</h1></div><div className="top-meta"><span className="status-pill"><i/> SCIENCE MODE</span><span className="coord">33.448Â° N&nbsp;&nbsp; 112.074Â° W</span></div></header>
      {loadError && <div className="notice">{loadError}</div>}
      {section === 'Overview' && <>
        <div className="intro"><div><span className="eyebrow amber">MISSION BRIEF / 01</span><p>Observe Phoenix through radar, wells, climate and reported infrastructure evidence. Each layer keeps its source and scale visible.</p></div><div className="brief-tag">EVIDENCE FIRST <span>â†—</span></div></div>
        <div className="overview-grid"><section className="map-section"><div className="section-head"><div><span className="eyebrow">SPATIAL OVERVIEW</span><h2>Phoenix metro region</h2></div><button className="text-button" onClick={() => setSection('Explore Map')}>OPEN MAP â†—</button></div><MapView facilities={facilities} radar={activeRadarLayer ?? null} prism={prismLayer}/><div className="map-foot"><span>Base map Â· OpenStreetMap</span><span>Only source-backed facility coordinates are mapped; facilities without verified coordinates remain in the directory</span></div></section>
          <aside className="readout"><div className="section-head"><div><span className="eyebrow">CATALOG STATUS</span><h2>Evidence on hand</h2></div></div><div className="readout-list"><Readout label="NISAR frames" value={summary.nisar_scene_count ?? 'â€”'} note="One acquisition pass Â· Oct 28, 2026"/><Readout label="Groundwater coverage" value={`${summary.usgs_station_count ?? 0} / ${summary.adwr_gwsi_site_count ?? 0}`} note={`USGS stations / ADWR inventory sites; ${summary.adwr_gwsi_sites_with_level_measurements ?? 0} ADWR sites have level records`}/><Readout label="Facility records" value={summary.facility_records ?? 'â€”'} note="Source-backed records Â· gaps shown"/><Readout label="Water disclosures" value={summary.water_disclosures ?? 'â€”'} note="No site-specific quantity verified"/></div><div className="interpretation"><span className="eyebrow amber">READ WITH CARE</span><p>GCOV measures radar response at the surface. It does not measure groundwater depth or prove why a surface changed.</p></div></aside>
        </div>
        <section className="bottom-band"><div><span className="eyebrow">CURRENT OBSERVATION</span><h3>Single-date radar coverage</h3><p>Two adjacent NISAR frames cover Phoenix on the same descending pass. Temporal change analysis needs another compatible date.</p></div><button className="outline-button" onClick={() => setSection('NISAR Radar')}>EXPLORE NISAR <span>â†—</span></button></section>
      </>}
      {section === 'Explore Map' && <div className="content-page"><div className="page-intro"><span className="eyebrow">INTERACTIVE GEOSPATIAL EXPLORER</span><p>Toggle evidence layers as they are validated. Unavailable layers are identified without simulated values.</p></div><MapView facilities={facilities} radar={activeRadarLayer ?? null} prism={prismLayer}/><div className="layer-list"><Layer name="Verified facility locations" state="1 source-published point Â· proposed site not mapped without coordinates"/><Layer name="NISAR GCOV HH / HV" state={radarLayer?.available ? `Frame 71 ${radarLayer.display_stretch?.input_units ?? ''} display quicklook` : 'Source available Â· georeferenced display product pending'}/><Layer name="Groundwater observations" state={`${summary.usgs_station_count ?? 0} USGS stations; ${summary.adwr_gwsi_site_count ?? 0} ADWR sites (${summary.adwr_gwsi_sites_with_level_measurements ?? 0} with level records)`}/><Layer name="Rainfall / PRISM" state={prismLayer?.available ? `October 2026 · ${prismLayer.regional_mean_mm?.toFixed(1)} mm Phoenix rectangle mean` : 'Processing pending'}/><Layer name="GRACE / GRACE-FO" state={`${storageData.series?.length ?? 0} monthly records · coarse regional mascon support`}/></div></div>}
      {section === 'NISAR Radar' && <div className="content-page"><div className="page-intro"><span className="eyebrow">L-BAND / L2 GCOV</span><p>Measured GCOV source values clipped to the Phoenix rectangle. Frames 71 and 72 are adjacent spatial frames from the same acquisition date and pass, not independent temporal observations. No temporal comparison is available.</p><label className="channel-select">SOURCE FRAME<select value={radarFrame} onChange={e => setRadarFrame(e.target.value)}><option value="71">Frame 71 · crop processed</option><option value="72">Frame 72 · source only</option></select></label><label className="channel-select">POLARIMETRIC TERM<select value={radarChannel} disabled={radarFrame !== '71'} onChange={e => setRadarChannel(e.target.value)}>{(radarLayer?.channel_layers ?? []).map(c => <option key={c.term} value={c.term} disabled={!c.available}>{c.term} / {c.frequency}{c.available ? '' : ' (not processed)'}</option>)}</select></label></div><MapView facilities={facilities} radar={activeRadarLayer} prism={prismLayer}/><div className="radar-panel"><div className="radar-info"><span className="eyebrow amber">{activeRadarLayer?.available ? 'FRAME 71 PHOENIX CROP PROCESSED' : `FRAME ${radarFrame} · SOURCE AVAILABLE, MAP PRODUCT NOT PROCESSED`}</span><h2>2026-10-28 / Descending</h2><p>Selected frame {radarFrame} · Frame 71: 02:15:35–02:16:10 UTC · Frame 72: 02:16:09–02:16:44 UTC · Track 56 / Product P05036 / v1.0.20</p><dl><dt>Displayed channel</dt><dd>{activeRadarLayer?.term ?? radarChannel} / {activeRadarLayer?.frequency ?? 'frequencyA'} / {activeRadarLayer?.display_stretch?.input_units ?? 'unitless'}</dd><dt>Processed channels</dt><dd>Frame 71: HHHH and HVHV Frequency A / 10 m; Frequency B remains unprocessed</dd><dt>Map projection</dt><dd>WGS 84 / UTM zone 12N / EPSG:32612</dd><dt>Temporal comparison</dt><dd>Unavailable / both frames are from the same pass and date</dd></dl><p className="science-note">Radar backscatter responds to surface conditions and acquisition geometry. It is not a groundwater-depth map.</p></div></div></div>}
      {section === 'Groundwater' && <div className="content-page"><div className="page-intro"><span className="eyebrow">ARIZONA WELL OBSERVATIONS / USGS + ADWR GWSI</span><p>USGS field measurements and ADWR GWSI well-level records filtered to the documented Phoenix rectangle. Series retain provider, measurement code, unit, date, source/method/remark and datum context. No interpolation or unit conversion is applied. All dates are archive observation dates, not current conditions.</p></div><div className="well-toolbar"><div className="station-picker"><label>FIND STATION<input type="search" placeholder="Search provider or site ID" aria-label="Search groundwater stations by provider or ID" value={stationSearch} onChange={e => { setStationSearch(e.target.value); setSelectedStation(''); setSelectedParameter('') }}/></label><label>SELECT FROM MATCHES<select value={selectedStation} onChange={e => { const next = stations.find(s => s.station_id === e.target.value); setSelectedStation(e.target.value); setStationSearch(next ? `${next.provider ?? 'USGS'} / ${next.station_id}` : stationSearch); setSelectedParameter(next?.measurement_definitions[0] ? definitionId(next.measurement_definitions[0]) : '') }}><option value="">Choose a station ({filteredStations.length} matches)</option>{visibleStations.map(s => <option key={`${s.provider}-${s.station_id}`} value={s.station_id}>{s.provider} / {s.station_id} · {s.observation_count} records · {s.date_start ?? 'undated'}–{s.date_end ?? ''}</option>)}</select></label></div>{selectedStation && <label>MEASUREMENT DEFINITION<select value={selectedParameter} onChange={e => setSelectedParameter(e.target.value)}>{(stations.find(s => s.station_id === selectedStation)?.measurement_definitions ?? []).map(d => <option key={definitionId(d)} value={definitionId(d)}>{d.parameter_code} · {d.unit} · {d.vertical_datum ?? 'vertical datum not stated'}</option>)}</select></label>}<div className="well-count"><b>{stations.length.toLocaleString()}</b><span>CATALOG ENTRIES · PROVIDER COUNTS BELOW</span></div></div>{stationError && <div className="notice">{stationError}</div>}{observationError && <div className="notice">{observationError}</div>}{filteredStations.length > visibleStations.length && <p className="data-source-note">Showing the first {visibleStations.length} of {filteredStations.length.toLocaleString()} matches. Refine the search to find a specific station.</p>}<div className="provider-counts"><span>USGS measurement stations: {summary.usgs_station_count ?? 0}</span><span>ADWR inventory sites: {summary.adwr_gwsi_site_count ?? 0}</span><span>ADWR sites with joined level data: {summary.adwr_gwsi_sites_with_level_measurements ?? 0}</span></div>{selectedStation ? <TimeSeriesChart station={stations.find(s => s.station_id === selectedStation)!} observations={observations}/> : <div className="empty-panel"><span className="empty-icon">âŒ–</span><h2>Choose a monitoring station</h2><p>{summary.usgs_station_count ?? 0} USGS measurement stations and {summary.adwr_gwsi_site_count ?? 0} ADWR inventory sites fall inside the study rectangle; only {summary.adwr_gwsi_sites_with_level_measurements ?? 0} ADWR sites have joined level measurements. These provider counts are not a deduplicated well census. Select a station to inspect the actual dated measurements.</p><div className="tag-row"><span>DEPTH TO WATER Â· ft below land surface</span><span>WATER LEVEL Â· datum-specific elevation</span></div></div>}<p className="data-source-note">Source: teammate-supplied USGS field-measurements export. The USGS export query URL was not included in the download folder. ADWR well-level measurements do not identify a vertical datum for elevation fields; source/method/remark codes remain undecoded. Zero values are preserved from the source and are not interpreted as missing or zero-depth without a codebook match.</p></div>}
      {section === 'Water Context' && <div className="content-page"><div className="page-intro"><span className="eyebrow">CLIMATE & REGIONAL STORAGE</span><p>Context layers retain their native scale. Rainfall is not proof of recharge; GRACE total storage is not groundwater-only or facility-scale.</p></div><div className="context-grid"><Context title="PRISM precipitation" kind="MODELED CLIMATE GRID" body={`October 2026 monthly precipitation accumulation in millimeters, reported as a native-cell mean for one month, not a time series. The source grid is 30 arc-second (~800 m); only valid pixel centers inside the Phoenix rectangle are included. Product ${rainfallData.dataset_version ?? 'version not stated'} release ${rainfallData.release_number ?? 'not stated'}; monthly values remain subject to PRISM revisions.`}/><Context title="GRACE / GRACE-FO" kind="REGIONAL STORAGE ESTIMATE" body={`JPL RL06.3Mv04 CRI total water storage anomaly for mascon ${storageData.mascon_id ?? '—'}, which contains central Phoenix. Native support is an approximately 3-degree equal-area mascon.`}/></div>{rainfallData.series?.length ? <EvidenceSeriesChart title="Phoenix rectangle · monthly precipitation" subtitle={`One available month; a single contextual cell-mean summary, not a time series. PRISM ${rainfallData.dataset_version ?? ''} release ${rainfallData.release_number ?? 'unknown'} · created ${rainfallData.dataset_create_date ?? 'date unavailable'}; provisional monthly product.`} unit="mm" source="PRISM Climate Group · October 2026 · mm precipitation" series={rainfallData.series}/> : <div className="notice">PRISM grid is not processed.</div>}{storageData.series?.length ? <EvidenceSeriesChart title="Total water storage anomaly · Phoenix mascon" subtitle={`${storageData.native_support ?? 'Coarse regional mascon support'} · total terrestrial storage, not groundwater only.`} unit="cm" source="NASA/JPL PO.DAAC · GRACE/GRACE-FO RL06.3Mv04 CRI" series={storageData.series}/> : <div className="notice">GRACE series is not processed.</div>}</div>}
      {section === 'Facilities' && <div className="content-page"><div className="page-intro facility-intro"><div><span className="eyebrow">DATA-CENTRE OBSERVATORY</span><p>Facility claims are tracked separately from operator-wide reports. Unknown water sources and missing figures remain explicit.</p></div><div className="gap-chip">PUBLIC SEARCH IN PROGRESS</div></div><MapView facilities={facilities} radar={activeRadarLayer ?? null} prism={prismLayer} facilityStatusFilter={statusFilter} facilityVerificationFilter={verificationFilter}/><div className="map-foot"><span>Verified points require source-published coordinates</span><span>Proposed addresses without verified coordinates are not plotted</span></div><div className="facility-stats"><Stat value={facilitySummary.verified_locations ?? 0} label="SOURCE-PUBLISHED LOCATIONS"/><Stat value={facilitySummary.operating_status_verified ?? 0} label="VERIFIED OPERATING STATUS"/><Stat value={facilitySummary.site_specific_water_figures ?? 0} label="SITE-SPECIFIC WATER FIGURES"/><Stat value={facilitySummary.facility_records ?? facilities.length} label="REGISTER RECORDS"/></div><div className="facility-layout"><div className="facility-list-panel"><div className="filters"><input aria-label="Search facilities" placeholder="Search name, operator, cityâ€¦" value={query} onChange={e => setQuery(e.target.value)}/><select aria-label="Filter by operator" value={operatorFilter} onChange={e => setOperatorFilter(e.target.value)}><option value="all">All operators</option>{operators.map(v => <option key={v}>{v}</option>)}</select><select aria-label="Filter by city or county" value={cityFilter} onChange={e => setCityFilter(e.target.value)}><option value="all">All cities / counties</option>{unique([...cities, ...facilities.map(f => f.county)]).map(v => <option key={v}>{v}</option>)}</select><select aria-label="Filter by status" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option value="all">All status</option><option value="operating">Operating</option><option value="under_construction">Under construction</option><option value="proposed">Proposed</option><option value="closed">Closed</option><option value="unknown">Unknown</option></select><select aria-label="Filter by location verification" value={verificationFilter} onChange={e => setVerificationFilter(e.target.value)}><option value="all">All coordinate evidence</option><option value="published">Coordinates published</option><option value="missing">Coordinates unavailable</option></select><select aria-label="Filter by water source" value={waterSourceFilter} onChange={e => setWaterSourceFilter(e.target.value)}><option value="all">All water-source evidence</option>{waterSources.map(v => <option key={v}>{v}</option>)}</select><select aria-label="Filter by disclosure availability" value={disclosureFilter} onChange={e => setDisclosureFilter(e.target.value)}><option value="all">All disclosure status</option><option value="with_figure">Reported quantity</option><option value="no_figure">No verified quantity</option></select></div>{visibleFacilities.map(f => <button key={f.facility_id} className="facility-row" onClick={() => openFacility(f)}><span className="facility-marker">âŒ–</span><span><b>{f.facility_name}</b><small>{f.operator} Â· {f.city}</small></span><span className={`status-label ${f.status}`}>{f.status.replace('_', ' ')}</span></button>)}{visibleFacilities.length === 0 && <p className="no-results">No matching registered facilities.</p>}</div><div className="facility-detail">{selected ? <FacilityDetail profile={selected}/> : <div className="detail-empty"><span className="eyebrow">SELECT A FACILITY</span><h2>Evidence profile</h2><p>Open a record to inspect its location basis, status confidence, water disclosures and source documents.</p><p className="muted">A blank quantity means no verified site-specific figure was found in the current register. It does not mean zero use.</p></div>}</div></div><p className="data-source-note">Directory search covers {visibleFacilities.length} of {facilities.length} matching sourced records; coordinates and water disclosures remain incomplete where evidence is unavailable. No facility water amount is imputed.</p></div>}
      {section === 'Evidence & Methods' && <div className="content-page"><div className="page-intro"><span className="eyebrow">PROVENANCE / METHODS / LIMITATIONS</span><p>PIEZO keeps radar observations, ground measurements, modeled context, regional estimates and reported disclosures distinct.</p></div><div className="method-list"><Context title="Radar observation" kind="NISAR L2 GCOV" body="Geocoded covariance/backscatter information. Surface response can be influenced by moisture, roughness, vegetation, land cover and geometry. It does not directly measure deep groundwater."/><Context title="Ground observations" kind="USGS + ADWR" body="Measurements are local to monitoring stations. Depth below land surface, elevation and vertical datum are preserved as separate variables."/><Context title="Reported facility evidence" kind="EVIDENCE REGISTER" body="Location and operating status each require evidence. Water values remain tied to reporting scope, date, definition and source page. Proximity does not establish cause."/><Context title="Source documents" kind="PRIMARY RECORDS" body="Edged operator specification (July 2024) and City of Phoenix Council agenda Item 80 (March 25, 2026) are linked in each facility profile."/></div><RegionalEvidenceProfile data={regionalEvidence}/><SourcesAndGlossary/></div>}
      <footer><span>PIEZO / PHOENIX WATER & RADAR OBSERVATORY</span><span>OBSERVATIONS Â· MEASUREMENTS Â· REPORTED EVIDENCE</span></footer>
    </main>
  </div>
}

function Readout({ label, value, note }: { label: string; value: string | number; note: string }) { return <div className="readout-row"><div><span>{label}</span><small>{note}</small></div><strong>{value}</strong></div> }
function Layer({ name, state }: { name: string; state: string }) { return <div className="layer-row"><span className="layer-toggle"/><div><b>{name}</b><small>{state}</small></div><span className="layer-meta">i</span></div> }
function Stat({ value, label }: { value: string | number; label: string }) { return <div className="stat"><strong>{value}</strong><span>{label}</span></div> }
function Context({ title, kind, body }: { title: string; kind: string; body: string }) { return <article className="context-card"><span className="eyebrow amber">{kind}</span><h2>{title}</h2><p>{body}</p><span className="card-arrow">â†—</span></article> }


function RegionalEvidenceProfile({ data }: { data: RegionalEvidence }) {
  const groups = [
    ['Observed', data.observed ?? []],
    ['Modeled context', data.modeled ?? []],
    ['Regional estimate', data.regional_estimate ?? []],
    ['Reported claims', data.reported ?? []],
    ['Hypotheses', data.hypotheses ?? []],
  ]
  return <section className="regional-evidence"><div className="section-head"><div><span className="eyebrow amber">REGIONAL EVIDENCE PROFILE</span><h2>{data.study_area ?? 'Phoenix metropolitan region'}</h2></div><span className="gap-chip">CAUSAL LINK NOT ESTABLISHED</span></div><div className="evidence-classes">{groups.map(([name, entries]) => <article key={String(name)}><h3>{name}</h3>{(entries as string[]).length ? <ul>{(entries as string[]).map(item => <li key={item}>{item}</li>)}</ul> : <p>No supported entry in current evidence register.</p>}</article>)}</div><div className="evidence-limitations"><b>Interpretation limits</b><ul>{(data.limitations ?? []).map(item => <li key={item}>{item}</li>)}</ul></div></section>
}

function SourcesAndGlossary() {
  const sources = [
    ['NASA/JPL NISAR L2 GCOV product', 'https://doi.org/10.5067/NIL2GCOV-V1'],
    ['NASA/JPL GRACE/GRACE-FO RL06.3Mv04 CRI', 'https://doi.org/10.5067/TEMSC-3JC634'],
    ['PRISM data documentation and units', 'https://www.prism.oregonstate.edu/faq/'],
    ['Arizona ADWR Groundwater Site Inventory package', 'Datasets/GWSI_ZIP_20260714/GWSI_README.txt'],
    ['USGS groundwater export', 'Datasets/2026-11-14T11-47-59.452Z-download/ (source query URL not included in supplied files)'],
    ['Edged Phoenix specification sheet (July 2024)', 'https://assets.website-files.com/62f4046c4606ae485a2c58ec/6686503f566fcb42ef9d6ce7_Phoenix_Spec_Sheet_July2024.pdf'],
    ['City of Phoenix Council agenda, Item 80 (March 25, 2026)', 'https://www.phoenix.gov/content/dam/phoenix/cityclerksite/city-council-meeting-files/2026/3-25-26%20Formal%20Agenda-FINAL.pdf'],
    ['City of Mesa Comarch colocation record (August 18, 2025)', 'https://apps.mesaaz.gov/meetingarchive/ArchiveDocuments/ClerkDetailedMinutes/August%2018%2C%202025%20RGL.pdf'],
    ['City of Phoenix QTS McDowell Road plat (March 22, 2023)', 'https://www.phoenix.gov/content/dam/phoenix/cityclerksite/city-council-meeting-files/2023/3-22-23%20formal%20agenda%20-%20final.pdf'],
    ['City of Phoenix development narrative with QTS adjacent-use context', 'https://web-prod.phoenix.gov/content/dam/phoenix/pddsite/documents/pz/40th%20street%20and%20mcdowell%20pud%20development%20narrative%20-%20hearing%20draft.pdf'],
    ['STACK PHX02 Central Phoenix campus', 'https://www.stackinfra.com/locations/americas/phoenix/phx02/'],
    ['STACK PHX01 Avondale campus', 'https://www.stackinfra.com/locations/americas/phoenix/phx01/'],
  ]
  const terms = [
    ['GCOV', 'Geocoded covariance product; the displayed channel is a source radar covariance term.'],
    ['Depth to water', 'Vertical distance from land surface to water in a well; not interchangeable with water-level elevation.'],
    ['Water-level elevation', 'Elevation of the water surface relative to a named vertical datum such as NAVD88 or NGVD29.'],
    ['Mascon', 'GRACE gravity solution region; the source grid is a display representation of larger native support.'],
    ['Withdrawal / consumption', 'Withdrawal is water taken from a source; consumption is the portion not returned to the same water system. They are separate reporting metrics.'],
    ['Evidence gap', 'A claim field without adequate source support; blank values remain unknown and are never treated as zero.'],
  ]
  return <div className="source-glossary"><section><span className="eyebrow amber">SOURCE REGISTER</span><h2>Data and evidence references</h2><div className="source-list">{sources.map(([label, href]) => <a key={label} href={href.startsWith('http') ? href : undefined} target={href.startsWith('http') ? '_blank' : undefined} rel="noreferrer"><b>{label}</b><small>{href}</small></a>)}</div></section><section><span className="eyebrow amber">GLOSSARY</span><h2>Terms used in PIEZO</h2><dl className="glossary-list">{terms.map(([term, definition]) => <div className="glossary-entry" key={term}><dt>{term}</dt><dd>{definition}</dd></div>)}</dl></section><p className="data-source-note">The USGS export did not retain its source query URL. Facility water claims are limited to the cited source records; public-source search remains incomplete.</p></div>
}

function ChartView({ option, height }: { option: EChartsOption; height: number }) {
  const element = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!element.current) return
    const chart = echarts.init(element.current, undefined, { renderer: 'svg' })
    chart.setOption(option, true)
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(element.current)
    return () => { observer.disconnect(); chart.dispose() }
  }, [option])
  return <div ref={element} style={{ height, width: '100%' }}/>
}

function EvidenceSeriesChart({ title, subtitle, unit, source, series }: { title: string; subtitle: string; unit: string; source: string; series: Array<{ date: string; period_label?: string; period_type?: string; value: number; unit?: string; uncertainty?: number }> }) {
  if (!series.length) return null
  const monthlySummary = series.length === 1 && series[0].period_type === 'monthly'
  const hasUncertainty = series.some(point => point.uncertainty !== undefined)
  const xValue = (point: typeof series[number]) => monthlySummary ? point.period_label ?? point.date : point.date
  const central = { type: 'line' as const, name: title, data: series.map(point => [xValue(point), point.value]), showSymbol: series.length === 1, symbolSize: 7, connectNulls: false, lineStyle: { color: '#82c4ad', width: 2 }, itemStyle: { color: '#d7b36f' }, z: 3 }
  const uncertaintyBand = hasUncertainty ? [
    { type: 'line' as const, name: 'Lower uncertainty bound', data: series.map(point => [xValue(point), point.value - (point.uncertainty ?? 0)]), stack: 'source-uncertainty', symbol: 'none' as const, lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(0,0,0,0)' }, tooltip: { show: false }, z: 1 },
    { type: 'line' as const, name: 'Reported source uncertainty', data: series.map(point => [xValue(point), (point.uncertainty ?? 0) * 2]), stack: 'source-uncertainty', symbol: 'none' as const, lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(130,196,173,0.18)' }, tooltip: { show: false }, z: 1 },
  ] : []
  const option: EChartsOption = {
    animation: false,
    aria: { enabled: true },
    grid: { left: 72, right: 24, top: 32, bottom: 54 },
    tooltip: { trigger: 'axis', valueFormatter: value => `${Number(value).toPrecision(5)} ${unit}` },
    xAxis: { type: monthlySummary ? 'category' : 'time', name: monthlySummary ? 'Reporting month' : 'Date', nameLocation: 'middle', nameGap: 34, axisLabel: { color: '#8f9e98' }, axisLine: { lineStyle: { color: '#687773' } } },
    yAxis: { type: 'value', name: unit, nameLocation: 'middle', nameGap: 48, scale: true, axisLabel: { color: '#8f9e98' }, splitLine: { lineStyle: { color: '#33403e', type: 'dashed' } } },
    series: [...uncertaintyBand, central],
  }
  return <section className="series-card evidence-series"><div className="series-heading"><div><span className="eyebrow">OBSERVED / MODELED CONTEXT</span><h2>{title}</h2><p>{subtitle}</p></div><span className="series-count">{monthlySummary ? '1 MONTHLY SUMMARY' : `${series.length.toLocaleString()} MONTHS`}</span></div><ChartView option={option} height={310}/><div className="series-note"><span>{source}</span><span>{hasUncertainty ? 'Shaded envelope shows the reported source uncertainty around each estimate.' : 'Values and dates retained at source support.'}</span></div></section>
}
function TimeSeriesChart({ station, observations }: { station: Station; observations: Observation[] }) {
  if (!observations.length) return <div className="empty-panel"><h2>No observations for this selection</h2><p>Inspect another measurement definition or station. Source records are not interpolated.</p></div>
  const first = observations[0]
  const option: EChartsOption = {
    animation: false,
    aria: { enabled: true },
    grid: { left: 76, right: 24, top: 32, bottom: 58 },
    tooltip: { trigger: 'axis', formatter: params => { const item = Array.isArray(params) ? params[0] : params; const point = item?.data as [string, number] | undefined; if (!point) return ''; const [date, value] = point; const record = observations.find(row => row.date === date && row.value === value); return `${date}<br/>${value} ${first.unit}<br/>${record?.parameter_description ?? ''}<br/>${record?.vertical_datum ?? 'Datum not recorded'}<br/>${record?.reading_type ?? 'Reading type not recorded'}<br/>${record?.method ? `Method: ${record.method}<br/>` : ''}${record?.qualifier ? `Remark/qualifier: ${record.qualifier}` : ''}` } },
    xAxis: { type: 'time', name: 'Observation date', nameLocation: 'middle', nameGap: 38, axisLabel: { color: '#8f9e98' }, axisLine: { lineStyle: { color: '#687773' } } },
    yAxis: { type: 'value', name: `${first.unit} · ${first.vertical_datum ?? 'datum not recorded'}`, nameLocation: 'middle', nameGap: 56, scale: true, axisLabel: { color: '#8f9e98' }, splitLine: { lineStyle: { color: '#33403e', type: 'dashed' } } },
    series: [{ type: 'line', name: first.parameter_description, data: observations.map(o => [o.date, o.value]), showSymbol: observations.length < 200, symbolSize: 5, connectNulls: false, lineStyle: { color: '#82c4ad', width: 2 }, itemStyle: { color: '#d7b36f' } }],
  }
  return <section className="series-card"><div className="series-heading"><div><span className="eyebrow">ARCHIVED MEASUREMENTS · NOT CURRENT CONDITIONS · {station.provider ?? 'USGS'} / {station.station_id}</span><h2>{first.parameter_description}</h2><p>Selected-definition observations: {observations[0].date} to {observations[observations.length - 1].date}. Reference / vertical datum: {first.vertical_datum ?? 'not stated in source'}.</p></div><span className="series-count">{observations.length.toLocaleString()} RECORDS</span></div><ChartView option={option} height={340}/><div className="series-note"><span>Source: {station.provider ?? 'USGS'} · site {station.station_id}</span><span>{first.reading_type ?? 'Reading type not recorded'} · {first.approval_status ?? 'approval state not recorded'}</span></div></section>
}
function FacilityDetail({ profile }: { profile: Profile }) { return <><span className="eyebrow amber">FACILITY PROFILE / {profile.status.toUpperCase()}</span><h2>{profile.facility_name}</h2><p className="detail-sub">{profile.operator} Â· {profile.city}, {profile.state}</p><dl><dt>Address</dt><dd>{profile.street_address}</dd><dt>Coordinates</dt><dd>{profile.latitude !== null ? `${profile.latitude}, ${profile.longitude}` : 'Not published / not verified'}</dd><dt>Verification</dt><dd>{profile.verification_status}</dd><dt>Status notes</dt><dd>{profile.confidence_notes}</dd><dt>Evidence dates</dt><dd>Source: {profile.publication_date ?? 'not dated in cited record'} · reviewed: {profile.accessed_date ?? 'date not recorded'}</dd></dl><div className="disclosure-box"><span className="eyebrow">WATER DISCLOSURE</span>{profile.water_disclosures.length ? profile.water_disclosures.map((d, i) => <p key={i}><b>{d.reported_quantity === null ? 'No verified site-specific withdrawal or consumption figure' : `${d.reported_quantity} ${d.original_unit ?? ''} reported ${d.metric_type}`}</b><br/>Water source: {d.water_source.replaceAll('_', ' ')} · Scope: {d.scope.replaceAll('_', ' ')}<br/>Reporting status: {d.actual_or_planned}{d.period_start || d.period_end ? ` · Period: ${d.period_start ?? 'start not given'} to ${d.period_end ?? 'end not given'}` : ''}<br/>{d.interpretation_notes}<br/><small>{d.page_section_table}</small></p>) : <p>Not publicly disclosed / no verified site-specific figure found in this register.</p>}</div><div className="evidence-links">{profile.evidence.map(e => <a key={e.source_url_or_path} href={e.source_url_or_path} target="_blank" rel="noreferrer">{e.source_title} â†—<small>{e.page_section_table} Â· {e.reliability}</small></a>)}</div></> }

export default App
