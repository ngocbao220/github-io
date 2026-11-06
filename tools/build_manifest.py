#!/usr/bin/env python3
"""Tạo danh sách mẫu gán nhãn từ file chép lời + file turn-event tự gán.

Đầu vào (cùng tên gốc, ví dụ 10154_2):
  10154_2.wav, 10154_2_transcript.txt  ("bắt đầu<TAB>kết thúc<TAB>SPEAKER_xx: lời")
  10154_2_turnevent.txt                ("bắt đầu<TAB>kết thúc<TAB>EoT|MoT|FI|BC|INT")
Chạy:  python3 build_manifest.py 10154_2 [--dir .] [--pre 12] [--post 3] [--clips out_dir]
Mỗi sự kiện là một mẫu: người dùng là người phát sinh sự kiện (đảo vai tự nhiên theo từng sự kiện).
Các trường có đuôi _auto lấy tự động, người gán nhãn chỉ kiểm tra.
"""
import argparse, json, os, re, subprocess, sys

MAP = {"EoT": "EOT", "MoT": "MOT", "FI": "MOT", "BC": "BC", "INT": "INT"}


def spk(s):
    return re.sub(r"_+", "_", s.strip())


def load_tr(p):
    out = []
    for l in open(p, encoding="utf8"):
        l = l.rstrip("\n")
        if not l.strip():
            continue
        a, b, rest = l.split("\t", 2)
        s, txt = rest.split(":", 1)
        out.append({"s": float(a), "e": float(b), "spk": spk(s), "text": txt.strip()})
    return out


def load_ev(p):
    return [(float(a), float(b), c) for a, b, c in (l.split() for l in open(p, encoding="utf8") if l.strip())]


def owner(ev, tr):
    """Người phát sinh sự kiện và đoạn lời liên quan."""
    s, e, c = ev
    if c in ("BC", "INT"):
        cand = [t for t in tr if abs(t["s"] - s) < 0.02]       # đoạn của người bắt đầu nói đúng lúc đó
        if cand:
            return cand[0]
    if c == "FI":
        cand = [t for t in tr if abs(t["s"] - s) < 0.02]
        if cand:
            return cand[0]
    prev = [t for t in tr if t["e"] <= s + 0.02]
    if c in ("EoT", "MoT"):
        cand = [t for t in tr if t["s"] - 0.02 <= s <= t["e"] + 0.02]  # đoạn kết thúc đúng lúc đó
        cand = [t for t in cand if abs(t["e"] - s) < 0.02] or cand
        if cand:
            return cand[-1]
    return prev[-1] if prev else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--dir", default=".")
    ap.add_argument("--pre", type=float, default=12.0, help="giây ngữ cảnh trước sự kiện")
    ap.add_argument("--post", type=float, default=3.0, help="giây giữ lại sau sự kiện")
    ap.add_argument("--clips", help="thư mục xuất clip wav (cần ffmpeg)")
    a = ap.parse_args()
    d = a.dir
    tr = load_tr(os.path.join(d, a.name + "_transcript.txt"))
    evs = load_ev(os.path.join(d, a.name + "_turnevent.txt"))
    dur = max(t["e"] for t in tr)
    rows = []
    for i, ev in enumerate(evs):
        s, e, c = ev
        seg = owner(ev, tr)
        if seg is None:
            continue
        user = seg["spk"]
        end = max(e, seg["e"]) if c in ("EoT", "MoT") else e
        nxt = [t for t in tr if t["s"] >= end - 0.05 and t is not seg]
        nxt = nxt[0] if nxt else None
        if c in ("BC",):
            nxt_spk = "OTHER"            # tiếng đệm: bên kia giữ lời
        elif nxt is None:
            nxt_spk = None
        else:
            nxt_spk = "SAME" if nxt["spk"] == user else "OTHER"
        ovl = any(t["spk"] != user and t["s"] < end and t["e"] > s for t in tr)
        gap = round(nxt["s"] - end, 2) if nxt and nxt["s"] >= end else 0.0
        t0 = max(0.0, s - a.pre)
        t1 = min(dur, end + a.post)
        rows.append({
            "conversation_id": a.name, "event_id": f"{a.name}_{i:03d}",
            "user": user, "event_auto": MAP[c], "event_raw": c,
            "t_event_start": round(s, 3), "t_event_end": round(end, 3),
            "clip": [round(t0, 3), round(t1, 3)],
            "marks_auto": {"turn_end_sec": round(end - t0, 3)},
            "user_text": seg["text"],
            "next_auto": nxt_spk, "overlap_auto": ovl, "gap_after_sec_auto": gap,
        })
        if a.clips:
            os.makedirs(a.clips, exist_ok=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t0), "-to", str(t1),
                            "-i", os.path.join(d, a.name + ".wav"), "-ac", "1", "-ar", "16000",
                            os.path.join(a.clips, rows[-1]["event_id"] + ".wav")], check=True)
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
