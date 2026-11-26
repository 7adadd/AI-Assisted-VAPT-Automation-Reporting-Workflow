# 01 — AI Lab Setup Guide (Week 1)

Complete setup of the **local AI runtime** and the **isolated vulnerable lab**.
Host: Windows 11. Everything runs locally — nothing leaves the machine.

---

## 0. ✅ CHOSEN VARIANT — WSL low-disk lab (no VMs)

The machine has **31 GB free on C:** — full VMs don't fit, so the lab runs inside the existing
**kali-linux WSL2** distro. Ollama stays on Windows (already installed & GPU-accelerated).

```
WINDOWS HOST (Windows 11)              WSL2: kali-linux (isolated lab)
---------------------------------      ---------------------------------------
Ollama :11434                          attacker toolset
  - llama3.2:3b  (fast draft)            nmap, impacket, enum4linux-ng
  - qwen2.5:7b   (primary)               Samba AD DC  <-- replaces Windows Server VM
Burp Suite Community                   DVWA (apache2 + php + mariadb)
BloodHound GUI + Neo4j                 seclists, bloodhound-python
jadx  (static mobile analysis)
frida-tools  (physical phone via USB)
```

**All lab traffic stays inside WSL2. Ollama stays on Windows (GPU-accelerated).
No VMs are created — this is what makes the project fit in ~31 GB of free disk.**

### Space budget (~9–13 GB of the 31 GB free)
| Item | Size |
|---|---|
| `qwen2.5:7b` (the one new download) | 4.7 GB |
| llama3.2:3b (already there) | 2.0 GB (kept) |
| kali WSL toolset (nmap, impacket, enum4linux-ng, seclists) | ~1.5 GB |
| Samba AD DC | ~0.5 GB |
| DVWA stack (apache2+php+mariadb) | ~1 GB |
| Burp + BloodHound GUI + jadx | ~2 GB |
| ** untouched: sentinel-* / llama-guard3 models (primary red-teaming project)** | (3.4 GB already used) |

### 0.1 Model pull (the only Windows download)
```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen2.5:7b
```

### 0.2 WSL → Windows Ollama access
Windows Ollama binds `127.0.0.1` only; kali WSL needs to reach it for scripted prompting.
Enable **mirrored networking** (Windows 11 22H2+): create `C:\Users\<you>\.wslconfig`:
```ini
[wsl2]
networkingMode=mirrored
```
then `wsl --shutdown` and reopen WSL. From kali: `curl http://127.0.0.1:11434/api/tags` must answer.
(Alternative without mirrored mode: set env var `OLLAMA_HOST=0.0.0.0` before starting Ollama and use the WSL gateway IP.)

### 0.3 kali WSL attacker toolset
```bash
sudo apt update
sudo apt install -y nmap enum4linux-ng smbclient ldap-utils seclists git python3-pip
pip3 install impacket bloodhound-python frida-tools
```

### 0.4 Samba AD DC (replaces the Windows Server VM)
```bash
sudo apt install -y samba krb5-config krb5-user winbind
sudo mv /etc/samba/smb.conf /etc/samba/smb.conf.initial
sudo samba-tool domain provision --realm=LAB.LOCAL --domain=LAB \
  --server-role=dc --dns-backend=SAMBA_INTERNAL \
  --administrator="S3cureLabPass!" --use-rfc2307
```
Then apply the **weak-AD configuration** with the generated script
`scripts/lab/configure_weak_ad_samba.sh` (Kerberoastable SPN accounts, AS-REP roastable user,
password-in-description, writable ACL path — same targets as the VM plan).
Checkpoint the distro afterwards: from Windows PowerShell `wsl --export kali-linux lab-snapshot.tar`
(export to D: if C: is tight — snapshot ~2–3 GB).

### 0.5 DVWA inside kali WSL
```bash
sudo apt install -y apache2 mariadb-server php php-mysqli php-gd git
git clone https://github.com/digininja/DVWA /var/www/html/dvwa
sudo systemctl start apache2 mariadb
sudo mysql -e "CREATE DATABASE dvwa; GRANT ALL ON dvwa.* TO 'dvwa'@'localhost' IDENTIFIED BY 'p@ssw0rd';"
# open http://127.0.0.1/dvwa/setup.php → Create/Reset Database → login admin:password
```
Burp (Windows) proxies to `http://127.0.0.1/dvwa` (mirrored networking makes WSL services
reachable from Windows on the same localhost).

