const API_BASE="https://aroundyou-api-xi6n.onrender.com";
async function apiPost(path,body){const r=await fetch(API_BASE+path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});let d=null;try{d=await r.json()}catch{}if(!r.ok)throw new Error(typeof d?.detail==="string"?d.detail:`Request failed (${r.status})`);if(!d)throw new Error("Empty response");return d}
const money=n=>new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0}).format(Number(n||0));
const num=n=>new Intl.NumberFormat("en-IN",{maximumFractionDigits:0}).format(Number(n||0));
function esc(v){const e=document.createElement("div");e.textContent=String(v??"");return e.innerHTML}
