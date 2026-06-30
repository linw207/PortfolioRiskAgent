const dbName = process.env.MONGODB_DATABASE || "portfolio_risk_agent";
const db = db.getSiblingDB(dbName);

const collections = [
  "users",
  "portfolios",
  "watch_items",
  "trade_journals",
  "analysis_tasks",
  "agent_run_records",
  "tool_call_records",
  "report_archives",
  "notification_channels",
  "notification_records",
  "scheduled_jobs",
  "config_change_records",
];

for (const name of collections) {
  if (!db.getCollectionNames().includes(name)) {
    db.createCollection(name);
  }
}

db.users.createIndex({ user_id: 1 }, { unique: true });
db.portfolios.createIndex({ portfolio_id: 1 }, { unique: true });
db.portfolios.createIndex({ user_id: 1, created_at: -1 });
db.watch_items.createIndex({ user_id: 1, symbol: 1 }, { unique: true });
db.trade_journals.createIndex({ user_id: 1, symbol: 1, trade_date: -1 });
db.analysis_tasks.createIndex({ task_id: 1 }, { unique: true });
db.analysis_tasks.createIndex({ user_id: 1, status: 1, created_at: -1 });
db.analysis_tasks.createIndex({ portfolio_id: 1, created_at: -1 });
db.agent_run_records.createIndex({ task_id: 1, created_at: 1 });
db.tool_call_records.createIndex({ task_id: 1, tool_name: 1, created_at: 1 });
db.report_archives.createIndex({ report_id: 1 }, { unique: true });
db.report_archives.createIndex({ task_id: 1 });
db.report_archives.createIndex({ portfolio_id: 1, created_at: -1 });
db.notification_channels.createIndex({ user_id: 1, channel_type: 1 });
db.notification_records.createIndex({ channel_id: 1, event_type: 1, created_at: -1 });
db.scheduled_jobs.createIndex({ user_id: 1, job_type: 1, enabled: 1 });
db.config_change_records.createIndex({ changed_at: -1 });

db.users.updateOne(
  { user_id: "user_demo" },
  {
    $setOnInsert: {
      user_id: "user_demo",
      username: "demo",
      role: "user",
      risk_preference: "balanced",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  },
  { upsert: true },
);

printjson({
  ok: true,
  database: dbName,
  collections: db.getCollectionNames().sort(),
});
