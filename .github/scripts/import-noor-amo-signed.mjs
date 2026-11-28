// Retrieve an already-approved Mozilla XPI; never re-upload a duplicate version.
// Credentials are passed only as GitHub Actions secrets (never logged or committed).
import { createHmac, createHash, randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve, basename } from "node:path";

const VERSION=process.env.RELEASE_VERSION || "2.8.26";
const ID="noor-prep-filler-private-2026@rouhous.github.io";
const KEY=process.env.AMO_JWT_ISSUER;
const SECRET=process.env.AMO_JWT_SECRET;
if(!/^\d+\.\d+\.\d+$/.test(VERSION)) throw Error("Invalid version");
if(!KEY||!SECRET) throw Error("AMO_JWT_ISSUER and AMO_JWT_SECRET must be configured in GitHub Actions secrets.");

const base64url=data=>Buffer.from(typeof data==="string"?data:JSON.stringify(data)).toString("base64url");
function jwt(){
 const now=Math.floor(Date.now()/1000);
 const data=base64url({alg:"HS256",typ:"JWT"})+"."+base64url({iss:KEY,jti:randomUUID(),iat:now,exp:now+60});
 return data+"."+createHmac("sha256",SECRET).update(data).digest("base64url");
}
const auth=()=>({Authorization:"JWT "+jwt(),Accept:"application/json"});
const endpoint="https://addons.mozilla.org/api/v5/addons/addon/"+encodeURIComponent(ID)+"/versions/"+encodeURIComponent(VERSION)+"/";
const infoResponse=await fetch(endpoint,{headers:auth(),signal:AbortSignal.timeout(30000)});
if(!infoResponse.ok)throw Error("Mozilla API version lookup failed: HTTP "+infoResponse.status+" (verify API ownership, signing completion, and extension ID)");
const version=await infoResponse.json();
if(version.version!==VERSION)throw Error("Mozilla returned an unexpected version");
if(version.channel!=="unlisted")throw Error("Only the unlisted self-distribution version can be imported");
const file=Array.isArray(version.file)?version.file.find(f=>f?.status==="public"&&f?.url):version.file;
if(!file||file.status!=="public"||typeof file.url!=="string")throw Error("Mozilla has not approved the signed XPI for this version yet");
const expected=typeof file.hash==="string" && /^sha256:[0-9a-fA-F]{64}$/.test(file.hash)?file.hash.slice(7).toLowerCase():null;
if(!expected)throw Error("Mozilla did not supply a verifiable SHA-256 signature/hash for the signed file");
function safeURL(raw){
 const u=new URL(raw);
 if(u.protocol!=="https:"||!(u.hostname==="addons.mozilla.org"||u.hostname.endsWith(".mozilla.org")||u.hostname.endsWith(".mozilla.net")))throw Error("Unexpected signed-download host from Mozilla");
 return u;
}
let url=safeURL(file.url);
let response;
for(let redirects=0;redirects<5;redirects++){
 response=await fetch(url,{headers:url.hostname==="addons.mozilla.org"?{Authorization:"JWT "+jwt()}:undefined,redirect:"manual",signal:AbortSignal.timeout(60000)});
 if([301,302,303,307,308].includes(response.status)){
  const next=response.headers.get("location");
  if(!next)throw Error("Mozilla download redirect lacked a location");
  url=safeURL(new URL(next,url).href);
  continue;
 }
 break;
}
if(!response?.ok)throw Error("Mozilla XPI download failed: HTTP "+response?.status);
const xpi=Buffer.from(await response.arrayBuffer());
if(xpi.length<15000||xpi.length>30000000)throw Error("Signed XPI has unexpected size");
if(xpi[0]!==0x50||xpi[1]!==0x4b)throw Error("Mozilla returned a non-ZIP file");
const actual=createHash("sha256").update(xpi).digest("hex");
if(actual!==expected)throw Error("Downloaded XPI SHA-256 does not match Mozilla");
const outputDir=process.env.SIGNED_XPI_DIR || "addons/files";
const filename="Noor-Unified-v"+VERSION+"-signed.xpi";
const filePath=resolve(outputDir,filename);
await mkdir(resolve(outputDir),{recursive:true});
await writeFile(filePath,xpi);
console.log("Verified and saved Mozilla-approved signed XPI version",VERSION,"bytes",xpi.length,"SHA-256",actual);
