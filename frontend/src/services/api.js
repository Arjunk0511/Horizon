import axios from 'axios';
export const api=axios.create({baseURL:import.meta.env.VITE_API_BASE_URL||'/api',timeout:120000});
api.interceptors.request.use(config=>{const token=sessionStorage.getItem('horizon_token');if(token)config.headers.Authorization=`Bearer ${token}`;return config;});
export function errorText(e){const d=e.response?.data?.detail;return Array.isArray(d)?d.map(x=>`${x.loc.at(-1)}: ${x.msg}`).join('; '):typeof d==='string'?d:e.message||'Request failed';}
export async function downloadReport(id,format){const r=await api.get(`/voyages/${id}/report`,{params:{format},responseType:'blob'});const url=URL.createObjectURL(r.data);const a=document.createElement('a');a.href=url;a.download=`horizon-voyage-${id}.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
