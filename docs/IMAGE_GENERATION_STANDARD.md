# Standard generowania i przygotowania zdjęć SportRent

**Wersja:** 1.0  
**Status:** obowiązujący dla nowych materiałów  
**Zakres:** frontend, panel administracyjny, API i storage obrazów

## 1. Cel

SportRent pomaga wypożyczać sprzęt sportowy i turystyczny bez konieczności jego
kupowania i przechowywania. Obraz ma zatem spełniać trzy zadania, w tej
kolejności:

1. wiarygodnie pokazać, co użytkownik rezerwuje;
2. umożliwić szybkie porównanie produktów;
3. budować ochotę na aktywny wypoczynek.

Materiały powinny wyglądać nowocześnie i atrakcyjnie, ale nie mogą sugerować
wyposażenia, stanu, koloru, marki ani funkcji, których wypożyczany egzemplarz
nie posiada.

> **Zasada nadrzędna:** generatywna AI może tworzyć materiały marketingowe
> i kontrolowane packshoty, lecz nie zastępuje dokumentacyjnych zdjęć
> rzeczywistego egzemplarza, jego stanu ani elementów zestawu.

W przypadku kasków, uprzęży, lin, zestawów via ferrata i innego wyposażenia
bezpieczeństwa wygląd konstrukcji, sposób użycia oraz kompletność zestawu muszą
zostać zweryfikowane przez osobę znającą produkt. Zdjęcie rzeczywistego
egzemplarza jest obowiązkowe, jeżeli obraz ma dokumentować jego stan.

## 2. Charakter wizualny marki

Każdy materiał powinien komunikować:

- **wiarygodność** — sprzęt wygląda realnie, czysto i zgodnie z ofertą;
- **prostotę wyboru** — jeden wyraźny temat, czytelna sylwetka, mało rozpraszaczy;
- **gotowość do przygody** — aktywny, ale osiągalny wypoczynek, nie ekstremalny
  wyczyn;
- **dostępność** — naturalni ludzie i miejsca, bez elitarnego lub luksusowego
  charakteru;
- **odpowiedzialność** — zadbany sprzęt wielokrotnego użytku, bez kultury
  nadmiernej konsumpcji.

Preferowana estetyka to realistyczna fotografia komercyjna, naturalne kolory,
lekko chłodna neutralna baza i umiarkowanie ciepłe światło. Należy unikać
przesadnego HDR, bardzo wysokiej saturacji, agresywnych filtrów, cyberpunkowych
barw, sztucznego połysku i wyglądu renderu 3D.

## 3. Miejsca użycia w obecnym interfejsie

Obrazy produktu dzielą się na dwie klasy o różnym przeznaczeniu:

- **okładka (`display_order = 0`)** — pierwsze zdjęcie; jest używane we
  wszystkich widokach produktu w aplikacji i jednocześnie jako pierwszy slajd
  galerii;
- **zdjęcia galeryjne (`display_order > 0`)** — są używane wyłącznie w galerii
  na stronie szczegółów produktu.

Na obecnym etapie okładka jest jednym plikiem i jednym URL-em. Nie generujemy
jej osobno w różnych proporcjach ani rozdzielczościach. Ten sam obraz jest
dopasowywany przez interfejs do każdego miejsca użycia.

| Zastosowanie | Obecny kadr | Sposób wyświetlania | Konsekwencja |
| --- | ---: | --- | --- |
| karta produktu na stronie głównej i w ulubionych | 256 × 224, **8:7** | `cover` | boki zdjęcia mogą zostać przycięte |
| wynik wyszukiwania na desktopie | ok. 240 × 192, **5:4** | `cover` | potrzebny centralny bezpieczny kadr |
| podsumowanie zamówienia | 80 × 80, **1:1** | `cover` | produkt musi pozostać czytelny w kwadracie |
| podpowiedź w wyszukiwarce | 80 × 64, **5:4** | `contain` | widoczny jest cały plik wraz z tłem |
| galeria produktu na mobile | **4:3** | `contain` dla wielu zdjęć | podstawowy format produktu |
| galeria produktu na desktopie i koszyk | format źródłowy | bez przycięcia / `contain` | widać cały produkt |
| panoramiczna kategoria na stronie głównej | pełna szerokość × 50 vh | `cover`, środek kadru | wymaga osobnego wariantu desktop i mobile |
| promocyjny kafel kategorii | od bardzo wąskiego do szerokiego | `cover` | jeden plik nie zapewnia poprawnego kadru na każdym ekranie |

