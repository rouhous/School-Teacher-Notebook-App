#!/usr/bin/env python3
"""Generate Noor 2.8.66 source ZIP from the tested 2.8.64 source archive.
This keeps the grade recognition fix and isolates SCORM navigation from preparation."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json, re, sys

directory = Path("addons/unified")
sources = sorted(directory.glob("*-v2.8.64-*-source.zip"))
if len(sources) != 1:
    sys.exit(f"Expected one 2.8.64 source archive, found {len(sources)}")
output = directory / "Noor-Unified-v2.8.66-ClassCard-source.zip"

def replace_exact(content, old, new, path):
    if content.count(old) != 1:
        sys.exit(f"Could not find unique patch anchor in {path}")
    return content.replace(old, new, 1)

with ZipFile(sources[0]) as original:
    files = {i.filename: original.read(i.filename) for i in original.infolist() if not i.is_dir()}
if any(p.startswith("META-INF/") for p in files):
    sys.exit("Refusing to use already signed source")
manifest = json.loads(files["manifest.json"])
if manifest["version"] != "2.8.64":
    sys.exit("Unexpected base version")
manifest["version"] = "2.8.66"
manifest["description"] = "Noor Unified 2.8.66: SCORM follows page three and Digital Library, never preparation."
files["manifest.json"] = (json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()

path = "noor-class-card.js"
s = files[path].decode()
s = replace_exact(s,
    "const cards=(root.NoorCourseCatalog?.cards?.()||[]).filter(c=>normalize(c.label)===normalize(course.label));",
    "const cards=(root.NoorCourseCatalog?.cards?.()||[]).filter(c=>normalize(c.label)===normalize(course.label));\n  // Use the verified course card, not the carousel page indicator, as grade evidence.",
    path)
files[path] = s.encode()

# Never reuse the preparation entry point as a fallback for SCORM card navigation.
# Only a proven popover/dropdown opener may open a course menu.
s = files["noor-class-card.js"].decode()
s = replace_exact(s,
    "return {element:card.querySelector('[data-toggle=\"popover\"],[data-bs-toggle=\"popover\"],[data-toggle=\"dropdown\"],[data-bs-toggle=\"dropdown\"],[aria-haspopup],button[type=\"button\"],[role=\"button\"]')||card,step:'open'};",
    "const opener=card.querySelector('[data-toggle=\"popover\"],[data-bs-toggle=\"popover\"],[data-toggle=\"dropdown\"],[data-bs-toggle=\"dropdown\"],[aria-haspopup=\"true\"]');\n  // A generic course-card button may lead to lesson preparation; never click it for SCORM.\n  return opener?{element:opener,step:'open'}:null;",
    "noor-class-card.js")
files["noor-class-card.js"] = s.encode()

path = "noor-scorm-publisher.js"
s = files[path].decode()
s = replace_exact(s,
    "if(!action||!visible(action))return false;",
    "if(!action||!visible(action))return false;\n  // The SCORM route is page 3 -> Digital Library, not lesson preparation.\n  if(/\\\\/teacher\\\\/courses\\\\/(?:preparations_index|add_preparation)/i.test(action.getAttribute('href')||action.closest('a')?.getAttribute('href')||''))return false;\n  if(/^(?:تحضير(?: الدروس)?|lesson preparation|preparations?)$/i.test(tidy(action.textContent||'')))return false;",
    path)
s = replace_exact(s,
    "if(!onUploadPage()&&pickNav(j))return;",
    "if(/\\\\/teacher\\\\/courses\\\\/(?:preparations_index|add_preparation)/i.test(location.pathname))throw Error('SCORM must use the third card page and Digital Library; preparation navigation is blocked.');\n    if(!onUploadPage()&&pickNav(j))return;",
    path)
files[path] = s.encode()

path = "noor-course-catalog.js"
s = files[path].decode()
anchor = "if(!s||s.length>210)return null;"
s = replace_exact(s,anchor,
    anchor+"\n  // Carousel page numbers and grade-span labels are not explicit grade identities.\n  if(/^\\d{1,3}$/.test(s)||/^\\(?\\d{1,2}\\s*[-–]\\s*\\d{1,2}\\)?$/.test(s))return null;",
    path)
s = replace_exact(s,
    "const grades=[...new Set(gradeLines.map(gradeOf))];",
    "const grades=[...new Set(gradeLines.map(gradeOf).filter(Number.isInteger))];",
    path)
files[path] = s.encode()

with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6) as dest:
    for path,data in files.items():
        dest.writestr(path,data)
print(f"Generated {output} ({output.stat().st_size} bytes)")
