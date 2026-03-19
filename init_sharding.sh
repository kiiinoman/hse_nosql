#!/bin/bash
# init_sharding.sh — Run this AFTER docker compose up

echo "⏳ Waiting for containers to start..."
sleep 10

echo "🔧 Initializing config server replica set..."
docker exec configsvr mongosh --port 27019 --eval '
rs.initiate({
  _id: "configReplSet",
  configsvr: true,
  members: [{ _id: 0, host: "configsvr:27019" }]
})
'

sleep 5

echo "🔧 Initializing shard1 replica set..."
docker exec shard1 mongosh --port 27018 --eval '
rs.initiate({
  _id: "shard1ReplSet",
  members: [{ _id: 0, host: "shard1:27018" }]
})
'

echo "🔧 Initializing shard2 replica set..."
docker exec shard2 mongosh --port 27020 --eval '
rs.initiate({
  _id: "shard2ReplSet",
  members: [{ _id: 0, host: "shard2:27020" }]
})
'

sleep 5

echo "🔗 Adding shards to the cluster..."
docker exec mongos mongosh --port 27017 --eval '
sh.addShard("shard1ReplSet/shard1:27018");
sh.addShard("shard2ReplSet/shard2:27020");
'

echo "🗄️ Creating database and enabling sharding..."
docker exec mongos mongosh --port 27017 --eval '
sh.enableSharding("university");

// Hashed sharding on student_id for even distribution
sh.shardCollection("university.students",   { student_id: "hashed" });
sh.shardCollection("university.enrollments",{ student_id: "hashed" });

// Range sharding on faculty_id — logical grouping
sh.shardCollection("university.courses",    { faculty_id: 1 });

use university;

// Create indexes
db.students.createIndex({ student_id: 1 }, { unique: true });
db.students.createIndex({ email: 1 },      { unique: true });
db.students.createIndex({ group_id: 1 });
db.enrollments.createIndex({ student_id: 1, course_id: 1 });
db.courses.createIndex({ faculty_id: 1 });

print("✅ Sharding initialized successfully!");
print(sh.status());
'

echo ""
echo "✅ Done! Connect to mongos at localhost:27017"
echo "   Run: python seed.py  — to populate with test data"
echo "   Run: python cli.py   — to start the CLI"
