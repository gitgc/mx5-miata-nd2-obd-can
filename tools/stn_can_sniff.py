#!/usr/bin/env python3
"""Passive CAN capture + summary for STN11xx/STN21xx adapters (vLinker FS, OBDLink, ...).

The adapter is put in "monitor all" mode (STMA), so nothing is transmitted on the
car's bus. The serial link is bumped to 2 Mbaud first, otherwise a 115200 baud
link tops out around 400 frames/s and the ND bus runs at ~2400 frames/s.

    pip install pyserial
    python3 stn_can_sniff.py capture --port /dev/cu.usbserial-XXXX --seconds 30 --out cap.txt
    python3 stn_can_sniff.py summary cap.txt

Capture format: one frame per line, "<seconds> <3-hex-digit id><data hex>".
NOTE: ID 0x40A multiplexes the VIN as ASCII. Scrub it before sharing captures.
"""
import argparse
import collections
import sys
import time

FAST_BAUD = 2000000


def _cmd(s, c, wait=1.5):
    s.reset_input_buffer()
    s.write((c + "\r").encode())
    buf, t0 = b"", time.time()
    while time.time() - t0 < wait:
        buf += s.read(4096)
        if buf.endswith(b">"):
            break
    return buf.decode(errors="replace").replace("\r", "\n").strip("> \n")


def _connect(port):
    import serial

    for baud in (FAST_BAUD, 115200, 38400):
        s = serial.Serial(port, baud, timeout=0.2)
        s.write(b"\r\r")
        time.sleep(0.2)
        s.reset_input_buffer()
        if "ELM" in _cmd(s, "ATI", 1.0):
            if baud != FAST_BAUD:
                s.write(f"STSBR {FAST_BAUD}\r".encode())
                time.sleep(0.3)
                s.close()
                s = serial.Serial(port, FAST_BAUD, timeout=0.2)
                s.write(b"\r")
                time.sleep(0.2)
                s.reset_input_buffer()
                if "ELM" not in _cmd(s, "ATI", 1.0):
                    sys.exit("adapter did not come back at 2 Mbaud")
            return s
        s.close()
    sys.exit("no ELM/STN adapter answering on " + port)


def capture(args):
    s = _connect(args.port)
    print("adapter:", _cmd(s, "STDI"), "/", _cmd(s, "STI"), file=sys.stderr)
    # ATSP6 = ISO 15765-4 CAN 11-bit 500k; ATCAF0 = raw frames; STFAC = clear filters
    for c in ["ATE0", "ATL0", "ATS0", "ATH1", "ATSP6", "ATCAF0", "ATAL", "STCSEGR0", "STFAC"]:
        _cmd(s, c, 1.0)
    s.timeout = 0.05
    s.write(b"STMA\r")
    t0, n, buf = time.time(), 0, b""
    with open(args.out, "w") as fh:
        while time.time() - t0 < args.seconds:
            buf += s.read(65536)
            *lines, buf = buf.split(b"\r")
            now = time.time() - t0
            for ln in lines:
                ln = ln.strip().decode(errors="replace")
                if ln and ln != ">":
                    fh.write(f"{now:.4f} {ln}\n")
                    n += 1
    s.write(b"\r")  # any byte stops STMA
    time.sleep(0.2)
    # Restore filters so OBD requests work again without a power cycle.
    s.timeout = 0.2
    _cmd(s, "ATZ", 2.0)
    print(f"{n} frames, {n / args.seconds:.0f}/s -> {args.out}", file=sys.stderr)


def load(path):
    for ln in open(path):
        parts = ln.split()
        if len(parts) != 2 or len(parts[1]) < 3:
            continue
        try:
            yield float(parts[0]), int(parts[1][:3], 16), bytes.fromhex(parts[1][3:])
        except ValueError:
            continue


def summary(args):
    by, t_first, t_last = collections.defaultdict(list), None, 0.0
    for t, cid, data in load(args.capture):
        t_first = t if t_first is None else t_first
        t_last = t
        by[cid].append(data)
    dur = max(t_last - (t_first or 0), 1e-9)
    print(f"{sum(map(len, by.values()))} frames over {dur:.1f}s, {len(by)} IDs")
    print("bytes: constant value, or [min-max:distinct-count] when they change")
    for cid in sorted(by):
        frames = by[cid]
        dlc = collections.Counter(map(len, frames)).most_common(1)[0][0]
        cols = []
        for i in range(dlc):
            vals = [d[i] for d in frames if len(d) > i]
            uniq = set(vals)
            cols.append(f"{vals[-1]:02X}" if len(uniq) == 1 else f"[{min(vals):02X}-{max(vals):02X}:{len(uniq)}]")
        print(f"0x{cid:03X} ({cid:4d}) {len(frames) / dur:6.1f}Hz  " + " ".join(cols))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture", help="record raw CAN frames")
    c.add_argument("--port", required=True, help="serial device, e.g. /dev/cu.usbserial-XXXX or COM5")
    c.add_argument("--seconds", type=float, default=30)
    c.add_argument("--out", default="capture.txt")
    c.set_defaults(fn=capture)
    m = sub.add_parser("summary", help="per-ID rate and byte activity of a capture")
    m.add_argument("capture")
    m.set_defaults(fn=summary)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