Okładkę przygotowujemy tylko w proporcji 4:3. Kompozycja powinna pozostać
czytelna, gdy interfejs przytnie ją do 8:7, 5:4 lub 1:1, ale nie tworzymy ani
nie zapisujemy takich wersji jako osobnych plików. Pozostałe zdjęcia również
mają format 4:3 i występują tylko w galerii.

## 4. Typy materiałów i presety

### P1 — okładka produktu (`display_order = 0`)

To pierwsze i najważniejsze zdjęcie produktu. Jest używane w katalogu,
wyszukiwaniu, galerii, ulubionych, koszyku i zamówieniu. Musi być dobrym
packshotem nawet wtedy, gdy w galerii dostępne są atrakcyjniejsze ujęcia
lifestyle.

| Parametr | Standard |
| --- | --- |
| proporcje | **4:3** |
| plik publikowany | **1600 × 1200 px**, WebP lub JPEG, sRGB |
| zalecane źródło do archiwum | 2400 × 1800 px, jeśli jest dostępne |
| tło | jednolite, matowe, jasne chłodne `#F3F6F9` |
| ujęcie | produkt w całości, widok 3/4 od przodu lub najbardziej rozpoznawalny bok |
| bezpieczny obszar | kluczowy produkt w centralnych **70% szerokości i 86% wysokości** |
| udział produktu | zwykle 60–70% powierzchni kadru |
| perspektywa | naturalna, odpowiednik obiektywu 50–70 mm |
| światło | duże miękkie źródło z lewej-góry, łagodne wypełnienie |
| cień | delikatny, realistyczny cień kontaktowy; produkt nie może „lewitować” |
| głębia ostrości | cały produkt ostry, bez rozmywania ważnych elementów |

Tło ma być nieprzezroczyste. Przezroczystość jest zarezerwowana dla wycinanych
materiałów kategorii. Jasne tło pozostaje częścią fotografii także w ciemnym
motywie aplikacji i zapewnia stałe odwzorowanie produktu.

Przed zatwierdzeniem warto wyświetlić okładkę pod maskami 8:7, 5:4 i 1:1.
Jest to wyłącznie kontrola kompozycji jednego pliku 4:3, a nie polecenie
generowania kolejnych wersji. W żadnym podglądzie nie wolno uciąć elementu
istotnego dla rozpoznania lub bezpieczeństwa produktu.

### P2 — zdjęcia tylko do galerii (`display_order > 0`)

Zalecany komplet produktu to **4 zdjęcia łącznie z okładką**, minimum 3,
maksimum 5:

0. `cover` — okładka 3/4 zgodna z P1, używana również poza galerią;
1. `side` — przeciwny bok albo widok z tyłu, tylko galeria;
2. `set` — wszystkie elementy faktycznie dołączone do wypożyczenia, tylko
   galeria;
3. `detail` — mechanizm, mocowanie, rozmiar lub inny element ważny przy wyborze,
   tylko galeria;
4. `use` — opcjonalne ujęcie w użyciu albo dokumentacja rzeczywistego stanu,
   tylko galeria.

Ujęcia `side`, `set` i `detail` zachowują proporcje 4:3, tło, światło, skalę
i balans bieli z P1. Są publikowane jako pojedyncze pliki 1600 × 1200 px. Nie
muszą przechodzić testu kadrowania do innych proporcji, ponieważ nie są używane
poza galerią. Ujęcie `set` może być wykonane z góry. Elementy zestawu są
rozłożone czytelnie, bez dekoracyjnych przedmiotów mogących sugerować, że należą
do oferty.

Galeria nie może składać się z kilku niemal identycznych wariacji wygenerowanych
przez AI. Każde zdjęcie musi odpowiadać na inne pytanie użytkownika.

### P3 — hero kategorii

