# Test Tecnico API ad alte performance

Nel repository è presente il codice per un API ad alte performance per l’ingestion di informazioni.

Sui dati salvati è possibile ottenere statistiche aggregate e la lista delle ultime 10 chiamate effettuate dell’ultima aggregazione.

## Prerequisiti

* Docker compose e Docker Engine installati sulla propria macchina, o in alternativa Docker Desktop
* Una Shell Linux, per Windows è consigliato WSL versione 2, qualsiasi distro. L'applicativo è stato testato con la WSL Ubuntu

## Getting Started

* Aprire un Terminale sulla directory del progetto
* Lanciare il codice `bin/start.sh` . Se il file non ha i diritti di esecuzione, lanciare `chmod +x bin/start.sh`
* Aprire con un browser la pagina http://localhost:8080/docs
* Eseguire i comandi seguendo la documentazione
* L'applicazione può essere terminata lanciando il comando `bin/stop.sh`, aggiungere anche in questo caso i permessi se mancanti.

## Troubleshooting

* Se viene usato Docker Desktop, e l file `bin/start.sh` impiega più di 2-3 minuti, riavviare Docker Desktop (problema noto)

# Scelte implementative

## Struttura

Per il deploy dell'applicazione viene sfruttato Docker, creando due container che contengono l'applicazione vera e propria (backend) e il database MongoDB (mongo). Il file docker-compose.yml indica le immagini da cui andranno creati i due container. 

Per quanto riguarda MongoDB viene usata un'immagine pubblica, il container di back-end viene invece creato a partire dal componente sviluppato nella directory backend. Nella directory è presente un Dockerfile, che copia tutto il contenuto della cartella backend nel container, importa tutte le librerie python necessarie tramite il comando `pip`, ed esegue il file `start_docker.sh`.

Il componente backend è un'applicazione Web che espone due Endpoint REST. Viene eseguita su server applicativo gunicorn, che viene lanciato nel comando start_docker.sh. Il codice dell'applicazione è composto da tre file python nella cartella _backend/app_:

* `main.py`: contiene i due endpoint REST. La libreria utilizzata è FastAPI
* `core.py`: contiene la logica applicativa principale ed il codice che effettua query ed insert su MongoDB
* `models.py`: contiene il modello per le risposte e i parametri di input delle API

Il codice del file models e la firma dei metodi associati alle API in main.py è stato generato tramite [fastapi-code-generator](https://github.com/koxudaxi/fastapi-code-generator), basandosi sulle direttive indicate nel file api.json

## Altre scelte rilevanti

### Insert Many

Per migliorare le performance, il codice non esegue un insert ad ogni chiamata nell'API di ingestion, ma mantiene i dati in una lista, e li salva in MongoDB con il comando insertMany solo nei seguenti casi:

* quando la lista supera o eguaglia i 1000 elementi
* quando viene chiamata l'API di retrieve (per evitare risposte parziali)

Nel momento in cui viene inserito un elemento, o viene "svuotato" questo buffer, inserisco un lock per evitare conflitti

### Varie

* In MongoDB vengono inseriti due campi aggiuntivi:
  * count_errors, che contiene 1 se la request ha generato un errore. Questo per facilitare la statistica total_errors da ritornare
  * response_time_minute, che contiene il minuto di lancio, per facilitare il group by nella request.

## Limitazioni

* Nella descrizione dell'API non è stato inserito il logo tramite [X-Logo]( https://fastapi.tiangolo.com/advanced/extending-openapi/)
* Piuttosto che usare una lista per il buffer, si poteva sperimentare l'uso delle Queue
* L'API-KEY non dovrebbe essere inserita direttamente nel codice, ma in un file a parte non versionato, oppure va inserita crittata con algoritmi come SHA-1
* Utilizzando i volumi di Docker avrei potuto migliorare il codice nei modi seguenti:
  * Permettere di cambiare il codice live senza dover buildare il container
  * se necessario (anche se non era indicato nella consegna) si poteva mantenere i dati nel database MongoDB anche spegnendo il container.
* Le performance sono state testate parzialmente usando curl, copiando il codice dalla pagina http://localhost:8080/docs e aggiungendo un foreach per eseguirlo più volte, come qui di seguito. Non è stato eseguito un test completo con 10 thread in parallelo ognuno da 10k comandi, ma solo uno da 10k. Anche in questo caso il tempo impiegato è circa 90 secondi contro i 45 richiesti.

`
for i in {1..10000}; do curl -s -X 'POST'   'http://localhost:8000/api/v1/ingest'   -H 'accept: application/json'   -H 'access_token: BigProfiles-API'   -H 'Content-Type: application/json'   -d '{
  "key": 1,
  "payload": "Stringa di esempio"
}' > /dev/null
done
`

## Assunzioni fatte

* Non mi era chiaro se i tempi di risposta ed il codice di errore fossero solo da inserire in MongoDB, oppure effettivamente l'API doveva rispondere con un certo delay random (aggiungendo uno sleep?) e inviare un errore. Ho scelto la prima ipotesi, senza aggiungere delay e rispondendo sempre con uno status 200, inserendo però il codice 200 o 500 nel corpo della risposta.

# Avvertenze

Questa sezione era già presente nella consegna ed è stata lasciata.

Usare le cartella "backend" come root del componente da sviluppare.

L'applicato Backend dovrà girare sulla porta 8000 su localhost.
Per lanciare lo stack è necessario usare docker-compose.

Per lanciare l'applicativo usare il comando 'bin/start.sh'.
Per fermale lo stack applicativo usare il comando 'bin/stop.sh'.