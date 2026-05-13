# 📺 Canale de Știri — Aplicație Distribuită Client-Server

Aplicație distribuită de tip client-server pentru gestionarea canalelor de știri, cu subscripție, notificări și filtrare de conținut.

## Arhitectură

```
┌─────────────────┐         TCP          ┌─────────────────┐
│   Client 1      │◄───────────────────► │                 │
│   (Python)      │                      │   Server        │
├─────────────────┤         TCP          │   (Python)      │
│   Client 2      │◄───────────────────► │   Port 5000     │
│   (Python)      │                      │   Docker        │
├─────────────────┤         TCP          │                 │
│   Client N      │◄───────────────────► │                 │
└─────────────────┘                      └─────────────────┘
```

## Structura proiectului

```
ReteleProiect/
├── server/
│   ├── server.py          # Serverul TCP concurent
│   ├── banned_words.txt   # Lista cuvinte interzise
│   └── Dockerfile         # Docker image server
├── client/
│   └── client.py          # Clientul consolă
├── docker-compose.yml     # Docker Compose
└── README.md              # Documentația
```

## Rulare

### Pornire server cu Docker

```bash
docker compose up --build
```

Server-ul va rula pe portul **5000**.

### Pornire server fără Docker (opțional)

```bash
cd server
python server.py
```

### Pornire client

```bash
cd client
python client.py
```

Sau cu adresă și port custom:

```bash
python client.py <host> <port>
```

Exemplu:

```bash
python client.py localhost 5000
```

## Protocol de comunicare

Protocol text-based TCP. Fiecare mesaj e pe o linie, câmpurile separate cu `|`.

### Comenzi client → server

| Comandă | Format | Descriere |
|---------|--------|-----------|
| SET_NAME | `SET_NAME\|nume` | Setează numele clientului |
| LIST | `LIST` | Cere lista canalelor |
| CREATE | `CREATE\|nume\|descriere` | Creează canal nou |
| DELETE | `DELETE\|nume` | Șterge canal propriu |
| SUBSCRIBE | `SUBSCRIBE\|nume` | Abonare la canal |
| UNSUBSCRIBE | `UNSUBSCRIBE\|nume` | Dezabonare |
| PUBLISH | `PUBLISH\|canal\|text` | Publică știre |
| QUIT | `QUIT` | Deconectare |

### Răspunsuri server → client

| Răspuns | Descriere |
|---------|-----------|
| `OK\|mesaj` | Operație reușită |
| `ERROR\|mesaj` | Eroare |
| `CHANNELS\|canal1:desc1,canal2:desc2` | Lista canalelor |
| `NOTIFY_NEW_CHANNEL\|canal\|descriere` | Canal nou creat |
| `NOTIFY_DEL_CHANNEL\|canal` | Canal șters |
| `NEWS\|canal\|text` | Știre primită |

## Funcționalități

- ✅ Conectare și listare canale
- ✅ Creare canal cu nume unic + notificare
- ✅ Ștergere canal (doar proprietarul) + notificare
- ✅ Subscribe / Unsubscribe la canale
- ✅ Publicare știri (doar proprietarul canalului)
- ✅ Filtrare cuvinte interzise (stirea nu se livrează)
- ✅ Server concurent (threading)
- ✅ Curățare subscripții la deconectare
- ✅ Tratare erori (canal inexistent, subscribe dublu, etc.)

## Filtrare conținut

Cuvintele interzise sunt definite în `server/banned_words.txt`, câte unul pe linie. Știrile care conțin aceste cuvinte nu sunt livrate abonaților.

## Comportament la deconectare

- Clientul este eliminat din toate subscripțiile
- Canalele create de client **rămân active** (nu se șterg la deconectare)
- Motivul: alți clienți pot fi abonați la acele canale

## Tehnologii

- **Python 3** — fără dependențe externe
- **TCP Sockets** — comunicare fiabilă
- **Threading** — server concurent
- **Docker** — containerizare server
