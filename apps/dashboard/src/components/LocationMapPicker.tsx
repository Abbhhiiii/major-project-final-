import { FormEvent, useEffect, useRef, useState } from 'react'
import L from 'leaflet'

import { reverseLocation, searchLocations } from '../api'
import type { GeoPlace } from '../types'

const DEFAULT_CENTER: L.LatLngExpression = [12.9716, 77.5946]

function placePin(map: L.Map, pin: { current: L.CircleMarker | null }, place: GeoPlace) {
  pin.current?.remove()
  pin.current = L.circleMarker([place.latitude, place.longitude], { radius: 8, color: '#0b3d78', weight: 3, fillColor: '#56c7ff', fillOpacity: 1 }).addTo(map)
  map.setView([place.latitude, place.longitude], 16)
}

export function LocationMapPicker({ value, onChange, name, compact = false }: { value: string; onChange: (location: string) => void; name?: string; compact?: boolean }) {
  const mapNode = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<L.Map | null>(null)
  const pin = useRef<L.CircleMarker | null>(null)
  const onChangeRef = useRef(onChange)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GeoPlace[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { onChangeRef.current = onChange }, [onChange])
  useEffect(() => {
    if (!mapNode.current || mapInstance.current) return
    const map = L.map(mapNode.current, { zoomControl: true }).setView(DEFAULT_CENTER, 12)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)
    map.on('click', async ({ latlng }: L.LeafletMouseEvent) => {
      setBusy(true); setError('')
      try {
        const place = await reverseLocation(latlng.lat, latlng.lng)
        placePin(map, pin, place); onChangeRef.current(place.display_name); setResults([])
      } catch (caught) { setError(caught instanceof Error ? caught.message : 'Map lookup failed') } finally { setBusy(false) }
    })
    mapInstance.current = map
    window.setTimeout(() => map.invalidateSize(), 0)
    return () => { map.remove(); mapInstance.current = null; pin.current = null }
  }, [])

  const search = async (event: FormEvent) => {
    event.preventDefault()
    if (query.trim().length < 2) return
    setBusy(true); setError('')
    try { setResults(await searchLocations(query)) } catch (caught) { setError(caught instanceof Error ? caught.message : 'Map search failed') } finally { setBusy(false) }
  }

  const choose = (place: GeoPlace) => {
    if (mapInstance.current) placePin(mapInstance.current, pin, place)
    onChange(place.display_name); setResults([]); setQuery(place.display_name)
  }

  return <div className={`location-picker ${compact ? 'compact' : ''}`}>
    {name && <input type="hidden" name={name} value={value} />}
    <form className="location-search" onSubmit={search}><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search camera location or landmark" aria-label="Search camera location" /><button disabled={busy || query.trim().length < 2}>{busy ? 'Locating…' : 'Search map'}</button></form>
    {results.length > 0 && <div className="location-results">{results.map(place => <button type="button" key={`${place.latitude}-${place.longitude}`} onClick={() => choose(place)}><strong>{place.display_name}</strong><small>{place.category} · {place.latitude.toFixed(4)}, {place.longitude.toFixed(4)}</small></button>)}</div>}
    <div ref={mapNode} className="location-map" aria-label="Interactive camera location map" />
    <div className="location-selection"><span>{busy ? 'Resolving map point…' : value ? 'Selected camera location' : 'Search or click the map to choose a location'}</span>{value && <strong>{value}</strong>}{error && <em>{error}</em>}</div>
  </div>
}