### 0.6 Mobile phase (Week 3) — two paths
- **Preferred:** physical Android phone via USB → Windows `adb` (platform-tools, ~50 MB) +
  `frida-tools`; rooted phone = frida-server; non-rooted = **Frida gadget repackaging** of the
  DIVA/InsecureBankv2 APK.
- **Fallback (no phone):** static-only — jadx code review on Windows + AI-generated Frida scripts
  validated on-device later. Scope honestly in the report.

### 0.7 Ollama startup note
If the tray app shows "timed out waiting for server": kill the `ollama app` process, then run
`ollama.exe serve`, or simply launch Ollama from the Start Menu again. Verified working: `ollama list`.

---

## 1. Hardware prerequisites (measured)

| Component | Minimum | Comfortable |
|---|---|---|
| RAM | 16 GB | 32 GB |
| GPU | none (CPU inference) | NVIDIA ≥8 GB VRAM |
| Free disk | 150 GB | 250 GB |

Check quickly:
```powershell
Get-CimInstance Win32_VideoController | Select Name, AdapterRAM
Get-CimInstance Win32_ComputerSystem | Select TotalPhysicalMemory
Get-PSDrive C | Select Used,Free
```

---

## 2. AI runtimes

### 2.1 Ollama (primary — CLI + API)
```powershell
winget install Ollama.Ollama
```
Pull models (start with these three):
```bash
ollama pull llama3.1:8b            # general reasoning / report writing
ollama pull qwen2.5:7b             # strong at structured analysis & multilingual
ollama pull deepseek-coder:6.7b    # code review / script generation
```
Verify + interact:
```bash
ollama list
ollama run llama3.1:8b "You are a VAPT assistant. Confirm you are local."
```
Local REST API on `http://localhost:11434` — enables scripted prompting:
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "List 3 phases of VAPT",
  "stream": false
}'
```

### 2.2 LM Studio (GUI + OpenAI-compatible server)
1. Download from https://lmstudio.ai → install.
2. Search & download the same models (GGUF, Q4_K_M quant recommended).
3. **Local Server** tab → Start (default `http://localhost:1234/v1` — OpenAI-compatible).
4. Useful when you want a GUI chat + easy context-size control.

### 2.3 GPT4All (GUI + LocalDocs)
1. Download from https://gpt4all.io → install.
2. Enable **LocalDocs**: point it at `docs/` and `lab/` to do simple RAG over our own documents.
3. Useful for the "compare with our SOP" style questions.

> **Rule (privacy):** all three must remain configured for **local** inference. Never enable any cloud/online model with test data.

---

## 3. Model benchmark matrix (Day 3)

Run the **same 6 fixed tasks** on every model. Store results in `lab/model-benchmarks.md`.

Tasks (use lab data, not invented data):
1. Summarize a real 100-line Nmap XML scan.
2. Explain one BloodHound edge (e.g., `GetChangesAll`) in plain language.
3. Suggest 3 XSS payloads for a reflected injection with a length limit.
4. Rewrite a finding paragraph in professional report English.
5. Generate a PowerShell one-liner to list SPNs in the domain.
6. Summarize 200 lines of decompiled Java code.

For each model×runtime record:

| Field | Notes |
|---|---|
| tokens/s (CPU) | `ollama run --verbose` prints eval rate |
| tokens/s (GPU) | if applicable |
| peak RAM | Task Manager during run |
| context used | for the 200-line task |
| quality 1–5 | your subjective score per task |
| verdict | primary / backup / reject |

---

## 4. Variant A — full VM lab (superseded by §0; keep only if disk space frees up later)

> All VMs on a **host-only / internal network** (no internet on the lab segment).

### 4.1 Kali VM (attacker workstation)
- VirtualBox or VMware Workstation Player (free).
- Import official Kali VM image or install ISO.
- After first boot, snapshot **"clean-kali"**.
- Tools to verify: `nmap`, `enum4linux-ng`, `smbclient`, `bloodhound`, `neo4j`, `impacket-*`, `frida-tools` (`pip install frida-tools`).

