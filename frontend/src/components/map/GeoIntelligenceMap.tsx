'use client';

import { useEffect, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Circle,
  Polyline,
  Popup,
  LayersControl,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useMilitaryBases } from '@/hooks/useMilitaryData';
import { useArmsTransfers } from '@/hooks/useMilitaryData';
import { useDefenseBudgets } from '@/hooks/useMilitaryData';
import type { MilitaryBase, ArmsTransfer, DefenseBudget } from '@/lib/types';

const { BaseLayer, Overlay } = LayersControl;

const BASE_COLORS: Record<string, string> = {
  air: '#3b82f6',
  naval: '#06b6d4',
  army: '#84cc16',
  special: '#a855f7',
  intelligence: '#f59e0b',
  logistics: '#6b7280',
};

function createBaseIcon(type: string) {
  const color = BASE_COLORS[type.toLowerCase()] ?? '#3b82f6';
  return L.divIcon({
    className: 'geo-intel-marker',
    html: `<div style="
      width:14px;height:14px;border-radius:50%;
      background:${color};
      border:2px solid rgba(255,255,255,0.3);
      box-shadow:0 0 8px ${color}80;
    "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

function BasePopup({ base }: { base: MilitaryBase }) {
  return (
    <div className="text-xs font-mono text-neutral-200 space-y-1 min-w-[180px]">
      <p className="font-bold text-sm text-white">{base.name}</p>
      <p className="text-neutral-400">Country: {base.country}</p>
      <p className="text-neutral-400">Type: <span className="text-blue-400 uppercase">{base.type}</span></p>
      {base.personnel_count != null && (
        <p className="text-neutral-400">Personnel: {base.personnel_count.toLocaleString()}</p>
      )}
      {base.status && (
        <p className="text-neutral-400">Status: <span className="text-emerald-400">{base.status}</span></p>
      )}
      {base.is_foreign && (
        <p className="text-amber-400 text-[10px] tracking-widest uppercase mt-1">Foreign Installation</p>
      )}
    </div>
  );
}

function TransferPopup({ transfer }: { transfer: ArmsTransfer }) {
  return (
    <div className="text-xs font-mono text-neutral-200 space-y-1 min-w-[200px]">
      <p className="font-bold text-sm text-white">{transfer.weapon_system}</p>
      <p className="text-neutral-400">
        {transfer.supplier_country} → {transfer.recipient_country}
      </p>
      <p className="text-neutral-400">Year: {transfer.year}</p>
      {transfer.value_usd != null && (
        <p className="text-neutral-400">
          Value: <span className="text-emerald-400">${(transfer.value_usd / 1e6).toFixed(1)}M</span>
        </p>
      )}
      <p className="text-neutral-400">Status: <span className="text-blue-400">{transfer.status}</span></p>
    </div>
  );
}

function BudgetPopup({ budget }: { budget: DefenseBudget }) {
  return (
    <div className="text-xs font-mono text-neutral-200 space-y-1 min-w-[160px]">
      <p className="font-bold text-sm text-white">{budget.country}</p>
      <p className="text-neutral-400">Year: {budget.year}</p>
      <p className="text-neutral-400">
        Budget: <span className="text-emerald-400">${(budget.budget_usd / 1e9).toFixed(1)}B</span>
      </p>
      {budget.gdp_percentage != null && (
        <p className="text-neutral-400">GDP: {budget.gdp_percentage.toFixed(2)}%</p>
      )}
    </div>
  );
}

const BUDGET_MARKER_POSITIONS: Record<string, [number, number]> = {
  'United States': [38.9, -77.0],
  'Russia': [55.75, 37.62],
  'China': [39.9, 116.4],
  'United Kingdom': [51.5, -0.13],
  'France': [48.86, 2.35],
  'India': [28.61, 77.21],
  'Germany': [52.52, 13.41],
  'Japan': [35.68, 139.69],
  'South Korea': [37.57, 126.98],
  'Brazil': [-15.79, -47.88],
  'Saudi Arabia': [24.71, 46.67],
  'Australia': [-35.28, 149.13],
  'Israel': [31.77, 35.23],
  'Turkey': [39.93, 32.86],
  'Italy': [41.9, 12.5],
};

export function GeoIntelligenceMap() {
  const mapRef = useRef<L.Map>(null);
  const { data: bases } = useMilitaryBases();
  const { data: transfers } = useArmsTransfers();
  const { data: budgets } = useDefenseBudgets();

  useEffect(() => {
    if (mapRef.current) {
      const map = mapRef.current;
      const style = document.createElement('style');
      style.textContent = `
        .leaflet-container { background: #0a0a0a !important; }
        .leaflet-popup-content-wrapper {
          background: #171717 !important;
          border: 1px solid #404040 !important;
          border-radius: 6px !important;
          box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
        }
        .leaflet-popup-tip { background: #171717 !important; border: 1px solid #404040 !important; }
        .leaflet-popup-close-button { color: #a3a3a3 !important; }
        .leaflet-control-layers {
          background: #171717 !important;
          border: 1px solid #404040 !important;
          color: #d4d4d4 !important;
        }
        .leaflet-control-zoom a {
          background: #171717 !important;
          color: #d4d4d4 !important;
          border-color: #404040 !important;
        }
      `;
      map.getContainer().appendChild(style);
    }
  }, []);

  const transferLines: Array<{ positions: [[number, number], [number, number]]; transfer: ArmsTransfer }> =
    (transfers ?? [])
      .filter((t) => t.lat_supplier != null && t.lng_supplier != null && t.lat_recipient != null && t.lng_recipient != null)
      .map((t) => ({
        positions: [[t.lat_supplier!, t.lng_supplier!], [t.lat_recipient!, t.lng_recipient!]] as [[number, number], [number, number]],
        transfer: t,
      }));

  return (
    <div className="w-full h-full rounded-lg overflow-hidden border border-neutral-800">
      <MapContainer
        ref={mapRef}
        center={[20, 0]}
        zoom={2}
        minZoom={2}
        maxZoom={12}
        className="w-full h-full"
        zoomControl={true}
        scrollWheelZoom={true}
      >
        <LayersControl position="topright">
          <BaseLayer checked name="Dark Map">
            <TileLayer
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
          </BaseLayer>

        <Overlay checked name="Military Bases">
          {(bases ?? []).map((base) => (
            <Marker
              key={base.id}
              position={[base.lat, base.lng]}
              icon={createBaseIcon(base.type)}
            >
              <Popup>
                <BasePopup base={base} />
              </Popup>
            </Marker>
          ))}
        </Overlay>

        <Overlay checked name="Conflict Zones">
          {(transfers ?? [])
            .filter((t) => t.lat_recipient != null && t.lng_recipient != null)
            .map((t) => (
              <Circle
                key={t.id}
                center={[t.lat_recipient!, t.lng_recipient!]}
                radius={80000}
                pathOptions={{
                  color: '#ef4444',
                  fillColor: '#ef4444',
                  fillOpacity: 0.15,
                  weight: 1,
                }}
              />
            ))}
        </Overlay>

        <Overlay checked name="Arms Transfers">
          {transferLines.map((line) => (
            <Polyline
              key={line.transfer.id}
              positions={line.positions}
              pathOptions={{
                color: '#3b82f6',
                weight: 2,
                opacity: 0.6,
                dashArray: '6 4',
              }}
            >
              <Popup>
                <TransferPopup transfer={line.transfer} />
              </Popup>
            </Polyline>
          ))}
        </Overlay>

        <Overlay name="Defense Budgets">
          {(budgets ?? []).map((b) => {
            const pos = BUDGET_MARKER_POSITIONS[b.country];
            if (!pos) return null;
            const radius = Math.max(50000, Math.sqrt(b.budget_usd / 1e9) * 30000);
            return (
              <Circle
                key={b.id}
                center={pos}
                radius={radius}
                pathOptions={{
                  color: '#10b981',
                  fillColor: '#10b981',
                  fillOpacity: 0.2,
                  weight: 1,
                }}
              >
                <Popup>
                  <BudgetPopup budget={b} />
                </Popup>
              </Circle>
            );
          })}
        </Overlay>
        </LayersControl>
      </MapContainer>
    </div>
  );
}
