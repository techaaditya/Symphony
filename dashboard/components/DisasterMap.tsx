"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, Tooltip } from "react-leaflet";
import { intensityColor, useThemePalette } from "@/lib/colors";
import type { CasualtyReport, TrappedReport, WorldStatePayload } from "@/lib/types";

interface DisasterMapProps {
  worldState: WorldStatePayload | null;
}

function statusDivIcon(emoji: string, color: string): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<div style="display:flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:9999px;background:${color};border:2px solid #fff;font-size:12px;">${emoji}</div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

/** Nudges an overlay marker a short, fixed distance from its zone center so
 * casualty/trapped/tower markers don't stack exactly on top of the zone dot. */
function offset(lat: number, lng: number, dLat: number, dLng: number): [number, number] {
  return [lat + dLat, lng + dLng];
}

export default function DisasterMap({ worldState }: DisasterMapProps) {
  const palette = useThemePalette();

  if (!worldState) {
    return (
      <div className="flex h-[480px] items-center justify-center rounded-lg border border-border bg-surface-1 text-sm text-text-muted">
        Start a simulation to see the live map.
      </div>
    );
  }

  const zones = Object.values(worldState.zones);
  const center: [number, number] = zones.length
    ? [
        zones.reduce((sum, z) => sum + z.lat, 0) / zones.length,
        zones.reduce((sum, z) => sum + z.lng, 0) / zones.length,
      ]
    : [0, 0];

  const casualtiesByZone = groupBy(worldState.casualties, (c) => c.zone_id);
  const trappedByZone = groupBy(worldState.trapped, (t) => t.zone_id);
  const towersByZone = groupBy(Object.values(worldState.towers), (t) => t.zone_id);

  return (
    <div className="h-[480px] overflow-hidden rounded-lg border border-border">
      <MapContainer center={center} zoom={11} className="h-full w-full" scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {zones.map((zone) => (
          <CircleMarker
            key={zone.id}
            center={[zone.lat, zone.lng]}
            radius={10 + Math.sqrt(zone.population) / 20}
            pathOptions={{
              color: palette.gridline,
              fillColor: intensityColor(palette, zone.fire_intensity),
              fillOpacity: 0.85,
              weight: 1,
            }}
          >
            <Tooltip direction="top" permanent>
              {zone.name}
            </Tooltip>
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">{zone.name}</p>
                <p>Population: {zone.population.toLocaleString()}</p>
                <p>Fire intensity: {Math.round(zone.fire_intensity * 100)}%</p>
                <p>Road: {zone.road_status}</p>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {zones.flatMap((zone) =>
          untreated(casualtiesByZone[zone.id]).map((c, i) => (
            <Marker
              key={`casualty-${zone.id}-${i}`}
              position={offset(zone.lat, zone.lng, 0.01, 0.01 * (i + 1))}
              icon={statusDivIcon("🚑", palette.status[severityStatus(c.severity)])}
            >
              <Tooltip direction="right" permanent>
                {c.count} {c.severity} casualties
              </Tooltip>
            </Marker>
          )),
        )}

        {zones.flatMap((zone) =>
          unrescued(trappedByZone[zone.id]).map((t, i) => (
            <Marker
              key={`trapped-${zone.id}-${i}`}
              position={offset(zone.lat, zone.lng, -0.01, 0.01 * (i + 1))}
              icon={statusDivIcon("🧑‍🤝‍🧑", palette.status.warning)}
            >
              <Tooltip direction="left" permanent>
                {t.count} trapped (window ends tick {t.window_ends_tick})
              </Tooltip>
            </Marker>
          )),
        )}

        {zones.flatMap((zone) =>
          (towersByZone[zone.id] ?? []).map((tower) => (
            <Marker
              key={`tower-${tower.id}`}
              position={offset(zone.lat, zone.lng, 0.01, -0.01)}
              icon={statusDivIcon(
                "📡",
                tower.operational ? palette.status.good : palette.status.critical,
              )}
            >
              <Tooltip direction="bottom" permanent>
                Tower {tower.operational ? "operational" : "down"}
              </Tooltip>
            </Marker>
          )),
        )}
      </MapContainer>
    </div>
  );
}

function severityStatus(severity: CasualtyReport["severity"]): "good" | "warning" | "critical" {
  if (severity === "critical") return "critical";
  if (severity === "serious") return "warning";
  return "good";
}

function untreated(reports: CasualtyReport[] | undefined): CasualtyReport[] {
  return (reports ?? []).filter((c) => !c.treated);
}

function unrescued(reports: TrappedReport[] | undefined): TrappedReport[] {
  return (reports ?? []).filter((t) => !t.rescued);
}

function groupBy<T>(items: T[], keyOf: (item: T) => string): Record<string, T[]> {
  const groups: Record<string, T[]> = {};
  for (const item of items) {
    const key = keyOf(item);
    (groups[key] ??= []).push(item);
  }
  return groups;
}
