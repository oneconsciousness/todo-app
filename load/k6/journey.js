// The load test: every virtual user (VU) signs in once, seeds five tasks, then repeats a full task journey.
// Run through compose: `docker compose --profile load run --rm k6 run /scripts/journey.js`.
// k6 scripting reference: https://grafana.com/docs/k6/latest/javascript-api/

import exec from "k6/execution";
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://web:8080";
const APP_ORIGIN = __ENV.APP_ORIGIN || "http://localhost:8080";
const VUS = Number(__ENV.VUS || 200);
const HOLD = __ENV.HOLD || "3m";
const RESULTS_DIR = __ENV.RESULTS_DIR || "/results";

const API = `${BASE_URL}/api/v1`;
const SEED_WORDS = ["milk", "report", "dentist", "garden", "invoice"];

const ONE_TASK = { name: `${API}/tasks/{id}` };

const serverErrors = new Counter("server_errors");

export const options = {
  scenarios: {
    journey: {
      executor: "ramping-vus",
      stages: [
        { duration: "1m", target: VUS },
        { duration: HOLD, target: VUS },
      ],
      gracefulRampDown: "30s",
    },
  },
  // k6 empties each VU's cookie jar between iterations by default; keep it, so a VU stays signed in like a browser.
  // https://grafana.com/docs/k6/latest/using-k6/k6-options/reference/#no-cookies-reset
  noCookiesReset: true,
  // Signing up or checking hundreds of accounts takes longer than k6's default 60 s for setup and teardown.
  setupTimeout: "5m",
  teardownTimeout: "5m",
  // The budgets: k6 exits non-zero when any of these fails. https://grafana.com/docs/k6/latest/using-k6/thresholds/
  thresholds: {
    http_req_failed: ["rate<0.001"],
    server_errors: ["count==0"],
    "http_req_duration{kind:read}": ["p(95)<250"],
    "http_req_duration{kind:write}": ["p(95)<400"],
    "http_req_duration{kind:auth}": ["p(95)<1500"],
    checks: ["rate>0.999"],
  },
};

/** Request params: the app's origin (the API refuses writes from any other), JSON, and the request's kind for the budgets. */
const params = (kind, extra = {}) => ({
  headers: { Origin: APP_ORIGIN, "Content-Type": "application/json", ...(extra.headers || {}) },
  // One name for every task's URL, or each task id becomes its own metric series:
  // https://grafana.com/docs/k6/latest/using-k6/tags-and-groups/#url-grouping
  tags: { kind, ...(extra.name ? { name: extra.name } : {}) },
  ...(extra.cookies ? { cookies: extra.cookies } : {}),
});

/** Count a 5xx and check the status the step expects. */
const expectStatus = (response, status, step) => {
  if (response.status >= 500) serverErrors.add(1);
  check(response, { [`${step} answers ${status}`]: (r) => r.status === status });
  return response.status === status;
};

const pick = (items) => items[Math.floor(Math.random() * items.length)];

/** Sign up one account per VU and give every VU their emails and the run's password. */
export function setup() {
  const runId = Date.now();
  const password = `load-${crypto.randomUUID()}`;
  // example.com, because the API's email validation refuses special-use domains such as .test.
  const emails = Array.from({ length: VUS }, (_, n) => `load-${runId}-${n + 1}@example.com`);
  const signUps = emails.map((email) => [
    "POST",
    `${API}/auth/register`,
    JSON.stringify({ email, password }),
    params("setup"),
  ]);
  // k6 sends a batch at most six requests at a time to one host, so sign-ups never all hash at once.
  // https://grafana.com/docs/k6/latest/using-k6/k6-options/reference/#batch-per-host
  const created = http.batch(signUps).filter((response) => response.status === 201).length;
  if (created !== VUS) exec.test.abort(`setup signed up ${created} of ${VUS} accounts`);
  return { emails, password };
}

// Module scope is per VU in k6, so this marks whether this VU has signed in and seeded its tasks yet.
let seeded = false;

/** Sign in as this VU's own account and create its five seed tasks, one per search word. */
const signInAndSeed = (data) => {
  const email = data.emails[exec.vu.idInTest - 1];
  const signIn = http.post(`${API}/auth/login`, JSON.stringify({ email, password: data.password }), params("auth"));
  expectStatus(signIn, 200, "sign in");
  SEED_WORDS.forEach((word) => {
    expectStatus(http.post(`${API}/tasks`, JSON.stringify({ title: `${word} seed` }), params("write")), 201, "seed");
  });
};

