"use client";

import { useEffect } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import { geoJSON } from "leaflet";
import type { FieldMapData } from "@/lib/field-types";

function FitFieldBounds({ data }: { data: FieldMapData }) {
  const map = useMap();

  useEffect(() => {
    const bounds = geoJSON(data).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 15 });
  }, [data, map]);

  return null;
}

export default function FieldMapView({
  data,
  lat,
  lon,
}: {
  data: FieldMapData;
  lat: number;
  lon: number;
}) {
  return (
    <MapContainer
      center={[lat, lon]}
      zoom={13}
      scrollWheelZoom={false}
      className="h-72 w-full rounded-2xl relative z-0 isolate"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <GeoJSON
        data={data}
        style={(feature) => ({
          color: feature?.properties?.flood_prone ? "#b42318" : "#047857",
          weight: 3,
          fillOpacity: 0.18,
        })}
      />
      <FitFieldBounds data={data} />
    </MapContainer>
  );
}
