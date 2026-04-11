# WMS — Role-Based Access Control (RBAC)

**Status**: LOCKED — ne mijenjati bez eksplicitnog odobrenja vlasnika projekta

---

## Koncept: Sistemske role vs. Display nazivi

Sustav koristi **fiksne sistemske role** u kodu i bazi. Svaki kupac može konfigurirati
**vlastiti naziv** za svaku rolu koji se prikazuje u UI-u — bez utjecaja na logiku dozvola.

### Primjer konfiguracije po kupcu

| Sistemska rola | Primjer: proizvodna firma | Primjer: distribucija |
|----------------|--------------------------|----------------------|
| `ADMIN` | Admin | Administrator |
| `MANAGER` | Menadžment | Direktor |
| `WAREHOUSE_STAFF` | Administracija | Referent nabave |
| `VIEWER` | Kontrola | Revizor |
| `OPERATOR` | Operater lakirnice | Skladištar |

---

## Sistemske role u v1

| Sistemska rola | Defaultni naziv | Opis |
|----------------|-----------------|------|
| `ADMIN` | Admin | Puni pristup svemu |
| `MANAGER` | Menadžment | Read-only pregled svega |
| `WAREHOUSE_STAFF` | Administracija | Identifikator + dosijei zaposlenika |
| `VIEWER` | Kontrola | Samo Identifikator |
| `OPERATOR` | Operater | Samo ekran za unos |

### Buduće role (nisu u v1 scope)

| Sistemska rola | Defaultni naziv | Opis |
|----------------|-----------------|------|
| `WAREHOUSE_OPERATOR` | Skladištar | Izdavanje iz skladišta (2. smjena) |

---

## Matrica dozvola

| Akcija | ADMIN | MANAGER | WAREHOUSE_STAFF | VIEWER | OPERATOR |
|--------|-------|---------|-----------------|--------|----------|
| **Unos izlaza (draft)** | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Odobravanje/odbijanje drafta** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Pregled stanja skladišta** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Primanje robe (ulaz)** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Kreiranje narudžbenica** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Pregled narudžbenica** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Upravljanje artiklima** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Generiranje/print barkoda** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Identifikator — pretraživanje** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Identifikator — missing report** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Identifikator — obrada reportova** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Dosijei zaposlenika — pregled** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Dosijei zaposlenika — uređivanje** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Osobna izdavanja** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Izvještaji i statistike** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Inventura** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Upravljanje korisnicima** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Konfiguracija sustava** | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## "Prozor" svake role (što vidi u sidebaru)

### ADMIN
Svi moduli.

### MANAGER
- Pregled skladišta (read-only)
- Narudžbenice (read-only)
- Dosijei zaposlenika (read-only)
- Izvještaji i statistike

### WAREHOUSE_STAFF
- Identifikator (pretraživanje + missing report)
- Dosijei zaposlenika (pregled)

### VIEWER
- Identifikator (pretraživanje + missing report)

### OPERATOR
- Ekran za unos (draft entry)

---

## Pravila implementacije

- **Backend** validira rolu neovisno za svaki endpoint — ovo je jedina prava sigurnosna provjera
- **Frontend** RBAC je samo UX (sidebar, routing) — ne može biti jedina zaštita
- Korisnici ne vide module kojima nemaju pristup (nema linka u sidebaru)
- Neovlašteni direktni pristup ruti → redirect na korisnikovu home rutu
- Display naziv role konfigurira se u postavkama sustava, ne mijenja sistemsku rolu
