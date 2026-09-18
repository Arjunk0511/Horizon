import {useEffect,useState} from 'react';
import {MapContainer,TileLayer,GeoJSON,Polyline,Circle,CircleMarker,Popup,useMap} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
function Fit({points}){const map=useMap();const key=JSON.stringify(points);useEffect(()=>{const fit=()=>{map.invalidateSize();if(points?.length>1)map.fitBounds(points,{padding:[35,35],animate:false});};fit();const observer=new ResizeObserver(fit);observer.observe(map.getContainer());return()=>observer.disconnect();},[key,map]);return null;}
const colors={LOW:'#3ab99c',MEDIUM:'#e5bc51',HIGH:'#ed8847',CRITICAL:'#f36470'};
export default function RouteMap({land,ports=[],voyage,position,historyRoute}){
 const [online,setOnline]=useState(false);const route=voyage?.optimized;const points=route?.points;
 return <div className="map-wrap"><MapContainer center={[12,77]} zoom={4} scrollWheelZoom className="map" attributionControl>
  {online&&<TileLayer attribution='© OpenStreetMap contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"/>}
  {land&&<GeoJSON data={land} style={{fillColor:'#c7d9d9',color:'#a7c2c2',weight:1,fillOpacity:online?.45:1}} attribution="Natural Earth (public domain)"/>}
  {ports.map(p=><CircleMarker key={p.id} center={[p.latitude,p.longitude]} radius={voyage&&(p.id===voyage.source_id||p.id===voyage.destination_id)?7:4} pathOptions={{color:'#16364c',fillColor:'#fff',fillOpacity:1,weight:2}}><Popup><b>{p.name}</b><br/>{p.country}<br/>Port display marker. Routes start/end offshore.</Popup></CircleMarker>)}
  {voyage?.baseline&&<Polyline positions={voyage.baseline.points} pathOptions={{color:'#e69843',weight:3,dashArray:'8 7'}}><Popup>Baseline · {voyage.baseline.distance.toFixed(1)} km<br/>Weather safe: {voyage.baseline.safe?'Yes':'No'}</Popup></Polyline>}
  {points&&<Polyline positions={points} pathOptions={{color:'#007f91',weight:4}}><Popup>Weather-aware optimized route</Popup></Polyline>}
  {historyRoute&&<Polyline positions={historyRoute.data.points} pathOptions={{color:'#9e55c5',weight:3,dashArray:'4 6'}}><Popup>Historical {historyRoute.kind} version {historyRoute.version}</Popup></Polyline>}
  {(route?.hazards||[]).concat(voyage?.hazards||[]).filter((h,i,arr)=>arr.findIndex(x=>x.latitude===h.latitude&&x.longitude===h.longitude)===i).map((h,i)=><Circle key={i} center={[h.latitude,h.longitude]} radius={h.radius_km*1000} pathOptions={{color:'#e85f69',weight:1,fillOpacity:.15}}><Popup><b>{h.name}</b><br/>Demo storm footprint<br/>Peak waves {h.wave_height} m · wind {h.wind_speed} m/s<br/>Actual safety contour depends on vessel limits.</Popup></Circle>)}
  {route?.segments.filter((_,i)=>i%Math.max(1,Math.ceil(route.segments.length/25))===0).map((s,i)=><CircleMarker key={i} center={[s.weather.latitude,s.weather.longitude]} radius={3} pathOptions={{color:colors[s.level],fillOpacity:1,weight:1}}><Popup><b>{s.level} weather exposure</b><br/>{s.weather.latitude.toFixed(3)}, {s.weather.longitude.toFixed(3)}<br/>Waves {s.weather.wave_height.toFixed(2)} m<br/>Wind {s.weather.wind_speed.toFixed(2)} m/s<br/>Risk {s.risk.toFixed(2)}<br/>{s.weather.source}<br/>{s.weather.timestamp}</Popup></CircleMarker>)}
  {position&&<CircleMarker center={[position.latitude,position.longitude]} radius={9} pathOptions={{color:'#fff',fillColor:'#0a465d',fillOpacity:1,weight:3}}><Popup>Vessel · {position.mode}<br/>{position.speed_over_ground.toFixed(1)} kn<br/>Course {position.course_over_ground.toFixed(0)}°</Popup></CircleMarker>}
  <Fit points={points}/>
 </MapContainer><div className="map-tools"><label><input type="checkbox" checked={online} onChange={e=>setOnline(e.target.checked)}/> Online OSM tiles</label><span>Bundled coastline available offline</span></div><div className="legend"><span><i className="line amber"/>Baseline</span><span><i className="line teal"/>Optimized</span>{Object.entries(colors).map(([k,v])=><span key={k}><i style={{background:v}}/>{k.toLowerCase()}</span>)}</div></div>;
}