Hero buduje emocje i prowadzi do rezerwacji. Może być generowane, jeśli nie
przedstawia konkretnego wypożyczanego egzemplarza.

| Wariant | Proporcje | Rozmiar docelowy |
| --- | ---: | ---: |
| desktop | **21:9** | **2520 × 1080 px** |
| mobile | **4:5** | **1280 × 1600 px** |

Wymagania:

- realistyczna aktywność odpowiadająca dokładnie kategorii;
- sceneria wiarygodna dla Polski lub Europy Środkowej;
- pora dnia i pogoda zachęcające, ale nie nierealnie idealne;
- ludzie używają sprzętu prawidłowo i mają wymagane zabezpieczenia;
- twarze nie są głównym tematem i nie przypominają osób publicznych;
- środkowe 45% kadru jest spokojne i zapewnia czytelność białego tytułu oraz CTA;
- brak tekstu, logo, przycisków i gradientów wypalonych w pliku;
- najważniejsza akcja nie może znajdować się pod tytułem.

Kontrast białego tekstu względem obrazu lub obrazu z nakładką musi wynosić co
najmniej 4,5:1. Preferowana jest nakładka realizowana w CSS, a nie zapisana
w obrazie.

### P4 — promocyjny kafel kategorii

Kafel może zawierać:

- pojedynczy, wycięty produkt na przezroczystym tle; albo
- prostą scenę lifestyle z jednym wyraźnym tematem.

| Wariant | Proporcje | Rozmiar docelowy | Użycie |
| --- | ---: | ---: | --- |
| mobile narrow | **1:2** | **800 × 1600 px** | boczny panel na małym ekranie |
| desktop portrait | **4:5** | **1200 × 1500 px** | mały kafel |
| desktop wide | **3:2** | **1800 × 1200 px** | średni kafel |
| desktop large | **6:5** | **1800 × 1500 px** | duży kafel |

Temat należy umieścić po stronie przeznaczonej na obraz, patrząc lub poruszając
się w kierunku tekstu. Dla wycinanego produktu stosuje się przezroczyste tło,
czyste krawędzie bez jasnej obwódki i naturalny miękki cień na osobnej warstwie
alfa.

### P5 — avatar użytkownika

Obecny interfejs nie wykorzystuje avatara jako głównego materiału, ale model
danych go przewiduje.

- proporcje **1:1**;
- master 800 × 800 px, publikacja 256 × 256 px;
- twarz w centralnych 60% kadru;
- tylko zdjęcie przesłane za zgodą użytkownika;
- nie generować ani nie „poprawiać” tożsamości realnej osoby bez wyraźnej zgody.

### Materiały, których nie generujemy

Logo SportRent, logo marek, znaki płatności, piktogramy bezpieczeństwa, etykiety
certyfikacyjne i ikony kategorii muszą pochodzić z zatwierdzonych plików
wektorowych lub od właściciela marki. AI nie może odtwarzać ani wymyślać
logotypów i certyfikatów.

## 5. Reguły kompozycji produktu

1. Pokazuj dokładnie jeden produkt albo dokładnie jeden oferowany zestaw.
2. Cały produkt musi mieścić się w kadrze; wyjątkiem jest zdjęcie `detail`.
3. Zostaw co najmniej 8% oddechu od każdej krawędzi mastera.
4. Główna bryła i elementy krytyczne muszą mieścić się w centralnym kwadracie.
5. Zachowaj realne proporcje, geometrię, liczbę elementów i punkty mocowania.
6. Nie dodawaj akcesoriów, opakowania, elektroniki ani dekoracji spoza oferty.
7. Nie zmieniaj koloru w celu dopasowania do palety aplikacji.
8. Skala produktu musi być zrozumiała. Jeśli wymaga człowieka, samochodu lub
   innego odniesienia, umieść takie ujęcie dopiero w galerii, nie jako `main`.
9. Nie maskuj normalnych śladów użytkowania na zdjęciach realnego egzemplarza.
10. Drobne czyszczenie tła i korekta ekspozycji są dozwolone; zmiana stanu
    technicznego lub wyposażenia nie jest.

## 6. Kolor, światło i retusz

