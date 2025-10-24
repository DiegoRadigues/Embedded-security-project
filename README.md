# Project write-up

---

## 1 — Abstract
The goal was to get the secret keyphrase from an Arduino Uno “vault”. The device asks for a password on the serial line. If the password is correct, the device prints the salt and the hash of the secret keyphrase.

I used a **protocol bruteforce** on the serial port. I extracted candidate strings from the firmware binary (`strings`), filtered and prioritized them, then tried each candidate automatically with a Python script that talks to the Arduino. The attack succeeded: one candidate produced `ACCESS GRANTED` and the device printed its salt and hash.

---

## 2 — Deliverables 
- Salt and hash
- Full write-up describing hardware, attack tree, vulnerability analysis, attack implementation, scripts and counter-measures.

**Successful output (examples captured during the attack):**
- Successful candidate: `f7-@Jp0w`
- SALT (hex): `3439353237363739`
- SALT (base64): `NDk1Mjc2Nzk=`
- HASH (hex): `30354637333044423835324344464442303831343041303033313039334631413635383432464641344435303932464535343935373837454130324433454634`
- HASH (base64): `MDVGNzMwREI4NTJDREZEQjA4MTQwQTAwMzEwOTNGMUE2NTg0MkZGQTRENTA5MkZFNTQ5NTc4N0VBMDJEM0VGNA==`


---

## 3 — Hardware and wiring
**Minimal hardware used**
- Target: Arduino Uno (ATmega328P).
- Host computer (Linux)
- USB TTL adapter HW-193 (CH340G)
- ChipWhisperer-Nano or logic analyzer (not required for this primary attack).

**Simple wiring / connections**
- Connect Arduino to the TTL Device on pin 10, 11. RX, TX.
- The host opens `/dev/ttyUSB0` (or `/dev/ttyACM0`) for serial.

