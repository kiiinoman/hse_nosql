# hse_nosql
## Структура проекта

```
.
├── docker-compose.yml   # MongoDB sharding инфраструктура
├── init_sharding.sh     # Инициализация шардов и коллекций
├── cli.py               # Консольный интерфейс
├── seed.py              # Заполнение тестовыми данными
└── load_test.py         # Нагрузочное тестирование
```

## Схема БД

Коллекции (аналог таблиц):

| Коллекция     | Ключ шардирования | Метод    |
|---------------|-------------------|----------|
| `students`    | `student_id`      | hashed   |
| `enrollments` | `student_id`      | hashed   |
| `courses`     | `faculty_id`      | ranged   |

**Почему hashed для students?**
Равномерное распределение документов по шардам без hot-spots.

**Почему ranged для courses?**
Courses часто запрашиваются по факультету — range sharding позволяет делать эффективные range scans.

---

## Быстрый старт

### 1. Запуск инфраструктуры

```bash
docker compose up -d
```

### 2. Инициализация шардинга

```bash
chmod +x init_sharding.sh
./init_sharding.sh
```

### 3. Установка Python зависимостей

```bash
pip install pymongo locust
```

### 4. Заполнение тестовыми данными

```bash
# По умолчанию: 10 000 студентов, 3 курса на студента
python seed.py

# Или с параметрами:
python seed.py --students 50000 --enrollments 5
```

### 5. Запуск CLI

```bash
python cli.py
```

### 6. Нагрузочное тестирование

```bash
# С веб-интерфейсом (открыть http://localhost:8089)
locust -f load_test.py

# Без веб-интерфейса
locust -f load_test.py --headless -u 50 -r 10 --run-time 60s
```

---

## Архитектура шардинга

```
Client
  │
  ▼
mongos (router) :27017
  │
  ├── configsvr (config replica set) :27019
  │
  ├── shard1 :27018  ←── ~50% documents
  └── shard2 :27020  ←── ~50% documents
```

## Полезные команды MongoDB

```javascript
// Статус шардирования
sh.status()

// Распределение по шардам
db.students.getShardDistribution()

// Explain запроса (показывает, на какой шард пошёл запрос)
db.students.find({student_id: "abc123"}).explain("executionStats")
```