- przestrzeń barw: **sRGB IEC61966-2.1**;
- balans bieli: neutralny, ten sam w całej serii produktu;
- biel i czerń nie mogą tracić faktury;
- średni kontrast, naturalne cienie, brak poświaty HDR;
- kolor produktu powinien być zgodny z referencją, docelowo z różnicą
  `ΔE00 ≤ 4` względem zatwierdzonej fotografii wzorcowej;
- z materiałów usuwamy aberracje, kurz na tle i artefakty generowania;
- nie usuwamy cech rzeczywistego egzemplarza istotnych dla najmu;
- nie stosujemy selektywnego wyszczuplania ludzi ani modyfikacji ich ciała.

Globalny filtr ciemnego motywu obniża obecnie jasność obrazów. Dlatego nie należy
prześwietlać plików wejściowych „na zapas”.

## 7. Format, eksport i wydajność

### Pliki źródłowe

- master archiwalny: PNG lub TIFF, bezstratny, 8 bitów na kanał, sRGB;
- zachować wersję przed retuszem lub obraz referencyjny;
- master nie jest bezpośrednio wysyłany użytkownikowi.

### Pliki publikowane

Preferowana kolejność:

1. AVIF — jako wariant najbardziej skompresowany;
2. WebP — podstawowy bezpieczny wariant;
3. JPEG — fallback dla fotografii;
4. PNG/WebP lossless — tylko gdy potrzebna jest przezroczystość.

| Rola | Wymiary | Limit orientacyjny |
| --- | ---: | ---: |
| okładka używana w całej aplikacji | 1600 × 1200 | 250 KB |
| zdjęcie tylko do galerii | 1600 × 1200 | 250 KB |
| hero desktop | 2520 × 1080 | 450 KB |
| hero mobile | 1280 × 1600 | 350 KB |
| kafel kategorii | zgodnie z P4 | 250 KB |

Limity są celami, nie powodem do widocznej degradacji. Nie wolno powiększać
małego źródła tylko po to, aby formalnie osiągnąć wymagany wymiar.

Przy eksporcie:

- usuń EXIF, lokalizację GPS i niepotrzebne profile;
- fizycznie obróć piksele zgodnie z orientacją;
- nie publikuj animowanych WebP/AVIF;
- zachowaj kanał alfa tylko tam, gdzie jest wymagany;
- sprawdź obraz przy powiększeniu 100% i w docelowym rozmiarze UI.

## 8. Nazewnictwo i metadane

Schemat klucza obiektu:

```text
{typ}/{slug}/{rola}-{kolejnosc}-{szerokosc}x{wysokosc}-v{wersja}.{format}
```

Przykłady:

```text
products/rower-szosowy/main-01-1600x1200-v01.webp
categories/kajaki/hero-desktop-2520x1080-v02.avif
categories/kajaki/card-mobile-800x1600-v01.webp
```

Nazwy używają małych liter ASCII, cyfr i myślników. Bez spacji, polskich znaków,
nazwy modelu AI, daty kampanii ani przypadkowego hasha w nazwie logicznej.
Hash treści może zostać dodany technicznie przez CDN.

Dla każdego mastera należy zapisać:

- typ, rolę i kolejność;
- zakres użycia: `cover` albo `gallery_only`;
- produkt lub kategorię;
- szerokość, wysokość, format i rozmiar;
- tekst alternatywny;
- autora lub operatora;
- źródło i licencję materiałów referencyjnych;
- informację, czy użyto AI;
- model, wersję modelu, prompt, seed lub identyfikator zadania;
- datę wygenerowania i datę akceptacji;
- osobę zatwierdzającą zgodność z produktem;
- numer wersji i status: `draft`, `approved`, `retired`.

## 9. Tekst alternatywny i dostępność

Tekst alternatywny opisuje informację, którą obraz wnosi w danym miejscu.

- zdjęcie produktu: nazwa, typ, kolor i istotny widok;
- zdjęcie zestawu: wymienić najważniejsze elementy;
- zdjęcie detalu: nazwać pokazany mechanizm lub cechę;
- nie zaczynać od „zdjęcie przedstawia”;
- nie dodawać ceny, treści marketingowej ani informacji niewidocznych;
- zalecana długość 80–140 znaków, maksimum techniczne 255 znaków;
- dekoracyjny hero z widocznym tytułem ma pusty `alt` lub pozostaje tłem
  `aria-hidden`;
