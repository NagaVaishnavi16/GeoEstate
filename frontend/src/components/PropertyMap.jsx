import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";

function MapFocus({ property }) {
  const map = useMap();
  useEffect(() => {
    if (property?.latitude !== null && property?.longitude !== null) {
      map.flyTo([Number(property.latitude), Number(property.longitude)], Math.max(map.getZoom(), 13), { duration: 0.6 });
    }
  }, [map, property]);
  return null;
}

export function PropertyMap({ properties, selectedId, onSelect }) {
  const mappable = useMemo(
    () => properties.filter((property) => property.latitude !== null && property.longitude !== null),
    [properties],
  );
  const selected = mappable.find((property) => property.property_id === selectedId) ?? mappable[0];
  const center = selected ? [Number(selected.latitude), Number(selected.longitude)] : [17.385, 78.4867];

  return (
    <section className="map-panel" aria-label="Property map">
      <div className="map-header"><span>Map view</span><small>{mappable.length} mapped listings</small></div>
      <MapContainer center={center} zoom={12} scrollWheelZoom className="property-map">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapFocus property={selected} />
        {mappable.map((property) => (
          <CircleMarker
            key={property.property_id}
            center={[Number(property.latitude), Number(property.longitude)]}
            radius={property.property_id === selectedId ? 11 : 7}
            pathOptions={{ color: property.property_id === selectedId ? "#f4b44e" : "#0f5b45", fillColor: property.property_id === selectedId ? "#f4b44e" : "#2d9b78", fillOpacity: 0.95, weight: 2 }}
            eventHandlers={{ click: () => onSelect(property.property_id) }}
          >
            <Popup><strong>{property.title}</strong><br />{property.location}<br />₹{Number(property.price_lakh).toLocaleString("en-IN")} L</Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </section>
  );
}
