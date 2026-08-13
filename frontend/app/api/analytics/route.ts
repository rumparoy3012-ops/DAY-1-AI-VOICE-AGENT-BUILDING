import { NextResponse } from 'next/server';
import sqlite3 from 'sqlite3';
import path from 'path';
import fs from 'fs';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(): Promise<NextResponse> {
  // Enforce/resolve absolute path to agent_memory.db
  let dbPath = path.resolve(process.cwd(), '../backend/agent_memory.db');
  if (!fs.existsSync(dbPath)) {
    // If not found (e.g. if run from workspace root), try alternative
    dbPath = path.resolve(process.cwd(), 'backend/agent_memory.db');
  }

  if (!fs.existsSync(dbPath)) {
    return NextResponse.json({
      total_calls: 0,
      successful_calls: 0,
      failed_calls: 0,
      success_rate: '0.0',
      recent_calls: [],
      error: `Database file not found at: ${dbPath}`
    }, { status: 404 });
  }

  // Query SQLite
  return new Promise((resolve) => {
    const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
      if (err) {
        resolve(NextResponse.json({ error: err.message }, { status: 500 }));
        return;
      }
    });

    db.serialize(() => {
      // 1. Get total_calls
      db.get("SELECT COUNT(*) as total FROM call_analytics", (err, rowTotal: any) => {
        if (err) {
          db.close();
          resolve(NextResponse.json({ error: err.message }, { status: 500 }));
          return;
        }

        const total_calls = rowTotal ? rowTotal.total : 0;

        // 2. Get successful_calls
        db.get("SELECT COUNT(*) as success FROM call_analytics WHERE outcome = 'SUCCESS'", (err, rowSuccess: any) => {
          if (err) {
            db.close();
            resolve(NextResponse.json({ error: err.message }, { status: 500 }));
            return;
          }

          const successful_calls = rowSuccess ? rowSuccess.success : 0;

          // 3. Get failed_calls
          db.get("SELECT COUNT(*) as failed FROM call_analytics WHERE outcome = 'FAILED'", (err, rowFailed: any) => {
            if (err) {
              db.close();
              resolve(NextResponse.json({ error: err.message }, { status: 500 }));
              return;
            }

            const failed_calls = rowFailed ? rowFailed.failed : 0;

            // 4. Get recent_calls (latest 5 logs ordered by timestamp DESC)
            db.all("SELECT call_id, timestamp, outcome, reason FROM call_analytics ORDER BY timestamp DESC LIMIT 5", (err, rowsRecent: any[]) => {
              db.close();
              if (err) {
                resolve(NextResponse.json({ error: err.message }, { status: 500 }));
                return;
              }

              const success_rate = total_calls > 0 
                ? ((successful_calls / total_calls) * 100).toFixed(1)
                : '0.0';

              const recent_calls = (rowsRecent || []).map((row) => ({
                call_id: row.call_id,
                timestamp: row.timestamp,
                outcome: row.outcome,
                reason: row.reason,
              }));

              resolve(NextResponse.json({
                total_calls,
                successful_calls,
                failed_calls,
                success_rate,
                recent_calls,
              }));
            });
          });
        });
      });
    });
  });
}