/** One pass of a user's task journey; on the VU's first pass it signs in and seeds its tasks. */
export default function journey(data) {
  if (!seeded) {
    signInAndSeed(data);
    seeded = true;
  }

  const list = http.get(`${API}/tasks`, params("read"));
  expectStatus(list, 200, "list");
  sleep(1);

  const word = pick(SEED_WORDS);
  expectStatus(http.get(`${API}/tasks?q=${word}`, params("read")), 200, "search");
  sleep(1);

  const create = http.post(
    `${API}/tasks`,
    JSON.stringify({ title: `load ${word} ${exec.vu.iterationInScenario}` }),
    params("write"),
  );
  if (!expectStatus(create, 201, "create")) {
    sleep(1);
    return;
  }
  const taskId = create.json("id");
  const task = `${API}/tasks/${taskId}`;
  sleep(1);

  const toggle = http.patch(task, JSON.stringify({ completed: true }), params("write", ONE_TASK));
  expectStatus(toggle, 200, "toggle");
  sleep(1);

  const others = list.status === 200 ? list.json("items").filter((item) => item.id !== taskId) : [];
  if (others.length > 0) {
    const after = pick(others).id;
    expectStatus(
      http.put(
        `${task}/position`,
        JSON.stringify({ afterId: after }),
        params("write", { name: `${API}/tasks/{id}/position` }),
      ),
      200,
      "move",
    );
    sleep(1);
  }

  // The toggle's ETag still names the current version: a move leaves the version alone.
  const ifMatch = { headers: { "If-Match": toggle.headers.Etag } };
  expectStatus(
    http.patch(task, JSON.stringify({ notes: "edited under load" }), params("write", { ...ONE_TASK, ...ifMatch })),
    200,
    "edit",
  );
  sleep(1);

  expectStatus(http.del(task, null, params("write", ONE_TASK)), 204, "delete");
  sleep(1);
}

/** True when a list holds exactly the five seed tasks, with no two ranks equal; the list query already sorts by rank. */
const isIntact = (items) => {
  const ranks = items.map((item) => item.rank);
  return items.length === SEED_WORDS.length && new Set(ranks).size === ranks.length;
};

/** Sign back into every account and fail the run unless each holds exactly its seed tasks. */
export function teardown(data) {
  const signIns = data.emails.map((email) => [
    "POST",
    `${API}/auth/login`,
    JSON.stringify({ email, password: data.password }),
    params("teardown"),
  ]);
  const sessions = http.batch(signIns).map((response) => response.cookies.session?.[0]?.value);
  // Teardown is one VU with one cookie jar, so each list sends its own account's session explicitly.
  const lists = sessions.map((session) => [
    "GET",
    `${API}/tasks`,
    null,
    params("teardown", { cookies: { session: { value: session || "", replace: true } } }),
  ]);
  const broken = http.batch(lists).filter((response) => response.status !== 200 || !isIntact(response.json("items")));
  if (broken.length > 0) {
    console.error(
      `data check: ${broken.length} of ${data.emails.length} accounts do not hold exactly five tasks with unique ranks`,
    );
    exec.test.fail(`data check failed for ${broken.length} accounts`);
  }
}

const p95 = (data, name) => data.metrics[name]?.values["p(95)"]?.toFixed(1) ?? "n/a";

/** Write the full summary as JSON for the capacity record, and print the figures that decide pass or fail. */
export function handleSummary(data) {
  const failed = Object.entries(data.metrics).flatMap(([name, metric]) =>
    Object.entries(metric.thresholds || {})
      .filter(([, threshold]) => !threshold.ok)
      .map(([expression]) => `${name} ${expression}`),
  );
  const text = [
    `VUs ${VUS}, hold ${HOLD}`,
    `requests ${data.metrics.http_reqs.values.count} (${data.metrics.http_reqs.values.rate.toFixed(1)}/s), iterations ${data.metrics.iterations?.values.count ?? 0}`,
    `p95 ms: read ${p95(data, "http_req_duration{kind:read}")}, write ${p95(data, "http_req_duration{kind:write}")}, auth ${p95(data, "http_req_duration{kind:auth}")}`,
    `failed requests ${(data.metrics.http_req_failed.values.rate * 100).toFixed(3)}%, server errors ${data.metrics.server_errors?.values.count ?? 0}, checks ${(data.metrics.checks.values.rate * 100).toFixed(2)}%`,
    failed.length === 0 ? "budgets: all met" : `budgets missed: ${failed.join("; ")}`,
    "",
  ].join("\n");
  // setup()'s return value holds every account's email and the run's password, so it never reaches the file.
  const { setup_data: _accounts, ...summary } = data;
  return { [`${RESULTS_DIR}/summary-${VUS}.json`]: JSON.stringify(summary, null, 2), stdout: text };
}
