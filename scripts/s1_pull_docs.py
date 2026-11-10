"""Session 1: download latest annual report and latest earnings-release exhibit per name."""
import json, sys
sys.path.insert(0, "src")
from nowcast import sec
SP = "/private/tmp/claude-501/-Users-david--claude-spares-spare-B5rNJE/8da16b4c-a381-4cf8-80db-388c65cae207/scratchpad/"
F = json.load(open(SP + "filings.json"))
CIKS = {"BKNG": 1075531, "EXPE": 1324424, "ABNB": 1559720, "UBER": 1543151,
        "LYFT": 1759509, "DASH": 1792789, "TCOM": 1269238}
mode = sys.argv[1]
if mode == "index":
    for t, d in F.items():
        filings = d["earnings"][:1] if t != "TCOM" else d["earnings"][:4]
        for f in filings:
            acc = f[2]
            body, _ = sec.fetch(sec.archive_index_url(CIKS[t], acc), "sec_filings", f"{t}_{acc}_index.json", ticker=t, accession=acc)
            items = json.loads(body)["directory"]["item"]
            print(t, acc, f[1], [(i["name"], i.get("size")) for i in items if i["name"].endswith((".htm", ".html"))])
elif mode == "get":
    t, acc, fn = sys.argv[2:5]
    sec.fetch(sec.archive_file_url(CIKS[t], acc, fn), "sec_filings", f"{t}_{acc}_{fn}", ticker=t, accession=acc, document=fn)
    print("ok", t, fn)