### 4.2 Windows Server 2019/2022 (Domain Controller — vulnerable on purpose)
1. Windows Server **Evaluation ISO** (free, 180 days) from Microsoft.
2. Promote to DC of `lab.local`:
   ```powershell
   Install-WindowsFeature AD-Domain-Services -IncludeManagementTools
   Install-ADDSForest -DomainName "lab.local"
   ```
3. Create the intentionally-weak configuration (see §4.3 or the generated script `scripts/lab/configure_weak_ad.ps1`).
4. Snapshot **"vulnerable-ad"** (before any exploitation practice).

### 4.3 Weak AD configuration (targets for Week 2)
- 2 accounts with SPNs → **Kerberoasting** targets (service accounts, weak passwords).
- 1 user with *"Do not require Kerberos preauthentication"* → **AS-REP Roasting** target.
- One user with password stored in the `description` attribute.
- A non-privileged user granted `GenericAll`/`WriteDacl` on another user → **ACL abuse path**.
- `GetChangesAll` (DS-Replication) granted to a low-privileged user → **DCSync** path.

### 4.4 Web targets (Week 3)
- **DVWA**: `git clone https://github.com/digininja/DVWA` + XAMPP (PHP/MySQL) inside a small VM, or the official docker image on the Kali VM.
- **OWASP Juice Shop**: `docker run --rm -p 3000:3000 bkimminich/juice-shop`.

### 4.5 Mobile targets (Week 3)
- **Android Studio** → Device Manager → create emulator with a **Google APIs (rooted AOSP)** image — NOT a Google Play image (Play images are not rootable).
- Targets: **DIVA** (`diva-beta.apk`), **InsecureBankv2** (GitHub), optionally **OVAA**.
- Frida server matching your `frida-tools` version:
  ```bash
  # from host, with adb
  adb push frida-server /data/local/tmp/
  adb shell "chmod 755 /data/local/tmp/frida-server && /data/local/tmp/frida-server &"
  frida-ps -U   # should list processes
  ```
- jadx: `winget install jadx` or download release; `jadx-gui diva-beta.apk`.

---

## 5. Verification checklist (Week 1 done gate)

**WSL variant (current, §0):**
- [x] `ollama list` works; `llama3.2:3b` and `qwen2.5:3b` verified on RTX 3050 Ti GPU ✅ (measured 2026-11-26)
- [x] `lab/model-benchmarks.md` filled for both models × 6 tasks (`qwen2.5:3b` 69.3 tok/s, 5.0/5; `llama3.2:3b` 39.3 tok/s, 4.3/5)
- [x] kali WSL: `nmap`, `smbclient`, `ldapsearch`, `bloodhound-python`, `impacket-GetUserSPNs`, `jadx` installed
- [x] Local Ollama REST API `http://127.0.0.1:11434` verified in `scripts/vapt_ai.py` (with Privacy Rule P1 host lock)
- [x] AD target dataset (`lab/ad-lab-dataset/`) + deterministic BFS Ground Truth solver (`scripts/ingest/bloodhound_to_context.py`) verified
- [x] Live DVWA deployed in kali WSL (`apache2` + `mariadb`) and 5/5 PoCs captured via Playwright
- [x] Mobile static analysis completed on `diva-beta.apk` via `jadx` v1.5.6 + 2 syntax/signature-verified Frida scripts (static-only fallback documented per §0.6)
- [x] Privacy checklist (doc 03) fully passed

---

## 6. Troubleshooting quick table

| Symptom | Likely cause | Fix |
|---|---|---|
| Ollama model downloads stop | disk space / proxy | check free disk; retry `ollama pull` |
| Very slow inference (CPU) | model too big | use 7–8B q4, or `qwen2.5:3b` |
| VMs can't reach each other | NAT instead of host-only | re-check network adapter per VM |
| BloodHound UI empty | neo4j not started / wrong creds | `sudo neo4j start`, default `neo4j`/`bloodhound` |
| `frida-ps -U` fails | frida-server not running on device | re-run push + start; match versions exactly |
| DVWA DB error | not initialized | open `http://dvwa/setup.php` → Create/Reset DB |
