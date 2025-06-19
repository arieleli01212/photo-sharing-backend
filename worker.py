# worker.py — face clustering with duplicate suppression
import os, time, pathlib, cv2, faiss, numpy as np, psycopg2
from insightface.app import FaceAnalysis
from psycopg2.extras import execute_values

# ─────────────────────  CONFIG  ─────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/metadata")
WATCH_DIR    = pathlib.Path(__file__).parent / "uploads"
scan_secs    = 2
thr, dup_thr = 0.45, 0.90         # cluster threshold, duplicate threshold

# ─────────────────────  GLOBALS  ────────────────────
DB          = psycopg2.connect(DATABASE_URL)
IDX         = faiss.IndexFlatIP(512)
PERSON_IDS  = []                  # Faiss row -> person_id

APP = FaceAnalysis(name="buffalo_l")
APP.prepare(ctx_id=0, det_size=(640, 640))   # CPU; set -1 for GPU

# ────────────────────  HELPERS  ─────────────────────
def new_person_id():
    cur = DB.cursor()
    cur.execute("SELECT COALESCE(MAX(person_id),0)+1 FROM faces")
    return cur.fetchone()[0]

def choose_cluster(vec: np.ndarray):
    """Return (person_id, is_duplicate)."""
    if IDX.ntotal == 0:
        return new_person_id(), False

    vec32 = np.expand_dims(vec.astype("float32"), 0)
    dists, idxs = IDX.search(vec32, 1)
    dist, idx = dists[0][0], idxs[0][0]

    if dist >= dup_thr:                      # identical face
        return PERSON_IDS[idx], True

    if dist > thr:                           # same person, new shot
        return PERSON_IDS[idx], False

    return new_person_id(), False            # brand-new person

def add_image(path: str):
    img = cv2.imread(path)
    if img is None:
        print("❌  cv2 failed", path); return

    faces = APP.get(img)
    if not faces:
        print("🤷‍♂️  no faces", path); return

    rows = []
    for f in faces:
        emb = f.embedding / np.linalg.norm(f.embedding)
        pid, dup = choose_cluster(emb)

        if dup:
            print("⏭️  duplicate skipped", pathlib.Path(path).name)
            continue

        rows.append((
            pid,
            str(path),
            [float(x) for x in emb],          # python floats
            [int(n) for n in f.bbox]          # plain ints
        ))

        IDX.add(np.expand_dims(emb.astype("float32"), 0))
        PERSON_IDS.append(pid)

    if not rows:
        return                                # all duplicates

    try:
        execute_values(
            DB.cursor(),
            "INSERT INTO faces (person_id,image_path,embedding,bbox) VALUES %s",
            rows
        )
        DB.commit()
        print(f"✅  inserted {len(rows)} new face(s) → person_ids {[r[0] for r in rows]}")
    except Exception as e:
        DB.rollback()
        print("❌  DB insert failed:", e)

# ────────────────────  WATCH LOOP  ──────────────────
def loop():
    seen = set()
    WATCH_DIR.mkdir(exist_ok=True)
    print("👂  watching", WATCH_DIR.resolve())

    while True:
        for p in WATCH_DIR.glob("*"):
            if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            if str(p) in seen:
                continue
            try:
                add_image(str(p))
                seen.add(str(p))
            except Exception as e:
                print("❌ in add_image", p, e)
        time.sleep(scan_secs)

if __name__ == "__main__":
    try:
        loop()
    finally:
        DB.close()