![Figure 1 — Simple wiring between Arduino Uno and USB-TTL adapter](https://github.com/user-attachments/assets/6f60e051-5966-4ed9-b2c7-8dc9c909b0aa)

*Figure 1 — Simple wiring between the Arduino Uno and the USB-TTL adapter (RX/TX). This setup allows direct serial communication for password attempts.*



---

## 4 — Asset description
**Assets (what we want to protect / what is sensitive):**
- **Secret keyphrase** stored inside Arduino firmware or memory.
- **Salt and resulting hash** printed only after correct password.
- **Serial interface** — a local access interface that accepts password input.

**Attacker model:** The attacker has local physical access to connect to the board via USB and UART and can send serial data. The attacker can read the firmware file (provided in the exercise), run `strings` on it, and run scripts on a PC.

---

## 5 — Attack tree
![Figure 2 — Attack tree showing different strategies to obtain the secret keyphrase](https://github.com/user-attachments/assets/f600ccc5-4d58-4d25-b3b9-a99b03b6d66d)

*Figure 2 — Attack tree.*



---

## 6 — Vulnerability identification and evidence
**Vulnerability:** The device accepts password attempts over an unprotected UART interface and leaks the salt and hash when a correct password is given. The firmware binary contains many readable strings. Using this information an attacker can build a wordlist and try the candidates until one succeeds.

**Evidence (from my logs and commands):**
- I extracted strings from the firmware:

```bash
strings secure_sketch_v20251001.0.elf > full_candidates_raw.txt
# filter by length 4..32 and remove CR:
awk 'length($0) >= 4 && length($0) <= 32 { print $0 }' full_candidates_raw.txt \
  | tr -d '\r' \
  | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' \
  | sort -u > full_candidates.txt
```

- Prioritized candidates (examples): found tokens like `PASSWORD`, `sha3`, `SHA3_256`, and many other symbols. Built a final cleaned wordlist: `candidates_priority_clean.txt` (382 candidates in my run).
- Automated tries with a Python script. The script reported:
- ![Figure 3 — Serial injection automation with Python script](https://github.com/user-attachments/assets/0cbce44f-feff-4b47-b983-f419c24bee1a)

*Figure 3 — Output from the Python brute-force script. When the correct candidate is tested, the device prints `ACCESS GRANTED` along with the salt and hash.*

This shows the firmware revealed the correct behavior when a candidate matched.

---

## 7 — Vulnerability severity assessment 

**Source:** [NVD CVSS v4.0 Calculator](https://nvd.nist.gov/vuln-metrics/cvss/v4-calculator)

**Final Score:** **7.2 (High)**

---

### 1. CVSS v4.0 Vector
```
CVSS:4.0/AV:L/AC:L/AT:N/PR:N/UI:N/S:U/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N
```

**Base Score:** 7.2 — High  

---

### 2. Metric Justifications

### Exploitability Metrics
| Metric | Value | Justification |
|--------|--------|---------------|
| **Attack Vector (AV)** | Local (L) | The attacker must have local or physical access to the USB/serial port. No network connection is available. |
| **Attack Complexity (AC)** | Low (L) | The attack is simple and reliable; a Python script can automatically test candidate passwords. |
| **Attack Requirements (AT)** | None (N) | No preconditions or setup are required beyond serial access. |
| **Privileges Required (PR)** | None (N) | Any local user with physical access can send commands. No prior privileges are needed. |
| **User Interaction (UI)** | None (N) | The attack requires no legitimate user participation. |

#### Vulnerable System Impact Metrics
| Metric | Value | Justification |
|--------|--------|---------------|
| **Confidentiality (VC)** | High (H) | Sensitive cryptographic data (salt + hash) is revealed, compromising the secret. |
| **Integrity (VI)** | High (H) | Disclosure of secret material enables impersonation or forged operations. |
| **Availability (VA)** | Low (L) | The device remains operational after the attack; minimal impact on availability. |

#### Subsequent System Impact Metrics
| Metric | Value | Justification |
|--------|--------|---------------|
| **Confidentiality (SC)** | None (N) | Leakage does not propagate to other systems. |
| **Integrity (SI)** | None (N) | No broader impact on other systems. |
| **Availability (SA)** | None (N) | No wider service degradation. |

---

### 3. Supplemental Metrics
| Metric | Value | Justification |
|--------|--------|---------------|
| **Safety (S)** | Not Defined (X) | No physical or human safety risk. |
| **Automatable (AU)** | Not Defined (X) | Although easily scriptable, automation impact not assessed. |
| **Recovery (R)** | Not Defined (X) | The system can be restored easily (firmware reflash). |
| **Value Density (V)** | Not Defined (X) | Low-density asset: a single secret keyphrase. |
| **Vulnerability Response Effort (RE)** | Not Defined (X) | No vendor patch officially available. |
| **Provider Urgency (U)** | Not Defined (X) | No vendor advisory issued. |

---

### 4. Environmental (Modified Base Metrics)
| Metric | Value | Justification |
|--------|--------|---------------|
| **MAV / MAC / MAT / MPR / MUI** | Not Defined (X) | Attack conditions same as base metrics. |
| **MVC (Confidentiality)** | High (H) | Secret data is critical. |
| **MVI (Integrity)** | High (H) | Manipulation of results would severely affect trust. |
| **MVA (Availability)** | High (H) | Availability is important but not vital. |
| **MSC / MSI** | Not Defined (X) | No extended effect beyond the device. |
| **MSA (Availability)** | Low (L) | Only slight operational disruption during brute-force. |

---

### 5. Environmental Security Requirements
| Metric | Value | Justification |
|--------|--------|---------------|
| **Confidentiality Requirement (CR)** | High (H) | The keyphrase is highly sensitive and should remain secret. |
| **Integrity Requirement (IR)** | High (H) | Device integrity relies on secret protection. |
| **Availability Requirement (AR)** | Low (L) | Temporary unavailability is acceptable. |

---

### 6. Threat Metrics
| Metric | Value | Justification |
|--------|--------|---------------|
| **Exploit Maturity (E)** | Proof-of-Concept (POC) | A working exploit (Python script) demonstrates the vulnerability in practice. |


---

## 8 — Attack description and implementation 

### clone the repository
```bash
git clone https://github.com/DiegoRadigues/Embedded-security-project.git
cd ~/Embedded-security-project
```

files must be in local folder
```bash
ls -l secure_sketch_v20251001.0.elf serial_bruteforce_protocol.py
```


### 8.1 — Environment setup (host)
```bash
# create a Python venv
cd ~/Embedded-security-project
python3 -m venv venv
source venv/bin/activate

# install pyserial if not present
pip install pyserial
```

### 8.2 — Extract candidate words from firmware
Assume firmware file `secure_sketch_v20251001.0.elf` is in `~/Embedded-security-project
`:

```bash
cd ~/Embedded-security-project
strings secure_sketch_v20251001.0.elf > full_candidates_raw.txt

# keep strings length 4..32, trim CR, remove duplicates
awk 'length($0) >= 4 && length($0) <= 32 { print $0 }' full_candidates_raw.txt \
  | tr -d '\r' \
  | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' \
  | sort -u > full_candidates.txt

# build priority lists (examples used in my workflow)
grep -P '[A-Za-z]' full_candidates.txt | grep -P '[0-9\W]' | sort -u > priority_A.txt
grep -E '^[A-Za-z]{4,12}$' full_candidates.txt | sort -u > priority_B.txt
printf "%s\n" "PASSWORD" "sha3" "SHA3_256" | grep -Fxf - full_candidates.txt > priority_C.txt || true

# combine ordered priority lists
cat priority_C.txt priority_A.txt priority_B.txt > candidates_priority.txt

# clean obviously irrelevant tokens (files, .c, symbols)
grep -vE '^/|\\.c$|\\.o$|__|vector_|\\.part\\.|\\.o$|\\.S$' candidates_priority.txt > candidates_priority_clean.txt

# check number of candidates
wc -l candidates_priority_clean.txt
# example result: 382
```

### 8.3 — Python bruteforce script
Use the script [serial_bruteforce_protocol.py](https://github.com/DiegoRadigues/Embedded-security-project/blob/main/serial_bruteforce_protocol.py). This script:
- opens the serial port,
- optionally toggles DTR to reset the Arduino before each try,
- waits for a password prompt,
- sends candidate either char-by-char (small delay between characters) or as a line,
- checks serial output for success markers,
- saves the serial capture of each try.



### 8.4 — Running the attack
1. Put the cleaned candidate list at `~/Embedded-security-project
/candidates_priority_clean.txt`.
2. Make the script executable:
```bash
chmod +x serial_bruteforce_protocol.py
```
3. Run the script inside the venv:
```bash
source ~/venv/bin/activate
python ~/Embedded-security-project/serial_bruteforce_protocol.py 2>&1 | tee bruteforce_priority_run.log
```
4. Monitor outputs. When the script prints `=== SUCCESS for <candidate>` it also saved the serial capture file, and it printed salt/hash.

**Notes about behavior**:
- The script tries two modes: char-by-char (useful if firmware reads char-by-char) and line mode.
- The script toggles DTR to reset the Arduino between tries to keep the device in a known prompt state.
- The script waits for typical prompts such as `Enter password:` to avoid sending data in wrong states.

---
# 9 — Countermeasures

## 9.1 — Hash & obfuscation

I have tested a more secure version of the firmware [very_secure_sketch_v20251001.0.elf](https://github.com/DiegoRadigues/Embedded-security-project/blob/main/very_secure_sketch_v20251001.0.elf)

- The password is **not stored in clear** in the firmware.
- Instead, the code stores a **SHA3‑256 hash** of the password.
- The hash is **XOR‑obfuscated** so it does not appear as readable text.


**Remaining weaknesses:**
- The hash is still in flash memory → a motivated attacker can read it.
- Serial is still open → an attacker can still try brute‑force.

---

## 9.2 — Delay against brute‑force

To slow down brute‑force attacks we can add a **delay after each wrong attempt**.

After many fails, the attacker must wait an exponential long time.
This makes brute‑force very slow.

**Store fail counter in EEPROM** → reset button does not reset delay.

---

## 9.3 — Force hardware interaction

If there are **too many failed attempts**, the system can lock:

- User must press a **physical button** to unlock the system.
- Or unplug power and press button during start.

This means an attacker **must be physically present** or implement a hardware system to automatize.

---

## 9.4 — Multiple passwords 

We can ask:
 Password 1
 Password 2
 Password 3

The attacker must guess **all passwords in the correct order**.

Example with 382 possible candidates:
- 2 passwords → 382² = 145,924 combinations
- 3 passwords → 382³ = 55,742,968 combinations

Combined with a delay at each try

## 9.4 decoy password

Add several decoy passwords whose purpose is to offer better-looking targets for the kinds of attacks we expect. For example, include a decoy that intentionally returns a much longer response time to fool a timing attack, or a decoy that performs extra, complex computations to change the power signature and mislead power analysis. When the device detects that a decoy was used, it can lock itself and require stronger authentication (longer passwords, second factor or multiple passwords), or it can simply return believable but fake data instead of the real secret. If the device is networked it can also report the intrusion attempt and upload its logs to a secure server. The idea is to exploit the predictability of an attack so the attacker falls into the trap and effectively announces themself as an attacker. In the case I used, if I had found decoy strings inside the ELF and classified them as possible passwords I would obviously have fallen into the trap. Make sure the decoys are very different from the real password so legitimate users don’t lock themselves out after a normal typo mistake.

---

## 10 Alternative method 

### access via ISP (not tested)

If the ELF file is not available you can try to read the chip using the ISP interface. ISP can read the **flash** and the **EEPROM** of the ATmega328P microcontroller.

1. Connect an ISP programmer (for example **USBasp**) to the 6-pin **ICSP** header on the board.  
2. On your computer use `avrdude` to try to read the flash:
   ```bash
   avrdude -c usbasp -p m328p -U flash:r:dump_flash.bin:r
   ```
3. If the read works, use `strings` and `avr-objdump` on `dump_flash.bin` to find readable text and to inspect the code that checks the password:
   ```bash
   strings dump_flash.bin | grep -iE 'pass|salt|sha|ACCESS|grant'
   avr-objdump -m avr -D dump_flash.bin > dump.s


### Timing analysis
Timing analysis looks at how long the device takes to do things. If a password check or a comparison takes a little longer for some inputs than others you can sometimes guess parts of the secret by measuring response times and comparing many tries. Defenses are : make the code run in constant time or add random delays so timing no longer leaks information.

### Power analysis
Power analysis studies the device’s power consumption while it runs. The idea is that different operations or data values cause slightly different current draws. With a single clear pattern you might get something from Simple Power Analysis (SPA); with many traces and statistics you can do Differential Power Analysis (DPA) and recover secret bits. Countermeasures include masking/blinding (so intermediate values are randomized), adding noise, and hardware measures that hide the power signature.

![Power measurement module assembled](https://github.com/user-attachments/assets/c4a94461-9435-4618-adb9-b0d496cb641d)

*Figure 4 — Power-supply / measurement module assembled to feed the Arduino and capture basic power traces.*
  
As shown in Figure 4, I assembled a simple power-supply/measurement module to feed the Arduino and verify that power traces were observable. I used this setup to confirm the board could be powered and that current waveforms could be recorded but I did not have time to fully configure the ChipWhisperer hardware and software, therefore I did not pursue the full power-analysis path further.




### Supply glitch
Glitching means briefly disturbing the power or clock to make the microcontroller misbehave (skip instructions, corrupt a comparison, etc.). If timed right, a glitch can bypass the check or force the device into a state that leaks info. Protections include detecting supply anomalies, redundant checks (check password many times before giving access).






