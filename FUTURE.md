# Future work

What we would build next, in the lead's order of priority, and why. The README's "Given more time" section draws from this list.

## 1. AI as the one way in

The user tells the app what they want, and the AI looks after the list. This comes first. We left it out of the build on purpose: the assessment is about full-stack skills.

- **Create tasks by describing them.** The user types or speaks ("remind me to call the dentist on Friday"), and the app creates the task. The model's answer is not trusted as it is: it is turned into the same typed models the API already checks, and the user confirms before anything changes.
- **Update tasks by voice.** A voice button on the list. The user says "move the dentist to Monday and mark the report done", and an agent makes the changes with tools that call the existing task service.
- **Tools next to the model at first, an MCP server later.** While the app is small, the tools live with the model call. If it grows into part of a bigger product, the tools move behind an MCP server, so they can scale and change apart from the model.
- **Open the MCP server to subscribers.** Anyone with a subscription connects the AI agent they already use every day, such as ChatGPT, to their list through our MCP server, and that agent keeps the list up to date. The web or mobile app is there to look at the list, with notifications on mobile. Few people will build an agent just for their to-dos; they will use the one they have, so the app becomes the place where the list lives. Open-sourcing the server is worth considering too.
- **Ask about your work.** "Summarise my backlog." "What does my week look like?" "What does my year look like?" Possibly streamed to the screen with the AG-UI protocol.
- **Memory.** The AI remembers what the user tells it about themselves, even when it is not a task, and uses it to make the list more personal and more realistic.
- **API management in front of the models.** Azure API Management, or the same service on another cloud, sits between the cluster and the models. It picks a model that is up, retries failed calls and applies rate limits, so the backend code does not have to.

## 2. Delivery and environments

- **CI/CD with dev, UAT and prod.** One GitHub environment per stage, each with its own deployment. Start with dev only; add UAT once there are users to test with; prod after that. Each release is a version tag that moves from dev to UAT to prod.
- **A cloud cluster (was round 3).** Terraform creates the cloud resources, and the same Kustomize manifests deploy the app, so it runs on AKS, EKS or GKE with only a new overlay. Images go to the cloud's registry, secrets to its key vault, and traffic comes in through a managed ingress with a real certificate. GitHub Actions deploys, signing in to the cloud with OIDC instead of stored keys. We did not build this, for lack of time.
- **The database: in the cluster or managed.** Decide with the team. Running Postgres in the cluster keeps it portable and cheap. A managed database (Azure Database for PostgreSQL, Azure Cosmos DB, or the same on another cloud) brings replicas, backups and a connection pooler; the pooler would lift the API's limit of five pods.
- **Clean up merged branches.** Twelve finished branches are still on GitHub; delete them once the submission is reviewed.
- **A k3d job in CI.** Create the cluster in the job and run the suites and a rolling restart under load against it, so a change that breaks only the cluster fails its own PR. Round 2 ran k3d on the Mac only.

## 3. Security and robustness

- **Monitoring with Grafana.** Dashboards and alerts for errors, response times, pods and the database, from a metrics endpoint scraped by Prometheus and from the JSON logs the app already writes.
- **Pod Security and network policies.** Enforce the `restricted` level on the namespace, and block all traffic by default, then allow only nginx to the API, and the API and the migration Job to Postgres.
- **Two API pods at rest.** One pod at rest is gentle on a laptop, but losing it costs about 15 seconds of errors. Two pods remove that.
- **Sign-in rate limiting.** It needs a limit that every replica shares, so it belongs in the ingress or in API management, not in each pod.
- **Self-host the API docs page, or turn it off in production.** `/api/docs` loads Swagger UI from jsDelivr with no integrity check, and its CSP allows one inline script by its hash. Serving pinned files from the API removes the outside script.
- **Cleaner logs.** uvicorn adds colour codes to its access lines, which end up inside the JSON logs; and 400 answers for domain errors are not logged yet.
- **The hygiene check's folder list.** It still names `e2e` and `load`, which moved under `tests/`, so it does not scan those suites. They were checked by hand before submission.
- **Later: split the frontend bundle by route.** The app ships as one 524 kB file. Not urgent.

## 4. The product

- **User testing (UAT) first.** Listening to real users is the most important step: it tells us what makes this app worth choosing.
- **More designs.** Three or four more next to the vintage one, chosen with users.
- **Mobile, web, or both.** A to-do list may work best as a mobile app, with notifications for what is due. Test that.
- **A paid plan.** Token-based or a subscription, whichever users prefer in UAT.
- **Data care.** A job that shortens long ranks in a list, and paging for long lists; the `{"items": [...]}` envelope already leaves room for a cursor.

## 5. Identity (last)

- **Sign-in with Microsoft, Google or Apple.** Only once external users test the app in UAT. OpenID Connect with the provider each client already uses; email and password stay.
- **Refresh-token rotation and revocation.** Short-lived access tokens, a rotating refresh token and a deny list, so a stolen or signed-out session can be ended early.
- **Email checks and password reset.** Both need an email service.
