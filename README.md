# Generator i walidator danych testowych

Aplikacja strumieniowo generuje fikcyjne dane osobowe (w tym celowo zniekształcone rekordy do testów negatywnych), waliduje pola za pomocą wyrażeń regularnych, równolegle sprawdza sumy kontrolne PESEL w wielu procesach oraz zapisuje partie danych do wielu plików z wykorzystaniem wątków.

---

## 1. Wymagania i uruchomienie

* **Środowisko:** Python 3.12+ (brak wymaganych bibliotek zewnętrznych — wykorzystana wyłącznie biblioteka standardowa).

### Uruchomienie aplikacji i benchmarku GIL

Z poziomu katalogu głównego projektu:

```bash
python -m generator_app.cli --count 1000 --batch-size 250 --workers 4 --invalid-ratio 0.2 --benchmark-gil -v


python -m unittest discover -s tests -v

Flaga,Opis,Wartość domyślna
--count,Liczba generowanych rekordów testowych,1000
--batch-size,Rozmiar pojedynczej paczki rekordów,250
--workers,Liczba wątków i procesów roboczych,4
--invalid-ratio,Udział celowo błędnych rekordów (0.0 – 1.0),0.2
--out-dir,Katalog wyjściowy dla plików JSON,output_batches
--benchmark-gil,Uruchamia pomiar porównawczy GIL,wyłączone
"-v, --verbose",Włącza szczegółowe logowanie (DEBUG),wyłączone

Zagadnienie,Gdzie w kodzie,Opis realizacji
Dekoratory funkcji,"generator_app/decorators.py → retry_call(), time_limit()",Dwa własne dekoratory z parametrami oraz zachowaniem metadanych przez @functools.wraps.
Dekoratory metod,"generator_app/decorators.py → require_active_configgenerator_app/models.py → BatchConfig.batch_size, from_cli_args(), build_pesel_with_checksum()","Dekorator metody korzystający z self oraz @property z setterem, @classmethod i @staticmethod."
Iteratory,generator_app/iterators.py → BatchIterator,"Własna klasa implementująca protokół iteratora (__iter__, __next__, StopIteration)."
Generatory,"generator_app/generators.py → infinite_person_stream(), select_even_id_records(), build_bounded_stream()","Nieskończony strumień (yield), wyrażenie generujące oraz delegacja strumienia przez yield from."
Wyrażenia regularne,"generator_app/patterns.py → PESEL_RE, EMAIL_RE, PHONE_RE, POSTAL_CODE_RE",Cztery prekompilowane wzorce z grupami nazwanymi ((?P<name>...)) do walidacji i ekstrakcji pól.
Wątki,"generator_app/writer_threads.py → write_batches_concurrently(), SafeFileCounter",Współbieżny zapis plików JSON w ThreadPoolExecutor z synchronizacją threading.Lock i kolejką queue.Queue.
Procesy,generator_app/validator_proc.py → validate_batches_parallel(),Równoległa weryfikacja sum kontrolnych PESEL i reguł regex w ProcessPoolExecutor.
Pomiar GIL,"generator_app/gil_bench.py → run_gil_comparison(), get_gil_status()",Porównanie czasu wykonania obciążenia CPU-bound: sekwencyjnie vs wątki vs procesy.

Konfiguracja ścieżek importów i struktury pakietu: Początkowo moduły znajdowały się bezpośrednio w katalogu głównym projektu, co powodowało błędy importów przy odwołaniach do pakietu generator_app. Problem rozwiązano poprzez wydzielenie właściwego pakietu generator_app/ z plikiem __init__.py oraz osobnego katalogu tests/, a także uruchamianie modułów z katalogu głównego za pomocą flagi -m.

Synchronizacja zapisu współbieżnego: Podczas równoległego zapisywania wielu plików wyjściowych przez wątki konieczne było zabezpieczenie wspólnego licznika zapisanych plików przed wyścigiem (race condition) przy użyciu threading.Lock oraz uporządkowanie rejestrowania zdarzeń przez wątkowo bezpieczną kolejkę queue.Queue