- nie powtarzać identycznego `alt` dla różnych ujęć galerii.

Przykład:

```text
Czarny rower gravelowy Trek z torbą ramową, widok z lewej strony
```

## 10. Szablony promptów

Prompt ma opisywać rezultat i ograniczenia, a nie markę stylistyczną konkretnego
fotografa.

### Packshot produktu

```text
Realistyczna komercyjna fotografia produktowa: [DOKŁADNY PRODUKT],
[KOLOR, MATERIAŁ, CECHY ZWERYFIKOWANE Z REFERENCJĄ]. Jeden kompletny produkt,
widok [3/4 OD PRZODU / BOK], cały obiekt w kadrze. Matowe, jednolite,
bezszwowe tło w kolorze #F3F6F9. Duże miękkie światło z lewej-góry,
delikatne wypełnienie, naturalny cień kontaktowy, poprawna geometria
i realistyczne materiały. Odpowiednik obiektywu 60 mm, cały produkt ostry.
Kadr poziomy 4:3, obiekt mieści się w centralnych 70% szerokości i 86%
wysokości, co najmniej 8% marginesu z każdej strony. Wierne zdjęciom
referencyjnym, bez zmiany wyposażenia.
```

### Hero kategorii

```text
Realistyczna fotografia lifestyle dla kategorii [KATEGORIA] w wypożyczalni
sprzętu sportowego. [OSOBA / GRUPA] prawidłowo używa [SPRZĘT] w [SCENERIA
EUROPY ŚRODKOWEJ], osiągalna weekendowa przygoda, naturalna pogoda i światło,
wiarygodne ubrania oraz wymagane zabezpieczenia. Nowoczesna, spokojna fotografia
komercyjna, naturalne kolory i umiarkowany kontrast. Główna akcja w [LEWEJ /
PRAWEJ] tercji. Środkowe 45% kadru ciemniejsze, mało szczegółowe i wolne dla
białego tytułu oraz przycisku. Bez tekstu. Wariant [21:9 DESKTOP / 4:5 MOBILE].
```

### Wycięty produkt do kafla

```text
Fotorealistyczny wycięty [PRODUKT], dokładnie [WIDOK I CECHY], cały obiekt,
naturalne materiały, miękkie światło studyjne i subtelny cień. Przezroczyste
tło, czyste krawędzie bez białej obwódki. Obiekt skierowany w [LEWO / PRAWO],
z bezpiecznym marginesem 10%. Proporcje [PRESET P4].
```

### Stała lista wykluczeń

```text
Bez tekstu, napisów, watermarków, ramek, przypadkowych logo, wymyślonych
certyfikatów, dodatkowych akcesoriów, opakowania, duplikatów elementów,
zdeformowanej geometrii, brakujących części, lewitowania, plastikowego wyglądu,
renderu 3D, przesadnego HDR, nadmiernej saturacji, mocnego bokeh, rybiego oka,
uciętego produktu, nierealnych dłoni i nieprawidłowego użycia sprzętu.
```

Lista wykluczeń nie zastępuje ręcznej kontroli wyniku.

## 11. Proces produkcyjny

```text
brief i referencje
→ generowanie / sesja zdjęciowa
→ kontrola zgodności z produktem
→ retusz mastera
→ test bezpiecznych kadrów
→ warianty responsywne
→ kodowanie i optymalizacja
→ alt oraz metadane
→ akceptacja
→ upload i publikacja
```

1. **Brief:** określić rolę, urządzenia, produkt, kategorię i warianty.
2. **Referencje:** używać zdjęć legalnych i możliwie dokładnego modelu produktu.
3. **Generowanie:** zachować prompt, model i identyfikator zadania.
4. **Weryfikacja:** porównać geometrię, kolor, logo, części i wyposażenie
   z rzeczywistym produktem.
5. **Kadrowanie:** okładkę 4:3 sprawdzić w podglądzie 8:7, 5:4 i 1:1, lecz
   opublikować tylko jeden plik 1600 × 1200 px. Zdjęcia `gallery_only` sprawdzić
   wyłącznie w ramie galerii 4:3.
