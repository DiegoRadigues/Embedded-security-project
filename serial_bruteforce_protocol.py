#!/usr/bin/env python3
"""
Bruteforce interactif amélioré :
- attend le prompt avant d'envoyer
- peut reset la carte via DTR avant chaque essai
- essaye deux modes d'envoi (char-by-char puis line) si nécessaire
- n'arrête que sur ACCESS GRANTED ou labels 'Here is your salt:'/'Here is your hash:'
"""
import serial, time, os, sys, binascii, base64

# ---------- CONFIG ----------
PORT = "/dev/ttyUSB0"
BAUD = 9600                # adapte à 115200 si besoin
WORDLIST = os.path.expanduser("~/Téléchargements/candidates_f.txt")
OUTDIR = os.path.expanduser("~/Téléchargements/bruteforce_protocol_tries")
CHAR_DELAY = 0.06          # délai entre caractères en mode char
READ_WAIT = 2.0            # lecture après envoi
INTER_TRY_DELAY = 0.2
RESET_BEFORE_TRY = True    # toggle DTR reset avant chaque essai
WAIT_FOR_PROMPT = True     # attendre un prompt avant d'envoyer
PROMPTS = [b"Enter password:", b"Character from password:", b"No input. Enter password:"]
SUCCESS_MARKERS = [b"ACCESS GRANTED", b"Here is your salt:", b"Here is your hash:"]
IGNORE_MARKERS = [b"ACCESS DENIED"]
# try modes in this order for each candidate
TRY_MODES = ["char","line"]  # "char" = char-by-char ; "line" = whole line at once
# ----------------------------

os.makedirs(OUTDIR, exist_ok=True)

def read_until(ser, timeout=1.0):
    buf = bytearray(); t0 = time.time()
    while time.time()-t0 < timeout:
        d = ser.read(4096)
        if d:
            buf.extend(d)
        else:
            time.sleep(0.01)
    return bytes(buf)

def wait_prompt(ser, timeout=3.0):
    """Attend l'apparition d'un prompt dans PROMPTS; retourne True si trouvé."""
    t0 = time.time()
    buf = bytearray()
    while time.time()-t0 < timeout:
        d = ser.read(4096)
        if d:
            buf.extend(d)
            for p in PROMPTS:
                if p in buf:
                    return True, bytes(buf)
        else:
            time.sleep(0.02)
    return False, bytes(buf)

def extract_labels(buf):
    """Retourne (salt_bytes or None, hash_bytes or None) si trouvés."""
    salt = None; h = None
    if b"Here is your salt:" in buf and b"Here is your hash:" in buf:
        i = buf.find(b"Here is your salt:")
        j = buf.find(b"Here is your hash:", i+1)
        if i!=-1 and j!=-1:
            salt = buf[i+len(b"Here is your salt:"):j]
            # trim common control bytes
            salt = salt.strip(b"\r\n\0 ")
            # hash after j
            k = j+len(b"Here is your hash:")
            # find end by ACCESS GRANTED/DENIED or CRLF
            end = len(buf)
            for mk in (b"ACCESS GRANTED", b"ACCESS DENIED", b"\r\n", b"\n"):
                pos = buf.find(mk, k)
                if pos!=-1 and pos < end:
                    end = pos
            h = buf[k:k+ (end-k)]
            h = h.strip(b"\r\n\0 ")
    return salt, h

def do_reset(ser):
    """Tente toggle DTR pour reset."""
    try:
        ser.dtr = False; time.sleep(0.05)
        ser.dtr = True; time.sleep(0.05)
    except Exception:
        pass

def try_mode(ser, candidate, mode):
    """Envoie candidate en mode 'char' ou 'line', retourne (marker, success_bool, resp)."""
    # clear buffers
    try:
        ser.reset_input_buffer(); ser.reset_output_buffer()
    except Exception:
        pass

    # Optionnel : poke CRLF to trigger prompt
    # ser.write(b"\r\n"); time.sleep(0.08)

    if mode == "char":
        for ch in candidate:
            ser.write(ch.encode(errors='ignore'))
            time.sleep(CHAR_DELAY)
        ser.write(b"\r\n")
    else:
        ser.write((candidate + "\r\n").encode())
    # read response
    resp = read_until(ser, READ_WAIT)
    # determine marker
    for m in SUCCESS_MARKERS:
        if m in resp:
            return m, m in (b"ACCESS GRANTED", b"Here is your salt:", b"Here is your hash:"), resp
    for m in IGNORE_MARKERS:
        if m in resp:
            return m, False, resp
    return None, False, resp

def save_resp(candidate, idx, mode, resp):
    safe = "".join(c if c.isalnum() or c in "-_.@" else "_" for c in candidate)[:40]
    fn = os.path.join(OUTDIR, f"try_{idx:04d}_{safe}_{mode}_{int(time.time())}.bin")
    open(fn,"wb").write(resp)
    return fn

def main():
    if not os.path.exists(WORDLIST):
        print("Wordlist missing:", WORDLIST); sys.exit(1)
    with open(WORDLIST,"r",encoding="utf-8",errors="ignore") as f:
        words = [w.strip() for w in f if w.strip()]
    print("[+] Opening", PORT, "baud", BAUD, "tries:", len(words))
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.05)
    except Exception as e:
        print("ERROR open port:", e); sys.exit(1)

    try:
        for i,w in enumerate(words,1):
            print(f"[{i}/{len(words)}] Candidate='{w}'")
            # Optionnel reset before try
            if RESET_BEFORE_TRY:
                do_reset(ser)
                time.sleep(0.12)
            # wait for prompt if requested
            if WAIT_FOR_PROMPT:
                got, pre = wait_prompt(ser, timeout=2.0)
                print("  - prompt seen:", got)
                if not got:
                    # try small poke and wait again
                    ser.write(b"\r\n"); time.sleep(0.08)
                    got, pre = wait_prompt(ser, timeout=1.0)
                    print("  - prompt after poke:", got)
            # try modes
            for mode in TRY_MODES:
                print("   -> trying mode:", mode)
                marker, ok, resp = try_mode(ser, w, mode)
                fn = save_resp(w, i, mode, resp)
                if marker:
                    print("     marker:", marker.decode(errors='ignore'))
                else:
                    print("     no marker")
                if ok:
                    print("=== SUCCESS for", w, "mode", mode, "file:", fn)
                    # extract salt/hash if present
                    s,h = extract_labels(resp)
                    if s:
                        print("SALT hex:", binascii.hexlify(s).decode())
                        print("SALT b64:", base64.b64encode(s).decode())
                    if h:
                        print("HASH hex:", binascii.hexlify(h).decode())
                        print("HASH b64:", base64.b64encode(h).decode())
                    return
                # else continue to next mode
                time.sleep(INTER_TRY_DELAY)
            # if none modes ok, continue to next candidate
        print("Done: no candidate succeeded.")
    finally:
        try: ser.close()
        except: pass

if __name__ == "__main__":
    main()
