# Отчёт качества данных

_Сформирован: 2026-03-12 18:39:55_

---
## Структурные замечания

| Файл | Проблема | Решение |
| --- | --- | --- |
| `clients_data.json` | Поле называется `id`, в ТЗ — `client_id` | Переименовано при чтении |

---
## Клиенты (`clients_data.json`)

| Метрика | Значение |
| --- | ---: |
| исходных_строк | 9799 |
| client_id_→_плейсхолдер | 1 |
| дубликатов_client_id_удалено | 0 |
| age_отрицательных_→_NaN | 0 |
| age_пропусков_итого | 983 |
| gender_некорректных_→_NaN | 0 |
| gender_пропусков_итого | 3319 |
| net_worth_отрицательных_→_NaN | 0 |
| net_worth_пропусков_итого | 475 |
| итоговых_строк | 9799 |

---
## Транзакции (`transactions_data.xlsx`)

| Метрика | Значение |
| --- | ---: |
| исходных_строк | 10000 |
| transaction_id_невалидных_УДАЛЕНО | 474 |
| transaction_id_дубликатов_УДАЛЕНО | 0 |
| client_id_плейсхолдеров | 191 |
| transaction_date_плохой_формат_УДАЛЕНО | 961 |
| transaction_date_вне_диапазона_УДАЛЕНО | 0 |
| amount_пропусков_или_аномальных | 8565 |
| service_пропусков | 0 |
| payment_method_пропусков | 0 |
| city_пропусков | 0 |
| consultant_пропусков | 0 |
| итоговых_строк | 8565 |

---
## Распределения значений

### `service`

| service | Кол-во |
| --- | ---: |
| Инвестиционное консультирование | 2077 |
| Управление активами | 1721 |
| Финансовое планирование | 1335 |
| Налоговое планирование | 1311 |
| Структурирование капитала | 1281 |
| Неизвестная услуга | 840 |

### `payment_method`

| payment_method | Кол-во |
| --- | ---: |
| Кредитная карта | 3424 |
| Банковский перевод | 2970 |
| Неизвестно | 871 |
| Наличные | 845 |
| Криптовалюта | 455 |

### `city`

| city | Кол-во |
| --- | ---: |
| Неизвестный город | 331 |
| Karenville | 192 |
| North Emily | 185 |
| Port James | 185 |
| New Chelseaberg | 184 |
| Kaneburgh | 184 |
| Mirandaside | 177 |
| North Hannahmouth | 177 |
| Port Jordan | 177 |
| Johnsonfort | 176 |
| Krystalland | 175 |
| Port Michellemouth | 175 |
| New Tommyborough | 174 |
| North Melissaland | 174 |
| Davidsonborough | 174 |
| Erichaven | 174 |
| East Matthewmouth | 173 |
| Cruzport | 173 |
| Lake Arielmouth | 173 |
| Patelbury | 171 |
| Mayoberg | 171 |
| Trevinoberg | 171 |
| New Dianechester | 170 |
| Lake Tina | 168 |
| North Lauriebury | 168 |
| South Andrew | 167 |
| West Jaymouth | 166 |
| Davidmouth | 166 |
| New Ryan | 163 |
| Matthewsville | 161 |
| Ibarramouth | 160 |
| North Patrickport | 160 |
| Jeanettetown | 159 |
| Lake Sallychester | 159 |
| Aprilstad | 158 |
| Roberttown | 158 |
| Port Darlene | 158 |
| East Rachelmouth | 156 |
| East Melissaville | 155 |
| Michellehaven | 154 |
| New Zacharyport | 152 |
| West Meredithhaven | 152 |
| Ronaldville | 151 |
| Hamiltontown | 151 |
| East Jamie | 147 |
| Tonystad | 146 |
| South Thomas | 145 |
| Dannyburgh | 145 |
| Elizabethmouth | 142 |
| Bondstad | 141 |
| Harrisberg | 141 |

### `consultant`

| consultant | Кол-во |
| --- | ---: |
| Неизвестный консультант | 307 |
| Deborah Stone | 195 |
| Ronald Shepherd | 193 |
| Kirsten Martin | 192 |
| Phillip White | 192 |
| Laura Herrera | 189 |
| Mario Jones | 188 |
| Michelle Morse | 183 |
| Erik Garcia | 182 |
| Alexandra Meyer | 180 |
| Catherine Lawson | 177 |
| Cynthia Coleman | 177 |
| Melissa Pena | 176 |
| Gregory Williams | 172 |
| Stephen Jones | 172 |
| Ronald Benson | 172 |
| Kathryn Young | 171 |
| Travis Curtis | 170 |
| David Palmer | 170 |
| Emily Stewart | 169 |
| Timothy Brown | 168 |
| Katherine Smith | 168 |
| Nicholas Barry | 166 |
| Harold Gibson | 165 |
| Joshua Fuentes | 164 |
| Gary Stevenson | 164 |
| Lisa Sanchez MD | 164 |
| Cheryl Waller | 163 |
| Mary Howard | 162 |
| Teresa Baker | 162 |
| Jordan Phillips | 162 |
| Judith Hansen | 160 |
| Wendy Cooper | 158 |
| Frank Pollard | 157 |
| Jessica Bates | 157 |
| Sarah Alvarez | 157 |
| William Bell | 156 |
| John Wolfe | 156 |
| Tiffany James | 156 |
| Dylan Martin | 154 |
| Julie Jones | 154 |
| David Thompson | 154 |
| Terry Brown | 152 |
| Chad Raymond | 152 |
| Antonio Benton | 152 |
| Edwin Cantrell | 151 |
| Patricia Haas | 149 |
| Jason Beard | 146 |
| Rachel Williamson | 139 |
| Courtney Callahan | 137 |
| Ethan Lowe | 133 |