6. **Optymalizacja:** eksportować wszystkie wymagane formaty i rozmiary.
7. **Publikacja:** dopiero materiał ze statusem `approved`.
8. **Wycofanie:** po zmianie modelu lub zestawu unieważnić nieaktualne obrazy.

## 12. Checklista akceptacyjna

Materiał można opublikować tylko wtedy, gdy wszystkie odpowiedzi brzmią „tak”.

### Zgodność

- [ ] Obraz przedstawia właściwy typ, model, kolor i wariant produktu.
- [ ] Liczba części, mocowania, przewody, koła, pasy i klamry są poprawne.
- [ ] Nie pokazano elementu, którego klient nie otrzyma.
- [ ] Logo, oznaczenia i certyfikaty są prawdziwe oraz czytelne tylko wtedy,
      gdy występują na referencji.
- [ ] Użycie sprzętu jest bezpieczne i prawidłowe.

### Kompozycja

- [ ] Okładka (`display_order = 0`) przechodzi kontrolę 4:3, 8:7, 5:4 i 1:1.
- [ ] Każde zdjęcie z `display_order > 0` jest potrzebne w galerii i nie
      duplikuje okładki.
- [ ] Produkt jest cały, ostry i natychmiast rozpoznawalny.
- [ ] Tło, światło i cień są zgodne ze standardem.
- [ ] Brak tekstu, watermarków, artefaktów i przypadkowych przedmiotów.
- [ ] Hero pozostawia czytelne miejsce na tytuł i CTA.

### Technika i dostępność

- [ ] Wymiary, przestrzeń sRGB, format i rozmiar pliku są poprawne.
- [ ] Usunięto EXIF i GPS.
- [ ] Plik dobrze wygląda w jasnym i ciemnym motywie.
- [ ] Zapisano alt, rolę, kolejność, źródło, licencję i pochodzenie AI.
- [ ] Osoba odpowiedzialna zatwierdziła zgodność z ofertą.

## 13. Kontrakt techniczny do wdrożenia

Obecny model tablicy zdjęć jest wystarczający dla przyjętego standardu. API
powinno zachowywać kolejność i podstawowe metadane, np.:

```json
{
  "role": "cover",
  "displayOrder": 0,
  "usage": "cover",
  "alt": "Czarny rower gravelowy, widok z lewej strony",
  "width": 1600,
  "height": 1200,
  "url": "/media/products/rower/main-01-1600x1200-v01.webp"
}
```

Frontend używa tego samego URL-a okładki we wszystkich widokach. Nie oczekuje
wariantów `card`, `square` ani `thumb`. Dopasowanie przez `cover` lub `contain`
jest odpowiedzialnością komponentu, a centralny bezpieczny obszar okładki
ogranicza ryzyko niekorzystnego przycięcia.

API musi zachowywać jednoznaczną kolejność zdjęć. Element z
`display_order = 0` jest okładką, a kolejne elementy są wyłącznie galeryjne.
Widoki list, wyszukiwarki, ulubionych, koszyka i zamówień wyświetlają wyłącznie
okładkę; endpointy obsługujące te widoki docelowo również powinny zwracać tylko
ją. Endpoint szczegółów produktu zwraca pełną, rosnąco posortowaną listę.

Backend powinien:

- przechowywać stabilny klucz obiektu lub URL zamiast BLOB/base64;
- walidować faktyczny MIME, dekodowalność, wymiary i liczbę pikseli;
- przyjmować tylko statyczne JPEG, PNG, WebP i AVIF;
- ograniczyć master do 8 MB i 40 megapikseli;
- nadawać długie cache dla wersjonowanych plików;
- usuwać lub planować usunięcie pliku razem z rekordem;
- zachować unikalną, atomowo zmienianą kolejność galerii.

Okładka jest pojedynczym plikiem 1600 × 1200 px zgodnym z bezpiecznym obszarem
P1. Zdjęcia `gallery_only` również mają 1600 × 1200 px, ale nie muszą
uwzględniać kadrów innych niż 4:3.
