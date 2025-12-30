/* chronos.js */
const opentelemetry = require('@opentelemetry/api');
const Task = require('./models/Task');

function startTelemetryCron() {
    console.log('Starting Telemetry Cron Service (Diff Detection Enabled)...');

    // Run every 10 seconds (checks for changes)
    const INTERVAL_MS = 10000;

    // Store the signature of the last sent snapshot
    let lastSnapshotSignature = '';

    setInterval(async () => {
        try {
            // 1. Fetch ALL data (Full Dump)
            // Using .lean() for performance since we just need the JSON
            const allTasks = await Task.find().sort({ createdAt: -1 }).lean();

            // 2. Create a signature (JSON string)
            const currentSignature = JSON.stringify(allTasks);

            // 3. Diff Detection: Skip if data hasn't changed
            if (currentSignature === lastSnapshotSignature) {
                // console.log('No DB changes detected. Skipping telemetry.'); 
                return;
            }

            console.log(`DB Change Detected! Sending Telemetry (Total: ${allTasks.length})...`);

            const tracer = opentelemetry.trace.getTracer('backend-service');
            const span = tracer.startSpan('db-snapshot-change', {
                kind: opentelemetry.SpanKind.INTERNAL,
            });

            try {
                // 1. Add Stats Attributes
                const totalTasks = allTasks.length;
                span.setAttribute('db.collection', 'tasks');
                span.setAttribute('db.count.total', totalTasks);

                // Aggregate stats manually since we have the full array
                const userCounts = allTasks.reduce((acc, task) => {
                    acc[task.user] = (acc[task.user] || 0) + 1;
                    return acc;
                }, {});
                span.setAttribute('db.stats.by_user', JSON.stringify(userCounts));

                // 2. FULL DUMP as an Event
                // Note: Large dumps might be truncated by the exporter depending on config
                span.addEvent('db-full-dump', {
                    'data.json': currentSignature
                });

                span.setStatus({ code: opentelemetry.SpanStatusCode.OK });

                // Update state
                lastSnapshotSignature = currentSignature;

            } catch (innerError) {
                console.error('Error recording span:', innerError);
                span.recordException(innerError);
            } finally {
                span.end();
            }

        } catch (error) {
            console.error('Error in Telemetry Cron:', error);
        }
    }, INTERVAL_MS);
}

module.exports = { startTelemetryCron };
